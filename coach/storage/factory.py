"""Storage provider factory for creating the appropriate storage backend."""

from typing import Optional
from coach.config import config
from coach.storage.base import StorageProvider
from coach.storage.local import LocalStorageProvider
from coach.storage.gcp import GCPStorageProvider
from coach.storage.encrypted import EncryptedStorageProvider
from coach.encryption import EncryptionManager
from coach.models import UserContext
from coach.exceptions import ConfigurationException


def create_storage_provider(
    user_context: Optional[UserContext] = None,
    enable_encryption: Optional[bool] = None
) -> StorageProvider:
    """Create the appropriate storage provider based on configuration.
    
    Args:
        user_context: Optional user context for encryption
        enable_encryption: Override encryption setting
    
    Returns:
        Configured storage provider instance
    """
    # Determine base storage provider
    backend = config.STORAGE_BACKEND.lower()
    
    if backend == "gcp":
        if not config.GCP_BUCKET_NAME:
            raise ConfigurationException("GCP_BUCKET_NAME must be set when using GCP storage")
        
        base_provider = GCPStorageProvider(
            bucket_name=config.GCP_BUCKET_NAME,
            credentials_path=config.GCP_CREDENTIALS_PATH
        )
    elif backend == "local":
        base_provider = LocalStorageProvider(
            base_path=config.USER_DATA_ROOT
        )
    else:
        raise ConfigurationException(f"Unknown storage backend: {backend}")
    
    # Determine if encryption should be enabled
    if enable_encryption is None:
        enable_encryption = config.ENABLE_ENCRYPTION
    
    # Wrap with encryption if enabled and user context provided
    if enable_encryption and user_context:
        encryption_manager = EncryptionManager(user_context)
        return EncryptedStorageProvider(base_provider, encryption_manager)
    
    return base_provider


def create_tenant_storage_provider(
    user_context: UserContext,
    tenant_id: str
) -> StorageProvider:
    """Create a tenant-aware storage provider.
    
    Args:
        user_context: User context for authentication
        tenant_id: Tenant identifier
    
    Returns:
        Configured storage provider with tenant isolation
    """
    # Get base provider with encryption if enabled
    storage_provider = create_storage_provider(
        user_context=user_context,
        enable_encryption=config.ENABLE_ENCRYPTION
    )
    
    # For cloud storage, we handle tenant isolation through path prefixes
    # The TenantManager will handle adding the tenant prefix to paths
    
    return storage_provider