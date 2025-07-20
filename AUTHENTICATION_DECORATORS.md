# Authentication Decorators

This document describes the authentication decorators available in the longevity coach application for protecting routes and functions.

## Available Decorators

### 1. `@require_authentication`

The primary decorator for requiring user authentication.

```python
from coach.auth import require_authentication

# Simple usage
@require_authentication
def protected_function():
    return "This requires authentication"

# With custom options
@require_authentication(
    error_message="Please log in to access this feature",
    redirect_to_login=True,
    check_session_timeout=True
)
def custom_protected_function():
    return "This has custom authentication behavior"
```

**Parameters:**
- `error_message`: Custom error message for unauthenticated users
- `redirect_to_login`: Whether to show login interface (default: True)
- `show_error_message`: Whether to show error messages (default: True)
- `check_session_timeout`: Whether to validate session timeout (default: True)

### 2. `@require_role` (Placeholder)

Role-based access control decorator. Currently a placeholder for future implementation.

```python
from coach.auth import require_role

@require_role("admin")
def admin_function():
    return "This requires admin role"

@require_role(["admin", "moderator"])
def multi_role_function():
    return "This requires admin or moderator role"
```

**Parameters:**
- `required_roles`: Single role string or list of allowed roles
- `error_message`: Custom error message for insufficient permissions
- `check_authentication`: Whether to also check authentication (default: True)

### 3. `@with_rate_limiting`

Rate limiting decorator to prevent abuse.

```python
from coach.auth import with_rate_limiting

@with_rate_limiting(max_requests=10, time_window_minutes=5)
@require_authentication
def rate_limited_function():
    return "This is rate limited"
```

**Parameters:**
- `max_requests`: Maximum requests allowed in time window (default: 10)
- `time_window_minutes`: Time window in minutes (default: 1)
- `error_message`: Custom error message when rate limit is exceeded

### 4. `@audit_access`

Security auditing decorator for logging access attempts.

```python
from coach.auth import audit_access

@audit_access(log_level="INFO", include_user_info=True)
@require_authentication
def audited_function():
    return "This logs access attempts"
```

**Parameters:**
- `log_level`: Logging level for audit messages (default: "INFO")
- `include_args`: Whether to include function arguments in logs (default: False)
- `include_user_info`: Whether to include user information in logs (default: True)

### 5. `@protected_page`

Convenience decorator for protecting entire Streamlit pages.

```python
from coach.auth import protected_page

@protected_page()
def admin_page():
    st.title("Admin Dashboard")
    # Page content here
```

**Parameters:**
- `error_message`: Custom error message for unauthenticated access
- `require_fresh_session`: Whether to require a fresh session (within last hour)

## Usage Examples

### Basic Authentication

```python
from coach.auth import require_authentication

@require_authentication
def my_protected_function():
    # This function requires authentication
    return "Success"
```

### Multiple Decorators

```python
from coach.auth import require_authentication, with_rate_limiting, audit_access

@audit_access(log_level="WARNING")
@with_rate_limiting(max_requests=5, time_window_minutes=1)
@require_authentication(error_message="Please log in for this feature")
def highly_protected_function():
    # This function has multiple security layers
    return "Multi-layered protection"
```

### Page Protection

```python
from coach.auth import protected_page
import streamlit as st

@protected_page(error_message="Please log in to access the admin area")
def admin_dashboard():
    st.title("Admin Dashboard")
    st.write("This entire page is protected")
    
    # User info is automatically shown in sidebar
    # Logout button is automatically provided
```

### Manual Authentication Check

```python
from coach.auth import auth_manager

def manual_check_example():
    if auth_manager.is_authenticated():
        user_email = auth_manager.get_user_email()
        st.success(f"Welcome, {user_email}!")
    else:
        st.error("Please log in")
        auth_manager.authenticate_user()
```

## Integration with Streamlit Pages

To protect a Streamlit page, simply add the decorator to your page function:

```python
# pages/admin.py
import streamlit as st
from coach.auth import protected_page

@protected_page()
def main():
    st.title("Admin Page")
    # Your page content here

if __name__ == "__main__":
    main()
```

## Security Features

### Session Timeout
- Automatically checks session timeout based on `SESSION_TIMEOUT_HOURS` config
- Clears expired sessions and requires re-authentication

### Rate Limiting
- Tracks requests per user session within configurable time windows
- Prevents abuse and excessive API usage

### Audit Logging
- Logs all access attempts for security monitoring
- Configurable logging levels and information inclusion
- Helps track unauthorized access attempts

### Error Handling
- Comprehensive error handling with informative messages
- Graceful degradation when authentication services are unavailable
- Security-focused error messages that don't leak sensitive information

## Configuration

The decorators use the following configuration options from `coach/config.py`:

```python
# Session timeout in hours
SESSION_TIMEOUT_HOURS = 24

# OAuth configuration
GOOGLE_CLIENT_ID = "your_client_id"
GOOGLE_CLIENT_SECRET = "your_client_secret"
OAUTH_REDIRECT_URI = "http://localhost:8501/callback"
```

## Best Practices

1. **Always use `@require_authentication` first** in your decorator chain
2. **Use `@audit_access` for sensitive functions** to track access
3. **Apply rate limiting to API endpoints** and resource-intensive operations
4. **Use `@protected_page` for entire pages** rather than individual functions
5. **Test authentication flows** in development before deploying
6. **Monitor logs** for security events and unauthorized access attempts

## Error Handling

The decorators include comprehensive error handling:

- **Authentication failures**: Show user-friendly error messages
- **Session timeouts**: Automatically clear expired sessions
- **Rate limiting**: Prevent abuse with configurable limits
- **Audit logging**: Continue function execution even if logging fails
- **OAuth errors**: Handle OAuth callback errors gracefully

## Future Enhancements

- **Role-based access control**: Complete implementation of `@require_role`
- **Multi-factor authentication**: Add support for MFA
- **Advanced audit logging**: Integration with external security systems
- **Session management**: More sophisticated session handling
- **Permission granularity**: Fine-grained permission system