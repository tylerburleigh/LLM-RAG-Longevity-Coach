"""Storage provider system for multi-tenant cloud storage."""

from coach.storage.base import StorageProvider
from coach.storage.local import LocalStorageProvider
from coach.storage.gcp import GCPStorageProvider
from coach.storage.encrypted import EncryptedStorageProvider
from coach.storage.factory import create_storage_provider, create_tenant_storage_provider

__all__ = [
    "StorageProvider",
    "LocalStorageProvider", 
    "GCPStorageProvider",
    "EncryptedStorageProvider",
    "create_storage_provider",
    "create_tenant_storage_provider",
]