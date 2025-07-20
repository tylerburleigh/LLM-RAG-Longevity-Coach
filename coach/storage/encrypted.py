"""Encrypted storage provider wrapper."""

import os
import tempfile
from typing import List
from coach.storage.base import StorageProvider
from coach.encryption import EncryptionManager, EncryptionException
from coach.exceptions import StorageException
from coach.audit import audit


class EncryptedStorageProvider(StorageProvider):
    """Storage provider wrapper that encrypts all data before storing."""
    
    def __init__(self, storage_provider: StorageProvider, encryption_manager: EncryptionManager):
        """Initialize encrypted storage provider.
        
        Args:
            storage_provider: Underlying storage provider
            encryption_manager: Encryption manager instance
        """
        self.storage_provider = storage_provider
        self.encryption_manager = encryption_manager
    
    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Encrypt and upload file."""
        user_id = self.encryption_manager.user_context.user_id
        file_size = os.path.getsize(local_path) if os.path.exists(local_path) else None
        
        try:
            # Encrypt file to temporary location
            encrypted_path = self.encryption_manager.encrypt_file(local_path)
            
            try:
                # Upload encrypted file
                # Add .enc extension to remote path if not present
                if not remote_path.endswith('.enc'):
                    remote_path = f"{remote_path}.enc"
                
                self.storage_provider.upload_file(encrypted_path, remote_path)
                
                # Audit log success
                audit.log_storage_access(
                    user_id=user_id,
                    operation="upload_encrypted",
                    provider=type(self.storage_provider).__name__,
                    remote_path=remote_path,
                    success=True,
                    data_size=file_size
                )
            finally:
                # Clean up temporary encrypted file
                if os.path.exists(encrypted_path) and encrypted_path != local_path:
                    os.remove(encrypted_path)
        
        except EncryptionException as e:
            audit.log_storage_access(
                user_id=user_id,
                operation="upload_encrypted",
                provider=type(self.storage_provider).__name__,
                remote_path=remote_path,
                success=False,
                data_size=file_size,
                error="Encryption failed"
            )
            raise StorageException(f"Encryption failed during upload: {str(e)}")
        except OSError as e:
            audit.log_storage_access(
                user_id=user_id,
                operation="upload_encrypted",
                provider=type(self.storage_provider).__name__,
                remote_path=remote_path,
                success=False,
                data_size=file_size,
                error="File system error"
            )
            raise StorageException(f"File system error during upload: {str(e)}")
        except Exception as e:
            audit.log_storage_access(
                user_id=user_id,
                operation="upload_encrypted",
                provider=type(self.storage_provider).__name__,
                remote_path=remote_path,
                success=False,
                data_size=file_size,
                error="Upload failed"
            )
            raise StorageException(f"Failed to upload encrypted file: {str(e)}")
    
    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download and decrypt file."""
        user_id = self.encryption_manager.user_context.user_id
        
        try:
            # Add .enc extension if not present
            encrypted_remote_path = remote_path
            if not encrypted_remote_path.endswith('.enc'):
                encrypted_remote_path = f"{remote_path}.enc"
            
            # Download to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.enc') as tmp:
                temp_encrypted_path = tmp.name
            
            try:
                self.storage_provider.download_file(encrypted_remote_path, temp_encrypted_path)
                
                file_size = os.path.getsize(temp_encrypted_path) if os.path.exists(temp_encrypted_path) else None
                
                # Decrypt to final location
                self.encryption_manager.decrypt_file(temp_encrypted_path, local_path)
                
                # Audit log success
                audit.log_storage_access(
                    user_id=user_id,
                    operation="download_encrypted",
                    provider=type(self.storage_provider).__name__,
                    remote_path=encrypted_remote_path,
                    success=True,
                    data_size=file_size
                )
            finally:
                # Clean up temporary file
                if os.path.exists(temp_encrypted_path):
                    os.remove(temp_encrypted_path)
        
        except EncryptionException as e:
            audit.log_storage_access(
                user_id=user_id,
                operation="download_encrypted",
                provider=type(self.storage_provider).__name__,
                remote_path=encrypted_remote_path,
                success=False,
                error="Decryption failed"
            )
            raise StorageException(f"Decryption failed during download: {str(e)}")
        except OSError as e:
            audit.log_storage_access(
                user_id=user_id,
                operation="download_encrypted",
                provider=type(self.storage_provider).__name__,
                remote_path=encrypted_remote_path,
                success=False,
                error="File system error"
            )
            raise StorageException(f"File system error during download: {str(e)}")
        except Exception as e:
            audit.log_storage_access(
                user_id=user_id,
                operation="download_encrypted",
                provider=type(self.storage_provider).__name__,
                remote_path=encrypted_remote_path,
                success=False,
                error="Download failed"
            )
            raise StorageException(f"Failed to download and decrypt file: {str(e)}")
    
    def delete_file(self, remote_path: str) -> None:
        """Delete encrypted file."""
        # Add .enc extension if not present
        if not remote_path.endswith('.enc'):
            remote_path = f"{remote_path}.enc"
        
        self.storage_provider.delete_file(remote_path)
    
    def exists(self, remote_path: str) -> bool:
        """Check if encrypted file exists."""
        # Check both with and without .enc extension
        if self.storage_provider.exists(remote_path):
            return True
        
        if not remote_path.endswith('.enc'):
            return self.storage_provider.exists(f"{remote_path}.enc")
        
        return False
    
    def list_files(self, prefix: str) -> List[str]:
        """List encrypted files."""
        files = self.storage_provider.list_files(prefix)
        
        # Remove .enc extensions from results for transparency
        result = []
        for file in files:
            if file.endswith('.enc'):
                result.append(file[:-4])
            else:
                result.append(file)
        
        return result
    
    def upload_bytes(self, data: bytes, remote_path: str) -> None:
        """Encrypt and upload bytes."""
        try:
            # Encrypt bytes
            encrypted_data = self.encryption_manager.encrypt_bytes(data)
            
            # Add .enc extension if not present
            if not remote_path.endswith('.enc'):
                remote_path = f"{remote_path}.enc"
            
            # Upload encrypted bytes
            self.storage_provider.upload_bytes(encrypted_data, remote_path)
        
        except Exception as e:
            raise StorageException(f"Failed to upload encrypted bytes: {str(e)}")
    
    def download_bytes(self, remote_path: str) -> bytes:
        """Download and decrypt bytes."""
        try:
            # Add .enc extension if not present
            encrypted_remote_path = remote_path
            if not encrypted_remote_path.endswith('.enc'):
                encrypted_remote_path = f"{remote_path}.enc"
            
            # Download encrypted bytes
            encrypted_data = self.storage_provider.download_bytes(encrypted_remote_path)
            
            # Decrypt and return
            return self.encryption_manager.decrypt_bytes(encrypted_data)
        
        except Exception as e:
            raise StorageException(f"Failed to download and decrypt bytes: {str(e)}")
    
    def get_file_size(self, remote_path: str) -> int:
        """Get size of encrypted file.
        
        Note: This returns the size of the encrypted file, which will be
        larger than the original due to encryption overhead.
        """
        # Add .enc extension if not present
        if not remote_path.endswith('.enc'):
            remote_path = f"{remote_path}.enc"
        
        return self.storage_provider.get_file_size(remote_path)