"""Local file system storage provider implementation."""

import os
import shutil
from typing import List
from pathlib import Path
from coach.storage.base import StorageProvider
from coach.exceptions import StorageException
from coach.retry_utils import retry_storage_operation


class LocalStorageProvider(StorageProvider):
    """Local file system storage provider implementation."""
    
    def __init__(self, base_path: str = "storage"):
        """Initialize local storage provider.
        
        Args:
            base_path: Base directory for storage
        """
        self.base_path = Path(base_path).resolve()
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_full_path(self, remote_path: str) -> Path:
        """Get full local path for a remote path."""
        # Remove leading slash if present
        if remote_path.startswith("/"):
            remote_path = remote_path[1:]
        
        full_path = self.base_path / remote_path
        
        # Security check to prevent directory traversal
        try:
            full_path = full_path.resolve()
            if not str(full_path).startswith(str(self.base_path)):
                raise StorageException(f"Invalid path: {remote_path}")
        except Exception:
            raise StorageException(f"Invalid path: {remote_path}")
        
        return full_path
    
    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Copy file to local storage."""
        try:
            dest_path = self._get_full_path(remote_path)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, dest_path)
        except Exception as e:
            raise StorageException(f"Failed to upload file {local_path} to {remote_path}: {str(e)}")
    
    def download_file(self, remote_path: str, local_path: str) -> None:
        """Copy file from local storage."""
        try:
            source_path = self._get_full_path(remote_path)
            if not source_path.exists():
                raise StorageException(f"File not found: {remote_path}")
            
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            shutil.copy2(source_path, local_path)
        except StorageException:
            raise
        except Exception as e:
            raise StorageException(f"Failed to download file {remote_path} to {local_path}: {str(e)}")
    
    def delete_file(self, remote_path: str) -> None:
        """Delete file from local storage."""
        try:
            file_path = self._get_full_path(remote_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            raise StorageException(f"Failed to delete file {remote_path}: {str(e)}")
    
    def exists(self, remote_path: str) -> bool:
        """Check if file exists in local storage."""
        try:
            file_path = self._get_full_path(remote_path)
            return file_path.exists() and file_path.is_file()
        except:
            return False
    
    def list_files(self, prefix: str) -> List[str]:
        """List all files with given prefix."""
        try:
            prefix_path = self._get_full_path(prefix)
            
            # If prefix doesn't exist, return empty list
            if not prefix_path.exists():
                return []
            
            files = []
            
            # If prefix is a directory, list all files recursively
            if prefix_path.is_dir():
                for file_path in prefix_path.rglob("*"):
                    if file_path.is_file():
                        # Get relative path from base
                        relative_path = file_path.relative_to(self.base_path)
                        files.append(str(relative_path).replace(os.sep, "/"))
            else:
                # If prefix is a file pattern, search parent directory
                parent_dir = prefix_path.parent
                pattern = prefix_path.name
                
                if parent_dir.exists():
                    for file_path in parent_dir.glob(f"{pattern}*"):
                        if file_path.is_file():
                            relative_path = file_path.relative_to(self.base_path)
                            files.append(str(relative_path).replace(os.sep, "/"))
            
            return sorted(files)
        except Exception as e:
            raise StorageException(f"Failed to list files with prefix {prefix}: {str(e)}")
    
    def upload_bytes(self, data: bytes, remote_path: str) -> None:
        """Write bytes directly to local storage."""
        try:
            dest_path = self._get_full_path(remote_path)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(data)
        except Exception as e:
            raise StorageException(f"Failed to upload bytes to {remote_path}: {str(e)}")
    
    def download_bytes(self, remote_path: str) -> bytes:
        """Read file as bytes from local storage."""
        try:
            source_path = self._get_full_path(remote_path)
            if not source_path.exists():
                raise StorageException(f"File not found: {remote_path}")
            return source_path.read_bytes()
        except StorageException:
            raise
        except Exception as e:
            raise StorageException(f"Failed to download bytes from {remote_path}: {str(e)}")
    
    def get_file_size(self, remote_path: str) -> int:
        """Get size of file in bytes."""
        try:
            file_path = self._get_full_path(remote_path)
            if not file_path.exists():
                raise StorageException(f"File not found: {remote_path}")
            return file_path.stat().st_size
        except StorageException:
            raise
        except Exception as e:
            raise StorageException(f"Failed to get file size for {remote_path}: {str(e)}")