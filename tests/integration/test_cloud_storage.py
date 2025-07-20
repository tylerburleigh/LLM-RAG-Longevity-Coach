#!/usr/bin/env python3
"""Test script for cloud storage integration."""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from coach.storage import (
    LocalStorageProvider,
    GCPStorageProvider,
    EncryptedStorageProvider,
    create_storage_provider
)
from coach.models import UserContext
from coach.encryption import EncryptionManager
from coach.config import config


import unittest


class TestLocalStorage(unittest.TestCase):
    """Test local storage provider."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.provider = LocalStorageProvider(base_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_upload_download_bytes(self):
        """Test uploading and downloading bytes."""
        test_data = b"Hello, Local Storage!"
        remote_path = "test/file.txt"
        
        # Upload
        self.provider.upload_bytes(test_data, remote_path)
        self.assertTrue(self.provider.exists(remote_path))
        
        # Download
        downloaded = self.provider.download_bytes(remote_path)
        self.assertEqual(downloaded, test_data)
    
    def test_upload_download_file(self):
        """Test uploading and downloading files."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            test_content = "Test file content"
            f.write(test_content)
            local_path = f.name
        
        try:
            remote_path = "test/uploaded_file.txt"
            
            # Upload
            self.provider.upload_file(local_path, remote_path)
            self.assertTrue(self.provider.exists(remote_path))
            
            # Download
            download_path = os.path.join(self.temp_dir, "downloaded.txt")
            self.provider.download_file(remote_path, download_path)
            
            # Verify content
            with open(download_path, 'r') as f:
                downloaded_content = f.read()
            self.assertEqual(downloaded_content, test_content)
            
        finally:
            os.remove(local_path)
    
    def test_list_files(self):
        """Test listing files."""
        # Upload multiple files
        files_to_upload = [
            ("test/file1.txt", b"Content 1"),
            ("test/file2.txt", b"Content 2"),
            ("test/subdir/file3.txt", b"Content 3"),
            ("other/file4.txt", b"Content 4")
        ]
        
        for path, content in files_to_upload:
            self.provider.upload_bytes(content, path)
        
        # List with prefix
        test_files = self.provider.list_files("test")
        self.assertIn("test/file1.txt", test_files)
        self.assertIn("test/file2.txt", test_files)
        self.assertIn("test/subdir/file3.txt", test_files)
        self.assertNotIn("other/file4.txt", test_files)
    
    def test_delete_file(self):
        """Test file deletion."""
        remote_path = "test/delete_me.txt"
        
        # Upload
        self.provider.upload_bytes(b"Delete me", remote_path)
        self.assertTrue(self.provider.exists(remote_path))
        
        # Delete
        self.provider.delete_file(remote_path)
        self.assertFalse(self.provider.exists(remote_path))


class TestEncryptedStorage(unittest.TestCase):
    """Test encrypted storage provider."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user_context = UserContext(
            user_id="test_user_123",
            email="test@example.com",
            name="Test User",
            oauth_token="mock_token",
            refresh_token="mock_refresh"
        )
        
        # Create encryption manager
        self.encryption_manager = EncryptionManager(self.user_context)
        self.encryption_manager.set_user_password("test_password_123")
        
        # Create temporary directory and providers
        self.temp_dir = tempfile.mkdtemp()
        self.base_provider = LocalStorageProvider(base_path=self.temp_dir)
        self.provider = EncryptedStorageProvider(
            self.base_provider,
            self.encryption_manager
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Clear cached keys
        from coach.key_derivation import KeyDerivationService
        KeyDerivationService.clear_user_keys(self.user_context.user_id)
    
    def test_encrypted_upload_download(self):
        """Test encrypted file operations."""
        test_data = b"Secret data that should be encrypted!"
        remote_path = "secure/data.txt"
        
        # Upload
        self.provider.upload_bytes(test_data, remote_path)
        
        # Verify file is encrypted on disk
        encrypted_path = Path(self.temp_dir) / "secure/data.txt.enc"
        self.assertTrue(encrypted_path.exists())
        
        # Verify raw data is encrypted
        raw_data = encrypted_path.read_bytes()
        self.assertNotEqual(raw_data, test_data)
        
        # Verify we can decrypt through the provider
        downloaded = self.provider.download_bytes(remote_path)
        self.assertEqual(downloaded, test_data)
    
    def test_list_files_hides_encryption(self):
        """Test that listing hides .enc extension."""
        # Upload some files
        self.provider.upload_bytes(b"Data 1", "secure/file1.txt")
        self.provider.upload_bytes(b"Data 2", "secure/file2.txt")
        
        # List files
        files = self.provider.list_files("secure")
        
        # Should show original names, not .enc
        self.assertIn("secure/file1.txt", files)
        self.assertIn("secure/file2.txt", files)
        self.assertNotIn("secure/file1.txt.enc", files)
        self.assertNotIn("secure/file2.txt.enc", files)


class TestStorageFactory(unittest.TestCase):
    """Test storage factory."""
    
    def setUp(self):
        """Save original configuration."""
        self.original_backend = config.STORAGE_BACKEND
    
    def tearDown(self):
        """Restore original configuration."""
        config.STORAGE_BACKEND = self.original_backend
    
    def test_local_storage_creation(self):
        """Test local storage creation."""
        config.STORAGE_BACKEND = "local"
        provider = create_storage_provider()
        self.assertIsInstance(provider, LocalStorageProvider)
    
    def test_encrypted_storage_creation(self):
        """Test encrypted storage creation."""
        user_context = UserContext(
            user_id="test_user_456",
            email="factory@example.com",
            name="Factory User",
            oauth_token="mock_token",
            refresh_token="mock_refresh"
        )
        
        encryption_manager = EncryptionManager(user_context)
        encryption_manager.set_user_password("factory_password")
        
        try:
            config.STORAGE_BACKEND = "local"
            encrypted_provider = create_storage_provider(
                user_context=user_context,
                enable_encryption=True
            )
            self.assertIsInstance(encrypted_provider, EncryptedStorageProvider)
        finally:
            # Clear cached keys
            from coach.key_derivation import KeyDerivationService
            KeyDerivationService.clear_user_keys(user_context.user_id)


@unittest.skipUnless(
    config.GCP_BUCKET_NAME and config.STORAGE_BACKEND == "gcp",
    "GCP credentials not configured"
)
class TestGCPStorage(unittest.TestCase):
    """Test GCP storage provider (requires GCP credentials)."""
    
    def setUp(self):
        """Set up GCP provider."""
        self.provider = GCPStorageProvider(
            bucket_name=config.GCP_BUCKET_NAME,
            credentials_path=config.GCP_CREDENTIALS_PATH
        )
        self.test_prefix = "test/integration/"
    
    def tearDown(self):
        """Clean up test files."""
        # Clean up any test files
        try:
            files = self.provider.list_files(self.test_prefix)
            for file in files:
                self.provider.delete_file(file)
        except Exception:
            pass
    
    def test_gcp_operations(self):
        """Test basic GCP operations."""
        test_data = b"Hello, GCP Storage!"
        test_path = f"{self.test_prefix}file.txt"
        
        # Upload
        self.provider.upload_bytes(test_data, test_path)
        self.assertTrue(self.provider.exists(test_path))
        
        # Download
        downloaded = self.provider.download_bytes(test_path)
        self.assertEqual(downloaded, test_data)
        
        # Delete
        self.provider.delete_file(test_path)
        self.assertFalse(self.provider.exists(test_path))


if __name__ == "__main__":
    unittest.main()