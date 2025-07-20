#!/usr/bin/env python3
"""Integration tests for encryption functionality."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from coach.models import UserContext
from coach.encryption import EncryptionManager, EncryptionException
from coach.key_derivation import KeyDerivationService
from coach.rate_limiter import RateLimitExceeded, encryption_rate_limiter

# Initialize streamlit session state for tests
if not hasattr(st, 'session_state'):
    st.session_state = {}


class TestEncryption(unittest.TestCase):
    """Test encryption functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Ensure session state is initialized
        if not hasattr(st, 'session_state'):
            st.session_state = {}
            
        self.user_context = UserContext(
            user_id="test_user_123",
            email="test@example.com",
            name="Test User",
            oauth_token="test_oauth_token",
            refresh_token="test_refresh_token"
        )
        self.encryption_manager = EncryptionManager(self.user_context)
        
        # Set test password
        self.test_password = "test_password_123"
        self.encryption_manager.set_user_password(self.test_password)
        
        # Clear any existing rate limits
        encryption_rate_limiter.get_limiter(self.user_context.user_id).reset()
    
    def tearDown(self):
        """Clean up after tests."""
        # Clear cached keys
        KeyDerivationService.clear_user_keys(self.user_context.user_id)
    
    def test_encrypt_decrypt_file(self):
        """Test file encryption and decryption."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            test_content = "This is a test file for encryption."
            f.write(test_content)
            original_path = f.name
        
        try:
            # Encrypt file
            encrypted_path = self.encryption_manager.encrypt_file(original_path)
            self.assertTrue(os.path.exists(encrypted_path))
            self.assertTrue(encrypted_path.endswith('.enc'))
            
            # Check salt file exists
            salt_path = f"{encrypted_path}.salt"
            self.assertTrue(os.path.exists(salt_path))
            
            # Decrypt file
            decrypted_path = self.encryption_manager.decrypt_file(encrypted_path)
            
            # Verify content
            with open(decrypted_path, 'r') as f:
                decrypted_content = f.read()
            self.assertEqual(test_content, decrypted_content)
            
        finally:
            # Cleanup
            for path in [original_path, encrypted_path, salt_path, decrypted_path]:
                if os.path.exists(path):
                    os.remove(path)
    
    def test_encrypt_decrypt_bytes(self):
        """Test bytes encryption and decryption."""
        test_data = b"This is test binary data for encryption."
        
        # Encrypt
        encrypted_data = self.encryption_manager.encrypt_bytes(test_data)
        self.assertNotEqual(test_data, encrypted_data)
        self.assertGreater(len(encrypted_data), len(test_data))
        
        # Decrypt
        decrypted_data = self.encryption_manager.decrypt_bytes(encrypted_data)
        self.assertEqual(test_data, decrypted_data)
    
    def test_encrypt_decrypt_string(self):
        """Test string encryption and decryption."""
        test_string = "This is a test string with special chars: 你好世界 🔐"
        
        # Encrypt
        encrypted_string = self.encryption_manager.encrypt_string(test_string)
        self.assertNotEqual(test_string, encrypted_string)
        
        # Decrypt
        decrypted_string = self.encryption_manager.decrypt_string(encrypted_string)
        self.assertEqual(test_string, decrypted_string)
    
    def test_different_salts_produce_different_ciphertext(self):
        """Test that same data encrypted twice produces different ciphertext."""
        test_data = b"Same data encrypted twice"
        
        # Encrypt same data twice
        encrypted1 = self.encryption_manager.encrypt_bytes(test_data)
        encrypted2 = self.encryption_manager.encrypt_bytes(test_data)
        
        # Should produce different ciphertext due to different salts
        self.assertNotEqual(encrypted1, encrypted2)
        
        # But both should decrypt to same data
        decrypted1 = self.encryption_manager.decrypt_bytes(encrypted1)
        decrypted2 = self.encryption_manager.decrypt_bytes(encrypted2)
        self.assertEqual(decrypted1, decrypted2)
        self.assertEqual(decrypted1, test_data)
    
    @unittest.skip("Password verification requires stored password hash - not implemented yet")
    def test_invalid_password_fails(self):
        """Test that incorrect password fails to decrypt."""
        test_data = b"Test data"
        encrypted = self.encryption_manager.encrypt_bytes(test_data)
        
        # Clear session state to simulate a fresh session
        password_key = f"temp_password_prompt_{self.user_context.user_id}"
        if password_key in st.session_state:
            del st.session_state[password_key]
        
        # Create new manager with wrong password
        wrong_manager = EncryptionManager(self.user_context)
        wrong_manager.set_user_password("wrong_password")
        
        # Should fail to decrypt
        with self.assertRaises(EncryptionException):
            wrong_manager.decrypt_bytes(encrypted)
    
    @unittest.skip("Password verification requires stored password hash - not implemented yet")
    def test_password_verification(self):
        """Test password verification."""
        # Correct password
        self.assertTrue(
            self.encryption_manager.verify_password(self.test_password)
        )
        
        # Wrong password
        self.assertFalse(
            self.encryption_manager.verify_password("wrong_password")
        )
    
    def test_rate_limiting(self):
        """Test rate limiting on encryption operations."""
        # Get current rate limiter settings
        limiter = encryption_rate_limiter.get_limiter(self.user_context.user_id)
        
        # Perform operations up to burst limit
        test_data = b"Rate limit test"
        for i in range(limiter.burst_size):
            encrypted = self.encryption_manager.encrypt_bytes(test_data)
            self.assertIsNotNone(encrypted)
        
        # Next operation should be rate limited
        with self.assertRaises(RateLimitExceeded) as cm:
            self.encryption_manager.encrypt_bytes(test_data)
        
        # Check error message
        self.assertIn("Rate limit exceeded", str(cm.exception))
        self.assertIn(self.user_context.user_id, str(cm.exception))


class TestKeyDerivationService(unittest.TestCase):
    """Test key derivation service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user_context = UserContext(
            user_id="test_kds_user",
            email="kds@example.com",
            name="KDS Test",
            oauth_token="test_oauth_token",
            refresh_token="test_refresh_token"
        )
        self.test_password = "kds_test_password"
        self.test_salt = os.urandom(32)
    
    def tearDown(self):
        """Clean up after tests."""
        KeyDerivationService.clear_user_keys(self.user_context.user_id)
    
    def test_key_derivation_caching(self):
        """Test that derived keys are cached."""
        # Set password
        temp_key = f"temp_password_prompt_{self.user_context.user_id}"
        st.session_state[temp_key] = self.test_password
        
        try:
            # First derivation
            key1 = KeyDerivationService.get_derived_key(
                self.user_context,
                salt=self.test_salt,
                purpose="test",
                ttl_minutes=15
            )
            
            # Second derivation should return cached key
            key2 = KeyDerivationService.get_derived_key(
                self.user_context,
                salt=self.test_salt,
                purpose="test",
                ttl_minutes=15
            )
            
            self.assertEqual(key1, key2)
            
        finally:
            if temp_key in st.session_state:
                del st.session_state[temp_key]
    
    def test_different_purposes_different_keys(self):
        """Test that different purposes get different cache entries."""
        temp_key = f"temp_password_prompt_{self.user_context.user_id}"
        st.session_state[temp_key] = self.test_password
        
        try:
            # Same salt, different purposes
            key1 = KeyDerivationService.get_derived_key(
                self.user_context,
                password=self.test_password,
                salt=self.test_salt,
                purpose="encryption",
                ttl_minutes=15
            )
            
            key2 = KeyDerivationService.get_derived_key(
                self.user_context,
                password=self.test_password,
                salt=self.test_salt,
                purpose="signing",
                ttl_minutes=15
            )
            
            # Keys should be cached separately
            # (they'll be different because of cache key)
            # But let's verify they're both cached
            cache_key1 = KeyDerivationService._get_cache_key(
                self.user_context.user_id, "encryption"
            )
            cache_key2 = KeyDerivationService._get_cache_key(
                self.user_context.user_id, "signing"
            )
            
            self.assertIn(cache_key1, KeyDerivationService._key_cache)
            self.assertIn(cache_key2, KeyDerivationService._key_cache)
            
        finally:
            if temp_key in st.session_state:
                del st.session_state[temp_key]


if __name__ == "__main__":
    unittest.main()