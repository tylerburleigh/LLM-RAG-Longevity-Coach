"""Secure key derivation service for encryption operations."""

import hashlib
import hmac
import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import streamlit as st

from coach.models import UserContext
from coach.exceptions import EncryptionException
from coach.audit import audit


class DerivedKey:
    """Represents a derived encryption key with expiration."""
    
    def __init__(self, key: bytes, expires_at: datetime):
        """Initialize derived key.
        
        Args:
            key: The derived key bytes
            expires_at: When this key expires
        """
        self.key = key
        self.expires_at = expires_at
    
    def is_expired(self) -> bool:
        """Check if the key has expired.
        
        Returns:
            True if expired, False otherwise
        """
        return datetime.utcnow() > self.expires_at
    
    def __del__(self):
        """Securely clear key from memory when object is destroyed."""
        if hasattr(self, 'key') and self.key:
            # Overwrite key bytes with zeros
            key_len = len(self.key)
            self.key = b'\x00' * key_len


class KeyDerivationService:
    """Service for secure key derivation without storing passwords."""
    
    # Key cache with automatic expiration
    _key_cache: Dict[str, DerivedKey] = {}
    
    # Default key TTL (15 minutes)
    DEFAULT_TTL_MINUTES = 15
    
    @classmethod
    def _get_cache_key(cls, user_id: str, purpose: str = "encryption") -> str:
        """Generate cache key for user and purpose.
        
        Args:
            user_id: User identifier
            purpose: Key purpose (e.g., "encryption", "signing")
            
        Returns:
            Cache key string
        """
        return f"{user_id}:{purpose}"
    
    @classmethod
    def _cleanup_expired_keys(cls):
        """Remove expired keys from cache."""
        expired_keys = [
            key for key, derived_key in cls._key_cache.items()
            if derived_key.is_expired()
        ]
        for key in expired_keys:
            del cls._key_cache[key]
    
    @classmethod
    def get_derived_key(
        cls,
        user_context: UserContext,
        password: Optional[str] = None,
        salt: bytes = None,
        purpose: str = "encryption",
        ttl_minutes: int = DEFAULT_TTL_MINUTES
    ) -> bytes:
        """Get or derive encryption key.
        
        This method will:
        1. Check if a valid cached key exists
        2. If not, prompt for password if not provided
        3. Derive key and cache it with TTL
        
        Args:
            user_context: User context
            password: Optional password (will prompt if not provided)
            salt: Salt for key derivation
            purpose: Key purpose for caching
            ttl_minutes: Time-to-live in minutes
            
        Returns:
            Derived key bytes
            
        Raises:
            EncryptionException: If key derivation fails
        """
        # Cleanup expired keys
        cls._cleanup_expired_keys()
        
        # Check cache
        cache_key = cls._get_cache_key(user_context.user_id, purpose)
        
        if cache_key in cls._key_cache:
            derived_key = cls._key_cache[cache_key]
            if not derived_key.is_expired():
                # Audit log cache hit
                audit.log_key_derivation(
                    user_id=user_context.user_id,
                    purpose=purpose,
                    cached=True,
                    ttl_minutes=ttl_minutes
                )
                return derived_key.key
        
        # Need to derive new key
        if password is None:
            password = cls._prompt_for_password(user_context)
        
        if not password:
            raise EncryptionException("Password is required for encryption")
        
        # Derive key using PBKDF2
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.backends import default_backend
        
        if salt is None:
            # Generate default salt if not provided
            salt = hashlib.sha256(f"{user_context.user_id}:default".encode()).digest()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,
            backend=default_backend()
        )
        
        # Combine password with user context
        combined_secret = f"{password}:{user_context.email}".encode()
        key = kdf.derive(combined_secret)
        
        # Cache with expiration
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        cls._key_cache[cache_key] = DerivedKey(key, expires_at)
        
        # Clear password from memory
        password = None
        
        # Audit log key derivation
        audit.log_key_derivation(
            user_id=user_context.user_id,
            purpose=purpose,
            cached=False,
            ttl_minutes=ttl_minutes
        )
        
        return key
    
    @classmethod
    def _prompt_for_password(cls, user_context: UserContext) -> Optional[str]:
        """Prompt user for password through UI.
        
        Args:
            user_context: User context
            
        Returns:
            Password string or None
        """
        # This is a placeholder - in actual implementation,
        # this would interact with Streamlit UI to get password
        password_key = f"temp_password_prompt_{user_context.user_id}"
        
        if password_key in st.session_state:
            password = st.session_state[password_key]
            # Immediately remove from session state
            del st.session_state[password_key]
            return password
        
        return None
    
    @classmethod
    def clear_user_keys(cls, user_id: str):
        """Clear all cached keys for a user.
        
        Args:
            user_id: User identifier
        """
        keys_to_remove = [
            key for key in cls._key_cache.keys()
            if key.startswith(f"{user_id}:")
        ]
        for key in keys_to_remove:
            del cls._key_cache[key]
    
    @classmethod
    def verify_password(
        cls,
        user_context: UserContext,
        password: str,
        salt: bytes
    ) -> bool:
        """Verify if password is correct by attempting key derivation.
        
        Args:
            user_context: User context
            password: Password to verify
            salt: Salt for verification
            
        Returns:
            True if password is correct, False otherwise
        """
        try:
            # Try to derive key
            cls.get_derived_key(
                user_context=user_context,
                password=password,
                salt=salt,
                purpose="verification",
                ttl_minutes=0  # Don't cache verification keys
            )
            return True
        except Exception:
            return False