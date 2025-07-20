"""Authentication module for OAuth2 integration and user context management."""

import logging
from typing import Optional, Dict, Any, Callable, TypeVar, Union
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import hmac
import base64
import time
import json
import os
from urllib.parse import quote

import streamlit as st
from google.auth.transport import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

from coach.config import config
from coach.models import UserContext
from coach.exceptions import CoachException
from coach.audit import audit

logger = logging.getLogger(__name__)

# Allow insecure transport for development
# This is needed for OAuth2 to work with localhost
if config.OAUTH_INSECURE_TRANSPORT and os.getenv('OAUTHLIB_INSECURE_TRANSPORT') != '1':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    logger.warning("Enabled insecure transport for OAuth2 development mode")


class AuthenticationException(CoachException):
    """Exception raised for authentication-related errors."""
    pass


class AuthorizationException(CoachException):
    """Exception raised for authorization-related errors."""
    pass


# Type variable for decorated functions
F = TypeVar('F', bound=Callable[..., Any])


class AuthenticationManager:
    """Manages OAuth2 authentication and user context."""
    
    def __init__(self):
        """Initialize the authentication manager."""
        self.oauth_config = self._load_oauth_config()
        self._session_timeout = timedelta(hours=config.SESSION_TIMEOUT_HOURS)
        self._state_secret = self._get_state_secret()
        
    def _load_oauth_config(self) -> Dict[str, Any]:
        """Load OAuth configuration from config.
        
        Returns:
            Dictionary containing OAuth configuration
            
        Raises:
            AuthenticationException: If OAuth config is invalid or missing
        """
        try:
            # Load OAuth client configuration
            oauth_config = {
                'client_id': config.GOOGLE_CLIENT_ID,
                'client_secret': config.GOOGLE_CLIENT_SECRET,
                'redirect_uri': config.OAUTH_REDIRECT_URI,
                'scopes': [
                    'openid',
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile'
                ],
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
            }
            
            # Validate required fields
            if oauth_config['client_id'] and oauth_config['client_secret']:
                logger.info("OAuth configuration loaded successfully")
                return oauth_config
            else:
                logger.warning("OAuth client credentials not configured")
                return {}
                
        except Exception as e:
            logger.error(f"Error loading OAuth configuration: {e}")
            raise AuthenticationException(f"Failed to load OAuth configuration: {str(e)}")
    
    def _get_state_secret(self) -> str:
        """Get or generate a secret for state parameter signing.
        
        Returns:
            A secret string for signing state parameters
        """
        # Use a combination of client secret and a fixed salt for state signing
        # This ensures the secret is consistent across sessions but unique per deployment
        if self.oauth_config.get('client_secret'):
            base_secret = self.oauth_config['client_secret']
            salt = "longevity_coach_oauth_state"
            return hashlib.sha256(f"{base_secret}:{salt}".encode()).hexdigest()
        else:
            # Fallback for development mode
            return "development_mode_secret"
    
    def _create_state_parameter(self) -> str:
        """Create a self-validating state parameter.
        
        Returns:
            A signed state parameter containing timestamp and signature
        """
        try:
            # Create state data with timestamp
            timestamp = int(time.time())
            state_data = {
                'timestamp': timestamp,
                'client_id': self.oauth_config.get('client_id', 'dev'),
                'nonce': base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8').rstrip('=')
            }
            
            # Create signature
            state_json = json.dumps(state_data, sort_keys=True)
            signature = hmac.new(
                self._state_secret.encode(),
                state_json.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Combine data and signature
            complete_state = {
                'data': state_data,
                'signature': signature
            }
            
            # Encode as URL-safe base64
            state_bytes = json.dumps(complete_state).encode()
            return base64.urlsafe_b64encode(state_bytes).decode('utf-8').rstrip('=')
            
        except Exception as e:
            logger.error(f"Error creating state parameter: {e}")
            # Fallback to simple random state
            return base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
    
    def _validate_state_parameter(self, state_param: str) -> bool:
        """Validate a state parameter.
        
        Args:
            state_param: The state parameter to validate
            
        Returns:
            True if the state is valid, False otherwise
        """
        try:
            # Add padding if needed
            missing_padding = len(state_param) % 4
            if missing_padding:
                state_param += '=' * (4 - missing_padding)
            
            # Decode the state parameter
            state_bytes = base64.urlsafe_b64decode(state_param.encode())
            complete_state = json.loads(state_bytes.decode())
            
            # Extract data and signature
            state_data = complete_state.get('data', {})
            received_signature = complete_state.get('signature', '')
            
            # Recreate signature
            state_json = json.dumps(state_data, sort_keys=True)
            expected_signature = hmac.new(
                self._state_secret.encode(),
                state_json.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Verify signature
            if not hmac.compare_digest(expected_signature, received_signature):
                logger.warning("OAuth state signature validation failed")
                return False
            
            # Check timestamp (valid for 10 minutes)
            timestamp = state_data.get('timestamp', 0)
            current_time = int(time.time())
            if current_time - timestamp > 600:  # 10 minutes
                logger.warning("OAuth state timestamp expired")
                return False
            
            # Verify client ID matches
            if state_data.get('client_id') != self.oauth_config.get('client_id', 'dev'):
                logger.warning("OAuth state client ID mismatch")
                return False
            
            logger.debug("OAuth state validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Error validating state parameter: {e}")
            return False
    
    def authenticate_user(self) -> Optional[UserContext]:
        """Handle OAuth2 flow and return user context.
        
        Returns:
            UserContext if authentication is successful, None otherwise
            
        Raises:
            AuthenticationException: If authentication fails
        """
        try:
            # Check if authentication is enabled
            if not self.oauth_config:
                logger.debug("Authentication not configured, returning None")
                return None
                
            # Check for existing valid session
            existing_context = self.get_user_context()
            if existing_context:
                return existing_context
                
            # Initialize OAuth2 flow
            flow = self._create_oauth_flow()
            
            # Handle OAuth callback if present
            if 'code' in st.query_params:
                return self._handle_oauth_callback(flow)
                
            # Generate authorization URL with our custom state
            custom_state = self._create_state_parameter()
            logger.debug(f"Creating OAuth authorization URL with scopes: {self.oauth_config.get('scopes', [])}")
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='select_account',
                state=custom_state
            )
            logger.debug(f"Authorization URL created: {auth_url}")
            
            # Display login button
            st.info("Please log in to continue")
            if st.button("Login with Google"):
                st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
                
            return None
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationException(f"Authentication failed: {str(e)}")
    
    def get_user_context(self) -> Optional[UserContext]:
        """Get current user context from session.
        
        Returns:
            UserContext if user is authenticated and session is valid, None otherwise
        """
        try:
            # Check if user context exists in session state
            if 'user_context' not in st.session_state:
                return None
                
            user_data = st.session_state['user_context']
            
            # Validate session timeout
            if 'session_created' in st.session_state:
                session_age = datetime.now() - st.session_state['session_created']
                if session_age > self._session_timeout:
                    logger.info("Session expired, clearing user context")
                    self._clear_session()
                    return None
                    
            # Reconstruct UserContext from session data
            return UserContext(
                user_id=user_data.get('user_id'),
                email=user_data.get('email'),
                name=user_data.get('name'),
                oauth_token=user_data.get('oauth_token'),
                refresh_token=user_data.get('refresh_token'),
                encryption_key=user_data.get('encryption_key')
            )
            
        except Exception as e:
            logger.error(f"Error retrieving user context: {e}")
            return None
    
    def logout(self) -> None:
        """Log out the current user and clear session."""
        try:
            # Get user context before clearing
            user_context = self.get_user_context()
            user_id = user_context.user_id if user_context else "unknown"
            
            self._clear_session()
            logger.info("User logged out successfully")
            
            # Audit log logout
            audit.log_authentication(
                user_id=user_id,
                action="logout",
                success=True,
                method="manual"
            )
            
            st.success("You have been logged out successfully")
            st.rerun()
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            raise AuthenticationException(f"Logout failed: {str(e)}")
    
    def _create_oauth_flow(self) -> Flow:
        """Create OAuth2 flow instance.
        
        Returns:
            Configured OAuth2 flow
            
        Raises:
            AuthenticationException: If flow creation fails
        """
        try:
            client_config = {
                "web": {
                    "client_id": self.oauth_config['client_id'],
                    "client_secret": self.oauth_config['client_secret'],
                    "auth_uri": self.oauth_config['auth_uri'],
                    "token_uri": self.oauth_config['token_uri'],
                    "redirect_uris": [self.oauth_config['redirect_uri']]
                }
            }
            
            flow = Flow.from_client_config(
                client_config,
                scopes=self.oauth_config['scopes'],
                redirect_uri=self.oauth_config['redirect_uri']
            )
            
            return flow
            
        except Exception as e:
            logger.error(f"Error creating OAuth flow: {e}")
            raise AuthenticationException(f"Failed to create OAuth flow: {str(e)}")
    
    def _handle_oauth_callback(self, flow: Flow) -> Optional[UserContext]:
        """Handle OAuth2 callback and create user context.
        
        Args:
            flow: OAuth2 flow instance
            
        Returns:
            UserContext if successful, None otherwise
            
        Raises:
            AuthenticationException: If callback handling fails
        """
        try:
            # Get state parameter from URL query params
            state_param = st.query_params.get('state')
            if not state_param:
                raise AuthenticationException("Missing OAuth state parameter")
                
            # Validate state parameter
            if not self._validate_state_parameter(state_param):
                raise AuthenticationException("Invalid OAuth state")
                
            # Construct authorization response URL from query parameters
            base_url = self.oauth_config.get('redirect_uri', 'http://localhost:8501/')
            query_params = []
            for key, value in st.query_params.items():
                # URL encode both key and value to handle special characters
                encoded_key = quote(str(key), safe='')
                encoded_value = quote(str(value), safe='')
                query_params.append(f"{encoded_key}={encoded_value}")
            
            authorization_response = base_url
            if query_params:
                authorization_response += "?" + "&".join(query_params)
            
            logger.debug(f"OAuth authorization response URL: {authorization_response}")
            
            # Exchange authorization code for tokens
            logger.debug(f"Fetching token with authorization response: {authorization_response}")
            flow.fetch_token(
                authorization_response=authorization_response
            )
            logger.debug("Token fetch successful")
            
            # Get user info from ID token
            credentials = flow.credentials
            request = requests.Request()
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                request,
                self.oauth_config['client_id']
            )
            
            # Create user context
            user_context = UserContext(
                user_id=id_info.get('sub'),
                email=id_info.get('email'),
                name=id_info.get('name'),
                oauth_token=credentials.token,
                refresh_token=credentials.refresh_token or "",
                encryption_key=None  # Optional encryption key
            )
            
            # Store in session
            st.session_state['user_context'] = {
                'user_id': user_context.user_id,
                'email': user_context.email,
                'name': user_context.name,
                'oauth_token': user_context.oauth_token,
                'refresh_token': user_context.refresh_token,
                'encryption_key': user_context.encryption_key
            }
            st.session_state['session_created'] = datetime.now()
            
            logger.info(f"User {user_context.email} authenticated successfully")
            
            # Audit log successful authentication
            audit.log_authentication(
                user_id=user_context.user_id,
                action="login",
                success=True,
                method="oauth2_google",
                ip_address=None  # Could be extracted from request headers if available
            )
            
            return user_context
            
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            raise AuthenticationException(f"OAuth callback failed: {str(e)}")
    
    def _clear_session(self) -> None:
        """Clear all session data related to authentication."""
        keys_to_clear = ['user_context', 'session_created']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated.
        
        Returns:
            True if user is authenticated, False otherwise
        """
        return self.get_user_context() is not None
    
    def get_user_email(self) -> Optional[str]:
        """Get the current user's email address.
        
        Returns:
            User's email if authenticated, None otherwise
        """
        user_context = self.get_user_context()
        return user_context.email if user_context else None
    
    def get_user_name(self) -> Optional[str]:
        """Get the current user's name.
        
        Returns:
            User's name if authenticated, None otherwise
        """
        user_context = self.get_user_context()
        return user_context.name if user_context else None


# Singleton instance
auth_manager = AuthenticationManager()


# Authentication Decorators
def require_authentication(
    func: F = None,
    *,
    redirect_to_login: bool = True,
    show_error_message: bool = True,
    error_message: str = "Please log in to access this page",
    check_session_timeout: bool = True
) -> Union[F, Callable[[F], F]]:
    """
    Decorator to require authentication for protected routes and functions.
    
    This decorator checks if the user is authenticated before allowing access to
    the decorated function. It provides various configuration options for handling
    unauthenticated access attempts.
    
    Args:
        func: The function to be decorated (when used without parentheses)
        redirect_to_login: Whether to show login interface for unauthenticated users
        show_error_message: Whether to show an error message to unauthenticated users
        error_message: Custom error message to display
        check_session_timeout: Whether to validate session timeout
        
    Returns:
        The decorated function or a decorator function
        
    Usage:
        @require_authentication
        def protected_function():
            pass
            
        @require_authentication(error_message="Admin access required")
        def admin_function():
            pass
    """
    def decorator(f: F) -> F:
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Check if user is authenticated
                user_context = auth_manager.get_user_context()
                
                if not user_context:
                    # Log authentication failure
                    logger.warning(f"Unauthenticated access attempt to {f.__name__}")
                    
                    if show_error_message:
                        st.error(error_message)
                    
                    if redirect_to_login:
                        # Attempt to trigger authentication flow
                        auth_manager.authenticate_user()
                    
                    # Stop execution - don't call the protected function
                    return None
                
                # Additional session timeout check if enabled
                if check_session_timeout and 'session_created' in st.session_state:
                    session_age = datetime.now() - st.session_state['session_created']
                    if session_age > timedelta(hours=config.SESSION_TIMEOUT_HOURS):
                        logger.info(f"Session timeout for user {user_context.email}")
                        
                        # Clear expired session
                        auth_manager._clear_session()
                        
                        if show_error_message:
                            st.error("Your session has expired. Please log in again.")
                        
                        if redirect_to_login:
                            auth_manager.authenticate_user()
                        
                        return None
                
                # Log successful authentication
                logger.debug(f"Authenticated access to {f.__name__} by {user_context.email}")
                
                # Call the protected function
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Authentication error in {f.__name__}: {e}")
                if show_error_message:
                    st.error(f"Authentication error: {str(e)}")
                return None
        
        return wrapper
    
    # Handle both @require_authentication and @require_authentication() syntax
    if func is None:
        # Called with parentheses: @require_authentication()
        return decorator
    else:
        # Called without parentheses: @require_authentication
        return decorator(func)


def require_role(
    required_roles: Union[str, list[str]],
    *,
    error_message: str = "You don't have permission to access this resource",
    check_authentication: bool = True
) -> Callable[[F], F]:
    """
    Decorator to require specific roles for access (placeholder for future role-based access control).
    
    This decorator provides a framework for role-based access control. Currently,
    it serves as a placeholder since the UserContext model doesn't include roles yet.
    
    Args:
        required_roles: Single role string or list of roles that are allowed access
        error_message: Error message to display when access is denied
        check_authentication: Whether to also check authentication (recommended)
        
    Returns:
        Decorated function
        
    Usage:
        @require_role("admin")
        def admin_function():
            pass
            
        @require_role(["admin", "moderator"])
        def protected_function():
            pass
    """
    def decorator(f: F) -> F:
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Check authentication first if enabled
                if check_authentication:
                    user_context = auth_manager.get_user_context()
                    if not user_context:
                        logger.warning(f"Unauthenticated access attempt to role-protected {f.__name__}")
                        st.error("Please log in to access this page")
                        auth_manager.authenticate_user()
                        return None
                
                # TODO: Implement role checking once UserContext includes roles
                # For now, log the role requirement for future implementation
                roles_list = [required_roles] if isinstance(required_roles, str) else required_roles
                logger.debug(f"Role requirement for {f.__name__}: {roles_list}")
                
                # Currently, allow access if authenticated (placeholder behavior)
                # In the future, this should check user roles against required_roles
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Role authorization error in {f.__name__}: {e}")
                st.error(f"Authorization error: {str(e)}")
                return None
        
        return wrapper
    
    return decorator


def with_rate_limiting(
    max_requests: int = 10,
    time_window_minutes: int = 1,
    error_message: str = "Too many requests. Please try again later."
) -> Callable[[F], F]:
    """
    Decorator to add rate limiting to functions for security.
    
    This decorator implements a simple rate limiting mechanism using session state
    to track requests per user session within a time window.
    
    Args:
        max_requests: Maximum number of requests allowed in the time window
        time_window_minutes: Time window in minutes for rate limiting
        error_message: Error message to display when rate limit is exceeded
        
    Returns:
        Decorated function
        
    Usage:
        @with_rate_limiting(max_requests=5, time_window_minutes=1)
        def api_endpoint():
            pass
    """
    def decorator(f: F) -> F:
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Get current user context for rate limiting key
                user_context = auth_manager.get_user_context()
                rate_limit_key = f"rate_limit_{f.__name__}"
                
                # Use user ID if available, otherwise use session ID
                if user_context:
                    rate_limit_key += f"_{user_context.user_id}"
                else:
                    # Use a session-based key for anonymous users
                    if 'session_id' not in st.session_state:
                        import uuid
                        st.session_state['session_id'] = str(uuid.uuid4())
                    rate_limit_key += f"_{st.session_state['session_id']}"
                
                # Initialize or get rate limit data
                if rate_limit_key not in st.session_state:
                    st.session_state[rate_limit_key] = {
                        'requests': [],
                        'last_reset': datetime.now()
                    }
                
                rate_data = st.session_state[rate_limit_key]
                current_time = datetime.now()
                time_window = timedelta(minutes=time_window_minutes)
                
                # Clean up old requests outside the time window
                rate_data['requests'] = [
                    req_time for req_time in rate_data['requests']
                    if current_time - req_time < time_window
                ]
                
                # Check if rate limit is exceeded
                if len(rate_data['requests']) >= max_requests:
                    logger.warning(f"Rate limit exceeded for {f.__name__} by user {user_context.email if user_context else 'anonymous'}")
                    st.error(error_message)
                    return None
                
                # Add current request to the list
                rate_data['requests'].append(current_time)
                st.session_state[rate_limit_key] = rate_data
                
                # Call the original function
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Rate limiting error in {f.__name__}: {e}")
                st.error(f"Rate limiting error: {str(e)}")
                return None
        
        return wrapper
    
    return decorator


def audit_access(
    log_level: str = "INFO",
    include_args: bool = False,
    include_user_info: bool = True
) -> Callable[[F], F]:
    """
    Decorator to audit access to sensitive functions for security monitoring.
    
    This decorator logs access attempts to functions for security auditing purposes.
    It can optionally include function arguments and user information in the logs.
    
    Args:
        log_level: Logging level for audit messages
        include_args: Whether to include function arguments in audit logs
        include_user_info: Whether to include user information in audit logs
        
    Returns:
        Decorated function
        
    Usage:
        @audit_access(log_level="WARNING")
        def sensitive_function():
            pass
    """
    def decorator(f: F) -> F:
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Prepare audit log message
                audit_msg = f"Access to {f.__name__}"
                
                # Add user information if enabled
                if include_user_info:
                    user_context = auth_manager.get_user_context()
                    if user_context:
                        audit_msg += f" by user {user_context.email} (ID: {user_context.user_id})"
                    else:
                        audit_msg += " by unauthenticated user"
                
                # Add function arguments if enabled (be careful with sensitive data)
                if include_args and args:
                    # Only include non-sensitive argument information
                    audit_msg += f" with {len(args)} arguments"
                
                # Log the audit message
                getattr(logger, log_level.lower())(audit_msg)
                
                # Call the original function
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Audit logging error in {f.__name__}: {e}")
                # Continue with function execution even if audit logging fails
                return f(*args, **kwargs)
        
        return wrapper
    
    return decorator


# Convenience function for common authentication patterns
def protected_page(
    error_message: str = "Please log in to access this page",
    require_fresh_session: bool = False
) -> Callable[[F], F]:
    """
    Convenience decorator for protecting entire Streamlit pages.
    
    This decorator combines authentication checking with page-specific behavior,
    making it easy to protect entire Streamlit pages with a single decorator.
    
    Args:
        error_message: Custom error message for unauthenticated access
        require_fresh_session: Whether to require a fresh session (within last hour)
        
    Returns:
        Decorated function
        
    Usage:
        @protected_page()
        def admin_page():
            st.title("Admin Dashboard")
            # Page content here
    """
    def decorator(f: F) -> F:
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Check authentication
                user_context = auth_manager.get_user_context()
                
                if not user_context:
                    # Create a login interface for the page
                    st.error(error_message)
                    st.info("Please log in to continue")
                    
                    # Show login interface
                    auth_manager.authenticate_user()
                    return None
                
                # Check for fresh session if required
                if require_fresh_session and 'session_created' in st.session_state:
                    session_age = datetime.now() - st.session_state['session_created']
                    if session_age > timedelta(hours=1):  # Fresh session = within last hour
                        logger.info(f"Fresh session required for {f.__name__}, current age: {session_age}")
                        st.error("This page requires a fresh session. Please log in again.")
                        auth_manager.logout()
                        return None
                
                # Add user info to sidebar for authenticated pages
                with st.sidebar:
                    st.success(f"Logged in as: {user_context.name}")
                    st.info(f"Email: {user_context.email}")
                    if st.button("Logout"):
                        auth_manager.logout()
                        return None
                
                # Call the protected page function
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Protected page error in {f.__name__}: {e}")
                st.error(f"Page access error: {str(e)}")
                return None
        
        return wrapper
    
    return decorator