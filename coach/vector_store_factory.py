# coach/vector_store_factory.py
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from functools import lru_cache

from coach.config import config
from coach.langchain_vector_store import LangChainVectorStore, TenantAwareLangChainVectorStore
from coach.encrypted_vector_store import EncryptedTenantAwareLangChainVectorStore
from coach.exceptions import VectorStoreException

if TYPE_CHECKING:
    from coach.tenant import TenantManager
    from coach.encryption import EncryptionManager
    from coach.storage.base import StorageProvider

logger = logging.getLogger(__name__)


def create_vector_store(
    tenant_manager: Optional["TenantManager"] = None,
    embedding_provider: str = "openai",
    embedding_model: Optional[str] = None,
    **kwargs
) -> LangChainVectorStore:
    """
    Factory function to create appropriate vector store instance.
    
    Args:
        tenant_manager: TenantManager instance for tenant isolation (optional)
        embedding_provider: Provider for embeddings ('openai' or 'google')
        embedding_model: Specific embedding model to use
        **kwargs: Additional parameters for embeddings
        
    Returns:
        LangChainVectorStore: Either TenantAwareLangChainVectorStore or standard LangChainVectorStore
        
    Raises:
        VectorStoreException: If vector store creation fails
    """
    try:
        if tenant_manager:
            logger.info(f"Creating tenant-aware vector store for tenant {tenant_manager.tenant_id}")
            return TenantAwareLangChainVectorStore(
                tenant_manager=tenant_manager,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                **kwargs
            )
        else:
            logger.info("Creating standard vector store (single-tenant mode)")
            return LangChainVectorStore(
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                **kwargs
            )
    except Exception as e:
        raise VectorStoreException(f"Failed to create vector store: {str(e)}") from e


@lru_cache(maxsize=config.VECTOR_STORE_CACHE_SIZE if hasattr(config, 'VECTOR_STORE_CACHE_SIZE') else 5)
def create_cached_vector_store(
    tenant_id: str,
    embedding_provider: str = "openai",
    embedding_model: Optional[str] = None,
    **kwargs
) -> TenantAwareLangChainVectorStore:
    """
    Create a cached tenant-aware vector store.
    
    This function uses LRU cache to store vector store instances for performance.
    Note: tenant_manager needs to be reconstructed since it's not serializable.
    
    Args:
        tenant_id: Tenant identifier
        embedding_provider: Provider for embeddings
        embedding_model: Specific embedding model to use
        **kwargs: Additional parameters
        
    Returns:
        TenantAwareLangChainVectorStore: Cached vector store instance
        
    Raises:
        VectorStoreException: If vector store creation fails
    """
    # Note: This is a simplified cache that only works with tenant_id
    # In a full implementation, you'd need to reconstruct the TenantManager
    # or modify the caching strategy to work with the full object
    logger.info(f"Creating cached vector store for tenant {tenant_id}")
    
    try:
        # Import here to avoid circular imports
        from coach.tenant import TenantManager
        from coach.models import UserContext
        
        # Create a minimal UserContext for caching purposes
        # In production, you'd want a more sophisticated approach
        user_context = UserContext(
            user_id=tenant_id,
            email=f"{tenant_id}@cached.local",
            name=f"Cached User {tenant_id}",
            oauth_token="cached",
            refresh_token="cached"
        )
        
        tenant_manager = TenantManager(user_context)
        
        return TenantAwareLangChainVectorStore(
            tenant_manager=tenant_manager,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            **kwargs
        )
    except Exception as e:
        raise VectorStoreException(f"Failed to create cached vector store for tenant {tenant_id}: {str(e)}") from e


def get_vector_store_for_tenant(tenant_manager: "TenantManager", use_cache: bool = True) -> TenantAwareLangChainVectorStore:
    """
    Get a vector store instance for a specific tenant.
    
    Args:
        tenant_manager: TenantManager instance
        use_cache: Whether to use cached instances
        
    Returns:
        TenantAwareLangChainVectorStore: Vector store for the tenant
    """
    if use_cache:
        return create_cached_vector_store(
            tenant_id=tenant_manager.tenant_id,
            embedding_provider=config.EMBEDDING_PROVIDER if hasattr(config, 'EMBEDDING_PROVIDER') else "openai",
            embedding_model=config.EMBEDDING_MODEL
        )
    else:
        # Type cast since we know when tenant_manager is provided, create_vector_store returns TenantAwareLangChainVectorStore
        return create_vector_store(tenant_manager=tenant_manager)  # type: ignore


def clear_vector_store_cache():
    """Clear the vector store cache."""
    create_cached_vector_store.cache_clear()
    logger.info("Cleared vector store cache")


def get_cache_info() -> Dict[str, Any]:
    """Get information about the vector store cache."""
    cache_info = create_cached_vector_store.cache_info()
    return {
        "hits": cache_info.hits,
        "misses": cache_info.misses,
        "maxsize": cache_info.maxsize,
        "currsize": cache_info.currsize
    }


def create_encrypted_vector_store(
    tenant_manager: "TenantManager",
    encryption_manager: "EncryptionManager",
    storage_provider: Optional["StorageProvider"] = None,
    embedding_provider: str = "openai",
    embedding_model: Optional[str] = None,
    **kwargs
) -> EncryptedTenantAwareLangChainVectorStore:
    """
    Create an encrypted tenant-aware vector store.
    
    Args:
        tenant_manager: TenantManager instance for tenant isolation
        encryption_manager: EncryptionManager for data encryption
        storage_provider: Optional storage provider for cloud storage
        embedding_provider: Provider for embeddings ('openai' or 'google')
        embedding_model: Specific embedding model to use
        **kwargs: Additional parameters for embeddings
        
    Returns:
        EncryptedTenantAwareLangChainVectorStore: Encrypted vector store instance
        
    Raises:
        VectorStoreException: If vector store creation fails
    """
    try:
        logger.info(f"Creating encrypted vector store for tenant {tenant_manager.tenant_id}")
        return EncryptedTenantAwareLangChainVectorStore(
            tenant_manager=tenant_manager,
            encryption_manager=encryption_manager,
            storage_provider=storage_provider,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            **kwargs
        )
    except Exception as e:
        raise VectorStoreException(f"Failed to create encrypted vector store: {str(e)}") from e