"""Base storage provider abstraction for multi-tenant cloud storage."""

import os
from abc import ABC, abstractmethod
from typing import List, Optional, BinaryIO
from pathlib import Path


class StorageProvider(ABC):
    """Abstract base class for storage providers."""
    
    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a file from local path to remote path.
        
        Args:
            local_path: Path to local file
            remote_path: Path in storage system
        
        Raises:
            StorageException: If upload fails
        """
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from remote path to local path.
        
        Args:
            remote_path: Path in storage system
            local_path: Path to save file locally
        
        Raises:
            StorageException: If download fails
        """
        pass
    
    @abstractmethod
    def delete_file(self, remote_path: str) -> None:
        """Delete a file from storage.
        
        Args:
            remote_path: Path in storage system
        
        Raises:
            StorageException: If deletion fails
        """
        pass
    
    @abstractmethod
    def exists(self, remote_path: str) -> bool:
        """Check if a file exists in storage.
        
        Args:
            remote_path: Path in storage system
        
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    def list_files(self, prefix: str) -> List[str]:
        """List all files with given prefix.
        
        Args:
            prefix: Path prefix to search
        
        Returns:
            List of file paths
        """
        pass
    
    @abstractmethod
    def upload_bytes(self, data: bytes, remote_path: str) -> None:
        """Upload bytes directly to storage.
        
        Args:
            data: Bytes to upload
            remote_path: Path in storage system
        
        Raises:
            StorageException: If upload fails
        """
        pass
    
    @abstractmethod
    def download_bytes(self, remote_path: str) -> bytes:
        """Download file as bytes.
        
        Args:
            remote_path: Path in storage system
        
        Returns:
            File contents as bytes
        
        Raises:
            StorageException: If download fails
        """
        pass
    
    @abstractmethod
    def get_file_size(self, remote_path: str) -> int:
        """Get size of file in bytes.
        
        Args:
            remote_path: Path in storage system
        
        Returns:
            File size in bytes
        
        Raises:
            StorageException: If file doesn't exist
        """
        pass
    
    def upload_directory(self, local_dir: str, remote_prefix: str) -> None:
        """Upload entire directory to storage.
        
        Args:
            local_dir: Local directory path
            remote_prefix: Remote path prefix
        """
        local_path = Path(local_dir)
        for file_path in local_path.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_path)
                remote_path = f"{remote_prefix}/{relative_path}"
                self.upload_file(str(file_path), remote_path)
    
    def download_directory(self, remote_prefix: str, local_dir: str) -> None:
        """Download entire directory from storage.
        
        Args:
            remote_prefix: Remote path prefix
            local_dir: Local directory path
        """
        os.makedirs(local_dir, exist_ok=True)
        files = self.list_files(remote_prefix)
        
        for remote_file in files:
            relative_path = remote_file.replace(remote_prefix + "/", "", 1)
            local_path = os.path.join(local_dir, relative_path)
            
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.download_file(remote_file, local_path)