# coach/tenant_aware_vector_store.py
"""Tenant-aware vector store implementation for multi-tenant support."""

import os
import logging
from typing import Optional, Dict, Any

from coach.langchain_vector_store import LangChainVectorStore
from coach.tenant import TenantManager
from coach.config import Config

logger = logging.getLogger(__name__)


class TenantAwareLangChainVectorStore(LangChainVectorStore):
    """Tenant-aware vector store that isolates data per tenant."""
    
    def __init__(
        self,
        tenant_manager: TenantManager,
        config: Config,
        embedding_provider: str = "openai",
        embedding_model: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize tenant-aware vector store.
        
        Args:
            tenant_manager: Manager for tenant-specific paths
            config: Application configuration
            embedding_provider: Provider for embeddings ('openai' or 'google')
            embedding_model: Specific embedding model to use
            **kwargs: Additional parameters for embeddings
        """
        self.tenant_manager = tenant_manager
        self.config = config
        
        # Use tenant-specific vector store path
        store_folder = tenant_manager.get_vector_store_path()
        
        # Initialize parent class with tenant-specific folder
        super().__init__(
            store_folder=store_folder,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model or config.EMBEDDING_MODEL,
            **kwargs
        )
        
        logger.info(f"Initialized tenant-aware vector store for tenant {tenant_manager.tenant_id}")
    
    def _get_faiss_index_path(self) -> str:
        """Get tenant-specific FAISS index path."""
        return self.tenant_manager.get_faiss_index_path()
    
    def _load_existing_store(self):
        """Load existing vector store from tenant-specific location."""
        faiss_path = self._get_faiss_index_path()
        
        try:
            if os.path.exists(faiss_path):
                # Import here to avoid circular imports
                from langchain_community.vectorstores import FAISS
                
                self.faiss_store = FAISS.load_local(
                    faiss_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                # Get documents from FAISS store
                self.documents = list(self.faiss_store.docstore._dict.values())
                logger.info(
                    f"Loaded existing FAISS store for tenant {self.tenant_manager.tenant_id} "
                    f"with {len(self.documents)} documents"
                )
                
                # Rebuild retrievers
                self._build_retrievers()
            else:
                logger.info(
                    f"No existing vector store found for tenant {self.tenant_manager.tenant_id}, "
                    "will create new one"
                )
        except Exception as e:
            logger.warning(
                f"Failed to load existing store for tenant {self.tenant_manager.tenant_id}: {e}"
            )
            self.faiss_store = None
            self.documents = []
    
    def save(self):
        """Save the vector store to tenant-specific disk location."""
        if not self.faiss_store:
            logger.warning(f"No FAISS store to save for tenant {self.tenant_manager.tenant_id}")
            return
        
        try:
            faiss_path = self._get_faiss_index_path()
            self.faiss_store.save_local(faiss_path)
            logger.info(
                f"Saved vector store for tenant {self.tenant_manager.tenant_id} "
                f"with {len(self.documents)} documents"
            )
            
        except Exception as e:
            from coach.exceptions import VectorStoreSaveException
            raise VectorStoreSaveException(
                f"Failed to save vector store for tenant {self.tenant_manager.tenant_id}: {str(e)}"
            ) from e
    
    def get_tenant_id(self) -> str:
        """Get the tenant ID associated with this vector store."""
        return self.tenant_manager.tenant_id
    
    def __repr__(self):
        return (
            f"TenantAwareLangChainVectorStore(tenant_id={self.tenant_manager.tenant_id}, "
            f"documents={len(self.documents)})"
        )


from coach.resource_pool import get_vector_store_pool


def get_cached_vector_store(
    tenant_id: str,
    tenant_manager: TenantManager,
    config: Config,
    **kwargs
) -> TenantAwareLangChainVectorStore:
    """
    Get or create a cached tenant-aware vector store.
    
    Uses LRU resource pool to manage memory usage for concurrent users.
    
    Args:
        tenant_id: Unique tenant identifier (used as cache key)
        tenant_manager: Manager for tenant-specific paths
        config: Application configuration
        **kwargs: Additional parameters for vector store initialization
        
    Returns:
        Cached TenantAwareLangChainVectorStore instance
    """
    # Get the resource pool
    pool = get_vector_store_pool()
    
    # Try to get from pool
    vector_store = pool.get(tenant_id)
    
    if vector_store is not None:
        logger.info(f"Returning cached vector store for tenant {tenant_id}")
        return vector_store
    
    # Create new vector store
    logger.info(f"Creating new vector store for tenant {tenant_id}")
    vector_store = TenantAwareLangChainVectorStore(
        tenant_manager=tenant_manager,
        config=config,
        **kwargs
    )
    
    # Add to pool
    pool.put(tenant_id, vector_store)
    
    return vector_store


def clear_vector_store_cache(tenant_id: Optional[str] = None):
    """
    Clear vector store cache.
    
    Args:
        tenant_id: Specific tenant to clear, or None to clear all
    """
    pool = get_vector_store_pool()
    
    if tenant_id:
        removed = pool.remove(tenant_id)
        if removed:
            logger.info(f"Cleared vector store cache for tenant {tenant_id}")
    else:
        pool.clear()
        logger.info("Cleared all vector store caches")


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics about the vector store cache."""
    pool = get_vector_store_pool()
    return pool.get_stats()


def cleanup_expired_stores() -> int:
    """
    Clean up expired vector stores from the cache.
    
    Returns:
        Number of expired stores removed
    """
    pool = get_vector_store_pool()
    count = pool.cleanup_expired()
    
    if count > 0:
        logger.info(f"Cleaned up {count} expired vector stores")
    
    return count