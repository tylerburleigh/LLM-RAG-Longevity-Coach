"""Encrypted tenant-aware vector store implementation."""

import os
import tempfile
import shutil
from typing import Optional
import logging

from coach.langchain_vector_store import TenantAwareLangChainVectorStore
from coach.tenant import TenantManager
from coach.encryption import EncryptionManager
from coach.storage.base import StorageProvider
from coach.exceptions import VectorStoreSaveException, VectorStoreLoadException

logger = logging.getLogger(__name__)


class EncryptedTenantAwareLangChainVectorStore(TenantAwareLangChainVectorStore):
    """Tenant-aware vector store with encryption support for cloud storage."""
    
    def __init__(
        self,
        tenant_manager: TenantManager,
        encryption_manager: EncryptionManager,
        storage_provider: Optional[StorageProvider] = None,
        embedding_provider: str = "openai",
        embedding_model: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the encrypted tenant-aware vector store.
        
        Args:
            tenant_manager: TenantManager instance for tenant isolation
            encryption_manager: EncryptionManager for data encryption
            storage_provider: Optional storage provider for cloud storage
            embedding_provider: Provider for embeddings ('openai' or 'google')
            embedding_model: Specific embedding model to use
            **kwargs: Additional parameters for embeddings
        """
        self.encryption_manager = encryption_manager
        self.storage_provider = storage_provider
        
        # Initialize parent class
        super().__init__(
            tenant_manager=tenant_manager,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            **kwargs
        )
        
        logger.info(
            f"Initialized encrypted vector store for tenant {tenant_manager.tenant_id}"
        )
    
    def _get_remote_faiss_path(self) -> str:
        """Get remote path for FAISS index in cloud storage."""
        return f"tenants/{self.tenant_manager.tenant_id}/vector_store/faiss_index"
    
    def _load_existing_store(self):
        """Load existing tenant-specific vector store, downloading from cloud if needed."""
        if not self.storage_provider:
            # No cloud storage, use local loading
            super()._load_existing_store()
            return
        
        faiss_path = self._get_faiss_index_path()
        remote_path = self._get_remote_faiss_path()
        
        try:
            # Check if exists in cloud storage
            if self.storage_provider.exists(remote_path):
                logger.info(
                    f"Downloading encrypted vector store from cloud for tenant "
                    f"{self.tenant_manager.tenant_id}"
                )
                
                # Create temporary directory for download
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_faiss_path = os.path.join(temp_dir, "faiss_index")
                    
                    # Download entire FAISS index directory
                    self.storage_provider.download_directory(
                        remote_path,
                        temp_faiss_path
                    )
                    
                    # Ensure local directory exists
                    os.makedirs(os.path.dirname(faiss_path), exist_ok=True)
                    
                    # Move to final location
                    if os.path.exists(faiss_path):
                        shutil.rmtree(faiss_path)
                    shutil.move(temp_faiss_path, faiss_path)
                
                # Load from local path
                super()._load_existing_store()
                
            else:
                logger.info(
                    f"No encrypted vector store found in cloud for tenant "
                    f"{self.tenant_manager.tenant_id}"
                )
                self.faiss_store = None
                self.documents = []
                
        except FileNotFoundError:
            logger.info(
                f"No existing vector store found for tenant "
                f"{self.tenant_manager.tenant_id}"
            )
            self.faiss_store = None
            self.documents = []
        except VectorStoreLoadException as e:
            logger.warning(
                f"Failed to load vector store for tenant "
                f"{self.tenant_manager.tenant_id}: {e}"
            )
            self.faiss_store = None
            self.documents = []
        except Exception as e:
            logger.error(
                f"Unexpected error loading vector store for tenant "
                f"{self.tenant_manager.tenant_id}: {e}"
            )
            self.faiss_store = None
            self.documents = []
    
    def save(self):
        """Save the tenant-specific vector store, uploading to cloud if configured."""
        if not self.faiss_store:
            logger.warning(
                f"No FAISS store to save for tenant {self.tenant_manager.tenant_id}"
            )
            return
        
        try:
            # First save locally
            super().save()
            
            # Then upload to cloud if storage provider is configured
            if self.storage_provider:
                faiss_path = self._get_faiss_index_path()
                remote_path = self._get_remote_faiss_path()
                
                logger.info(
                    f"Uploading encrypted vector store to cloud for tenant "
                    f"{self.tenant_manager.tenant_id}"
                )
                
                # Upload entire FAISS index directory
                self.storage_provider.upload_directory(
                    faiss_path,
                    remote_path
                )
                
                logger.info(
                    f"Successfully uploaded encrypted vector store for tenant "
                    f"{self.tenant_manager.tenant_id}"
                )
                
        except Exception as e:
            raise VectorStoreSaveException(
                f"Failed to save encrypted vector store for tenant "
                f"{self.tenant_manager.tenant_id}: {str(e)}"
            ) from e
    
    def clear_local_cache(self):
        """Clear local cached vector store files."""
        faiss_path = self._get_faiss_index_path()
        
        if os.path.exists(faiss_path):
            try:
                shutil.rmtree(faiss_path)
                logger.info(
                    f"Cleared local cache for tenant {self.tenant_manager.tenant_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to clear local cache for tenant "
                    f"{self.tenant_manager.tenant_id}: {e}"
                )
    
    def sync_from_cloud(self):
        """Force sync from cloud storage."""
        if self.storage_provider:
            self._load_existing_store()
        else:
            logger.warning("No storage provider configured, cannot sync from cloud")