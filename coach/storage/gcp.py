"""Google Cloud Storage provider implementation."""

import os
import logging
from typing import List, Optional
from google.cloud import storage
from google.cloud.exceptions import NotFound
from coach.storage.base import StorageProvider
from coach.exceptions import StorageException
from coach.retry_utils import retry_storage_operation
from coach.audit import audit

logger = logging.getLogger(__name__)


class GCPStorageProvider(StorageProvider):
    """Google Cloud Storage provider implementation with connection pooling."""
    
    # Class-level client pool
    _client_pool = {}
    _pool_lock = None
    
    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        """Initialize GCP storage provider.
        
        Args:
            bucket_name: Name of GCS bucket
            credentials_path: Path to service account JSON file (optional)
        """
        # Initialize thread lock if needed
        if GCPStorageProvider._pool_lock is None:
            import threading
            GCPStorageProvider._pool_lock = threading.Lock()
        
        self.bucket_name = bucket_name
        self.credentials_path = credentials_path
        
        # Get or create pooled client
        self.client = self._get_pooled_client(credentials_path)
        
        try:
            self.bucket = self.client.bucket(bucket_name)
            # Test bucket access
            self.bucket.reload()
        except Exception as e:
            # Log full error details for debugging
            logger.error(f"Failed to access GCS bucket {bucket_name}: {str(e)}")
            # Return sanitized error to user
            raise StorageException(
                "Failed to access storage bucket. Please check your configuration."
            )
    
    @classmethod
    def _get_pooled_client(cls, credentials_path: Optional[str] = None) -> storage.Client:
        """Get or create a pooled storage client.
        
        Args:
            credentials_path: Path to service account JSON file
            
        Returns:
            Pooled storage client
        """
        # Use credentials path as pool key (None for default credentials)
        pool_key = credentials_path or "default"
        
        with cls._pool_lock:
            if pool_key not in cls._client_pool:
                logger.info(f"Creating new GCS client for pool key: {pool_key}")
                if credentials_path:
                    client = storage.Client.from_service_account_json(credentials_path)
                else:
                    # Use default credentials
                    client = storage.Client()
                cls._client_pool[pool_key] = client
            
            return cls._client_pool[pool_key]
    
    @classmethod
    def clear_client_pool(cls):
        """Clear the client connection pool.
        
        This should be called during application shutdown.
        """
        with cls._pool_lock:
            for key, client in cls._client_pool.items():
                try:
                    client.close()
                except Exception as e:
                    logger.warning(f"Error closing GCS client {key}: {e}")
            cls._client_pool.clear()
            logger.info("GCS client pool cleared")
    
    @retry_storage_operation
    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a file to GCS with retry logic."""
        try:
            blob = self.bucket.blob(remote_path)
            blob.upload_from_filename(local_path)
        except Exception as e:
            logger.error(f"Failed to upload {local_path} to {remote_path}: {str(e)}")
            raise StorageException("Failed to upload file to storage.")
    
    @retry_storage_operation
    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from GCS with retry logic."""
        try:
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            blob = self.bucket.blob(remote_path)
            blob.download_to_filename(local_path)
        except NotFound:
            raise StorageException("File not found in storage.")
        except Exception as e:
            logger.error(f"Failed to download {remote_path} to {local_path}: {str(e)}")
            raise StorageException("Failed to download file from storage.")
    
    def delete_file(self, remote_path: str) -> None:
        """Delete a file from GCS."""
        try:
            blob = self.bucket.blob(remote_path)
            blob.delete()
        except NotFound:
            # Ignore if file doesn't exist
            pass
        except Exception as e:
            logger.error(f"Failed to delete {remote_path}: {str(e)}")
            raise StorageException("Failed to delete file from storage.")
    
    def exists(self, remote_path: str) -> bool:
        """Check if a file exists in GCS."""
        blob = self.bucket.blob(remote_path)
        return blob.exists()
    
    @retry_storage_operation
    def list_files(self, prefix: str) -> List[str]:
        """List all files with given prefix with retry logic."""
        try:
            blobs = self.bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Failed to list files with prefix {prefix}: {str(e)}")
            raise StorageException("Failed to list files from storage.")
    
    @retry_storage_operation
    def upload_bytes(self, data: bytes, remote_path: str) -> None:
        """Upload bytes directly to GCS with retry logic."""
        try:
            blob = self.bucket.blob(remote_path)
            blob.upload_from_string(data)
        except Exception as e:
            logger.error(f"Failed to upload bytes to {remote_path}: {str(e)}")
            raise StorageException("Failed to upload data to storage.")
    
    @retry_storage_operation
    def download_bytes(self, remote_path: str) -> bytes:
        """Download file as bytes from GCS with retry logic."""
        try:
            blob = self.bucket.blob(remote_path)
            return blob.download_as_bytes()
        except NotFound:
            raise StorageException("File not found in storage.")
        except Exception as e:
            logger.error(f"Failed to download bytes from {remote_path}: {str(e)}")
            raise StorageException("Failed to download data from storage.")
    
    def get_file_size(self, remote_path: str) -> int:
        """Get size of file in bytes."""
        try:
            blob = self.bucket.blob(remote_path)
            blob.reload()
            if blob.size is None:
                raise StorageException("Could not determine file size.")
            return blob.size
        except NotFound:
            raise StorageException("File not found in storage.")
        except Exception as e:
            logger.error(f"Failed to get file size for {remote_path}: {str(e)}")
            raise StorageException("Failed to retrieve file information.")
    
    def create_signed_url(self, remote_path: str, expiration_minutes: int = 60) -> str:
        """Create a signed URL for temporary access to a file.
        
        Args:
            remote_path: Path in storage system
            expiration_minutes: URL expiration time in minutes
        
        Returns:
            Signed URL string
        """
        from datetime import timedelta
        
        blob = self.bucket.blob(remote_path)
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET"
        )
        return url