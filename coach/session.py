"""Session management for the coach package.

This module provides session management functionality for handling user context
and authentication throughout the application lifecycle.
"""

import streamlit as st
from typing import Optional
from datetime import datetime, timedelta

from .models import UserContext
from .config import config
from .exceptions import CoachException


class SessionException(CoachException):
    """Base exception for session-related errors."""
    pass


class SessionExpiredException(SessionException):
    """Raised when a user session has expired."""
    pass


class SessionManager:
    """Manages user sessions and context throughout the application."""
    
    def __init__(self):
        """Initialize the session manager."""
        self.session_key = "user_context"
        self.session_timestamp_key = "session_timestamp"
        self.session_timeout_hours = config.SESSION_TIMEOUT_HOURS
    
    def set_user_context(self, user_context: UserContext) -> None:
        """Set the user context in the session.
        
        Args:
            user_context: The user context to store in the session.
        """
        st.session_state[self.session_key] = user_context
        st.session_state[self.session_timestamp_key] = datetime.now()
    
    def get_user_context(self) -> Optional[UserContext]:
        """Get the user context from the session.
        
        Returns:
            The user context if available and not expired, None otherwise.
            
        Raises:
            SessionExpiredException: If the session has expired.
        """
        if not self._is_session_valid():
            if self._has_session():
                self.clear_session()
                raise SessionExpiredException("Session has expired")
            return None
        
        return st.session_state.get(self.session_key)
    
    def clear_session(self) -> None:
        """Clear the user context and session data."""
        if self.session_key in st.session_state:
            del st.session_state[self.session_key]
        if self.session_timestamp_key in st.session_state:
            del st.session_state[self.session_timestamp_key]
    
    def is_authenticated(self) -> bool:
        """Check if the user is authenticated and session is valid.
        
        Returns:
            True if user is authenticated and session is valid, False otherwise.
        """
        try:
            user_context = self.get_user_context()
            return user_context is not None
        except SessionExpiredException:
            return False
    
    def get_user_id(self) -> Optional[str]:
        """Get the user ID from the current session.
        
        Returns:
            The user ID if available, None otherwise.
        """
        user_context = self.get_user_context()
        return user_context.user_id if user_context else None
    
    def get_user_email(self) -> Optional[str]:
        """Get the user email from the current session.
        
        Returns:
            The user email if available, None otherwise.
        """
        user_context = self.get_user_context()
        return user_context.email if user_context else None
    
    def get_user_name(self) -> Optional[str]:
        """Get the user name from the current session.
        
        Returns:
            The user name if available, None otherwise.
        """
        user_context = self.get_user_context()
        return user_context.name if user_context else None
    
    def refresh_session(self) -> None:
        """Refresh the session timestamp to extend the session lifetime."""
        if self._has_session():
            st.session_state[self.session_timestamp_key] = datetime.now()
    
    def get_session_remaining_time(self) -> Optional[timedelta]:
        """Get the remaining time before session expires.
        
        Returns:
            Time remaining until session expires, None if no active session.
        """
        if not self._has_session():
            return None
        
        session_time = st.session_state.get(self.session_timestamp_key)
        if not session_time:
            return None
        
        expiry_time = session_time + timedelta(hours=self.session_timeout_hours)
        remaining = expiry_time - datetime.now()
        
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    def _has_session(self) -> bool:
        """Check if there is an active session (regardless of expiry).
        
        Returns:
            True if session exists, False otherwise.
        """
        return (
            self.session_key in st.session_state and
            self.session_timestamp_key in st.session_state
        )
    
    def _is_session_valid(self) -> bool:
        """Check if the current session is valid and not expired.
        
        Returns:
            True if session is valid and not expired, False otherwise.
        """
        if not self._has_session():
            return False
        
        session_time = st.session_state.get(self.session_timestamp_key)
        if not session_time:
            return False
        
        expiry_time = session_time + timedelta(hours=self.session_timeout_hours)
        return datetime.now() < expiry_time
    
    def get_oauth_token(self) -> Optional[str]:
        """Get the OAuth access token from the current session.
        
        Returns:
            The OAuth access token if available, None otherwise.
        """
        user_context = self.get_user_context()
        return user_context.oauth_token if user_context else None
    
    def get_refresh_token(self) -> Optional[str]:
        """Get the OAuth refresh token from the current session.
        
        Returns:
            The OAuth refresh token if available, None otherwise.
        """
        user_context = self.get_user_context()
        return user_context.refresh_token if user_context else None
    
    def update_oauth_tokens(self, oauth_token: str, refresh_token: str) -> None:
        """Update the OAuth tokens in the current session.
        
        Args:
            oauth_token: The new OAuth access token.
            refresh_token: The new OAuth refresh token.
            
        Raises:
            SessionException: If no active session exists.
        """
        user_context = self.get_user_context()
        if not user_context:
            raise SessionException("No active session to update tokens")
        
        # Create a new user context with updated tokens
        updated_context = UserContext(
            user_id=user_context.user_id,
            email=user_context.email,
            name=user_context.name,
            oauth_token=oauth_token,
            refresh_token=refresh_token,
            encryption_key=user_context.encryption_key
        )
        
        self.set_user_context(updated_context)


# Create a singleton instance
session_manager = SessionManager()