"""Client-side encryption module for secure data storage."""

import os
import hashlib
import tempfile
from typing import Optional, Union, Tuple
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import argon2
import streamlit as st

from coach.models import UserContext
from coach.exceptions import CoachException
from coach.key_derivation import KeyDerivationService
from coach.rate_limiter import rate_limit
from coach.audit import audit


class EncryptionException(CoachException):
    """Exception raised for encryption-related errors."""
    pass


class EncryptionManager:
    """Manages client-side encryption for user data."""
    
    def __init__(self, user_context: UserContext):
        """Initialize encryption manager.
        
        Args:
            user_context: User context with authentication info
        """
        self.user_context = user_context
    
    def _get_user_password(self) -> str:
        """Get encryption password from user.
        
        This method is deprecated in favor of KeyDerivationService.
        It's kept for backward compatibility but will be removed.
        
        Returns:
            User's encryption password
        """
        # Check if password is temporarily available for migration
        password_key = f"temp_password_prompt_{self.user_context.user_id}"
        
        if password_key in st.session_state:
            password = st.session_state[password_key]
            # Don't delete here - let KeyDerivationService handle it
            return password
        
        # Otherwise prompt for password
        raise EncryptionException(
            "Encryption password not found. Please provide your encryption password."
        )
    
    def set_user_password(self, password: str) -> None:
        """Set the user's encryption password temporarily.
        
        This stores password only temporarily for immediate use.
        The KeyDerivationService will handle secure key derivation.
        
        Args:
            password: User's encryption password
        """
        # Store temporarily for KeyDerivationService to pick up
        password_key = f"temp_password_prompt_{self.user_context.user_id}"
        st.session_state[password_key] = password
    
    def _generate_salt(self) -> bytes:
        """Generate a cryptographically secure random salt.
        
        Returns:
            32-byte random salt
        """
        return os.urandom(32)
    
    def _get_salt_path(self, data_path: str) -> str:
        """Get the path for storing salt metadata.
        
        Args:
            data_path: Path to the data file
            
        Returns:
            Path to the salt file
        """
        return f"{data_path}.salt"
    
    def _save_salt(self, data_path: str, salt: bytes) -> None:
        """Save salt to a metadata file.
        
        Args:
            data_path: Path to the data file
            salt: Salt bytes to save
        """
        salt_path = self._get_salt_path(data_path)
        with open(salt_path, 'wb') as f:
            f.write(salt)
    
    def _load_salt(self, data_path: str) -> bytes:
        """Load salt from metadata file.
        
        Args:
            data_path: Path to the data file
            
        Returns:
            Salt bytes
            
        Raises:
            EncryptionException: If salt file not found
        """
        salt_path = self._get_salt_path(data_path)
        if not os.path.exists(salt_path):
            raise EncryptionException(
                f"Salt file not found for {data_path}. "
                "This may indicate the file was encrypted with an older version."
            )
        
        with open(salt_path, 'rb') as f:
            return f.read()
    
    def _derive_encryption_key(self, salt: bytes) -> bytes:
        """Derive encryption key from user OAuth data + password + salt.
        
        Args:
            salt: Salt bytes for key derivation
            
        Returns:
            32-byte encryption key for AES-256
        """
        # Use KeyDerivationService for secure key derivation
        return KeyDerivationService.get_derived_key(
            user_context=self.user_context,
            salt=salt,
            purpose="encryption",
            ttl_minutes=15  # 15-minute TTL for encryption keys
        )
    
    def _get_fernet(self, salt: bytes) -> Fernet:
        """Get or create Fernet instance for encryption/decryption.
        
        Args:
            salt: Salt for key derivation
            
        Returns:
            Fernet instance
        """
        # Always derive fresh key with provided salt
        raw_key = self._derive_encryption_key(salt)
        
        # Fernet requires base64-encoded key
        import base64
        fernet_key = base64.urlsafe_b64encode(raw_key)
        return Fernet(fernet_key)
    
    @rate_limit()
    def encrypt_file(self, file_path: str) -> str:
        """Encrypt file and return encrypted file path.
        
        Args:
            file_path: Path to file to encrypt
        
        Returns:
            Path to encrypted file
        """
        try:
            # Read file content
            with open(file_path, 'rb') as f:
                plaintext = f.read()
            
            data_size = len(plaintext)
            
            # Generate new salt for this encryption
            salt = self._generate_salt()
            
            # Get Fernet instance with this salt
            fernet = self._get_fernet(salt)
            
            # Encrypt content
            ciphertext = fernet.encrypt(plaintext)
            
            # Save encrypted file
            encrypted_path = f"{file_path}.enc"
            with open(encrypted_path, 'wb') as f:
                f.write(ciphertext)
            
            # Save salt metadata
            self._save_salt(encrypted_path, salt)
            
            # Audit log success
            audit.log_encryption_operation(
                user_id=self.user_context.user_id,
                operation="encrypt_file",
                file_path=file_path,
                data_size=data_size,
                success=True
            )
            
            return encrypted_path
        
        except Exception as e:
            # Audit log failure
            audit.log_encryption_operation(
                user_id=self.user_context.user_id,
                operation="encrypt_file",
                file_path=file_path,
                success=False,
                error=str(e)
            )
            raise EncryptionException(f"Failed to encrypt file {file_path}: {str(e)}")
    
    @rate_limit()
    def decrypt_file(self, encrypted_path: str, output_path: Optional[str] = None) -> str:
        """Decrypt file and return decrypted file path.
        
        Args:
            encrypted_path: Path to encrypted file
            output_path: Optional path for decrypted file
        
        Returns:
            Path to decrypted file
        """
        try:
            # Load salt for this file
            salt = self._load_salt(encrypted_path)
            
            # Read encrypted content
            with open(encrypted_path, 'rb') as f:
                ciphertext = f.read()
            
            data_size = len(ciphertext)
            
            # Get Fernet instance with loaded salt
            fernet = self._get_fernet(salt)
            
            # Decrypt content
            plaintext = fernet.decrypt(ciphertext)
            
            # Determine output path
            if not output_path:
                # Remove .enc extension if present
                if encrypted_path.endswith('.enc'):
                    output_path = encrypted_path[:-4]
                else:
                    # Create temporary file
                    fd, output_path = tempfile.mkstemp()
                    os.close(fd)
            
            # Save decrypted content
            with open(output_path, 'wb') as f:
                f.write(plaintext)
            
            # Audit log success
            audit.log_encryption_operation(
                user_id=self.user_context.user_id,
                operation="decrypt_file",
                file_path=encrypted_path,
                data_size=data_size,
                success=True
            )
            
            return output_path
        
        except Exception as e:
            # Audit log failure
            audit.log_encryption_operation(
                user_id=self.user_context.user_id,
                operation="decrypt_file",
                file_path=encrypted_path,
                success=False,
                error=str(e)
            )
            raise EncryptionException(f"Failed to decrypt file {encrypted_path}: {str(e)}")
    
    @rate_limit()
    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypt bytes directly.
        
        The salt is prepended to the encrypted data in the format:
        [salt_length:4 bytes][salt:32 bytes][encrypted_data]
        
        Args:
            data: Bytes to encrypt
        
        Returns:
            Encrypted bytes with salt prepended
        """
        try:
            # Generate new salt
            salt = self._generate_salt()
            
            # Get Fernet instance with this salt
            fernet = self._get_fernet(salt)
            
            # Encrypt data
            encrypted_data = fernet.encrypt(data)
            
            # Prepend salt length and salt to encrypted data
            salt_length = len(salt).to_bytes(4, byteorder='big')
            return salt_length + salt + encrypted_data
            
        except Exception as e:
            raise EncryptionException(f"Failed to encrypt data: {str(e)}")
    
    @rate_limit()
    def decrypt_bytes(self, ciphertext: bytes) -> bytes:
        """Decrypt bytes directly.
        
        Expects salt to be prepended in the format:
        [salt_length:4 bytes][salt:32 bytes][encrypted_data]
        
        Args:
            ciphertext: Encrypted bytes with salt prepended
        
        Returns:
            Decrypted bytes
        """
        try:
            # Extract salt length (first 4 bytes)
            if len(ciphertext) < 4:
                raise EncryptionException("Invalid encrypted data: too short")
            
            salt_length = int.from_bytes(ciphertext[:4], byteorder='big')
            
            # Validate and extract salt
            if len(ciphertext) < 4 + salt_length:
                raise EncryptionException("Invalid encrypted data: salt missing")
            
            salt = ciphertext[4:4 + salt_length]
            encrypted_data = ciphertext[4 + salt_length:]
            
            # Get Fernet instance with extracted salt
            fernet = self._get_fernet(salt)
            
            # Decrypt data
            return fernet.decrypt(encrypted_data)
            
        except Exception as e:
            raise EncryptionException(f"Failed to decrypt data: {str(e)}")
    
    def encrypt_string(self, text: str) -> str:
        """Encrypt a string.
        
        Args:
            text: String to encrypt
        
        Returns:
            Base64-encoded encrypted string
        """
        import base64
        encrypted_bytes = self.encrypt_bytes(text.encode('utf-8'))
        return base64.b64encode(encrypted_bytes).decode('ascii')
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """Decrypt a string.
        
        Args:
            encrypted_text: Base64-encoded encrypted string
        
        Returns:
            Decrypted string
        """
        import base64
        encrypted_bytes = base64.b64decode(encrypted_text.encode('ascii'))
        decrypted_bytes = self.decrypt_bytes(encrypted_bytes)
        return decrypted_bytes.decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        """Verify if the provided password is correct.
        
        Args:
            password: Password to verify
        
        Returns:
            True if password is correct, False otherwise
        """
        try:
            # Generate a test salt for verification
            test_salt = self._generate_salt()
            
            # Use KeyDerivationService to verify
            result = KeyDerivationService.verify_password(
                user_context=self.user_context,
                password=password,
                salt=test_salt
            )
            
            # Audit log verification attempt
            audit.log_authentication(
                user_id=self.user_context.user_id,
                action="password_verify",
                success=result,
                method="encryption_manager"
            )
            
            return result
            
        except Exception:
            # Audit log failure
            audit.log_authentication(
                user_id=self.user_context.user_id,
                action="password_verify",
                success=False,
                method="encryption_manager"
            )
            return False
    
    def clear_cached_keys(self) -> None:
        """Clear all cached encryption keys for the user.
        
        This should be called on logout or when user wants to clear keys.
        """
        KeyDerivationService.clear_user_keys(self.user_context.user_id)