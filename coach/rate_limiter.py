"""Rate limiting implementation for encryption operations."""

import time
import logging
from typing import Dict, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
from collections import deque
import threading

from coach.exceptions import CoachException
from coach.audit import audit

logger = logging.getLogger(__name__)


class RateLimitExceeded(CoachException):
    """Exception raised when rate limit is exceeded."""
    pass


class RateLimiter:
    """Token bucket rate limiter for encryption operations."""
    
    def __init__(
        self,
        max_calls: int,
        time_window: int,
        burst_size: Optional[int] = None
    ):
        """Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in time window
            time_window: Time window in seconds
            burst_size: Maximum burst size (defaults to max_calls)
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.burst_size = burst_size or max_calls
        
        # Thread-safe tracking
        self._lock = threading.Lock()
        self._call_times = deque()
        
        # Token bucket for burst handling
        self._tokens = float(self.burst_size)
        self._last_update = time.time()
        self._refill_rate = max_calls / time_window
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        
        # Add tokens based on refill rate
        self._tokens = min(
            self.burst_size,
            self._tokens + (elapsed * self._refill_rate)
        )
        self._last_update = now
    
    def _cleanup_old_calls(self):
        """Remove calls outside the time window."""
        cutoff_time = time.time() - self.time_window
        while self._call_times and self._call_times[0] < cutoff_time:
            self._call_times.popleft()
    
    def is_allowed(self) -> bool:
        """Check if a call is allowed under rate limits.
        
        Returns:
            True if allowed, False otherwise
        """
        with self._lock:
            # Refill tokens
            self._refill_tokens()
            
            # Cleanup old calls
            self._cleanup_old_calls()
            
            # Check if we have tokens available
            if self._tokens >= 1:
                # Use a token
                self._tokens -= 1
                self._call_times.append(time.time())
                return True
            
            return False
    
    def wait_if_needed(self) -> float:
        """Calculate wait time if rate limit exceeded.
        
        Returns:
            Wait time in seconds (0 if no wait needed)
        """
        with self._lock:
            self._refill_tokens()
            self._cleanup_old_calls()
            
            if self._tokens >= 1:
                return 0.0
            
            # Calculate time until next token
            tokens_needed = 1 - self._tokens
            wait_time = tokens_needed / self._refill_rate
            
            return wait_time
    
    def reset(self):
        """Reset the rate limiter."""
        with self._lock:
            self._call_times.clear()
            self._tokens = float(self.burst_size)
            self._last_update = time.time()


class UserRateLimiter:
    """Per-user rate limiting."""
    
    def __init__(
        self,
        max_calls_per_user: int = 100,
        time_window: int = 3600,  # 1 hour
        burst_size: Optional[int] = None
    ):
        """Initialize per-user rate limiter.
        
        Args:
            max_calls_per_user: Max calls per user in time window
            time_window: Time window in seconds
            burst_size: Maximum burst size per user
        """
        self.max_calls_per_user = max_calls_per_user
        self.time_window = time_window
        self.burst_size = burst_size
        
        # User-specific rate limiters
        self._user_limiters: Dict[str, RateLimiter] = {}
        self._lock = threading.Lock()
    
    def get_limiter(self, user_id: str) -> RateLimiter:
        """Get or create rate limiter for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            RateLimiter instance for user
        """
        with self._lock:
            if user_id not in self._user_limiters:
                self._user_limiters[user_id] = RateLimiter(
                    max_calls=self.max_calls_per_user,
                    time_window=self.time_window,
                    burst_size=self.burst_size
                )
            return self._user_limiters[user_id]
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if user is allowed to make a call.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if allowed, False otherwise
        """
        limiter = self.get_limiter(user_id)
        return limiter.is_allowed()
    
    def cleanup_inactive_users(self, inactive_hours: int = 24):
        """Remove rate limiters for inactive users.
        
        Args:
            inactive_hours: Hours of inactivity before cleanup
        """
        with self._lock:
            cutoff_time = time.time() - (inactive_hours * 3600)
            
            inactive_users = []
            for user_id, limiter in self._user_limiters.items():
                with limiter._lock:
                    if not limiter._call_times or limiter._call_times[-1] < cutoff_time:
                        inactive_users.append(user_id)
            
            for user_id in inactive_users:
                del self._user_limiters[user_id]
                logger.info(f"Cleaned up rate limiter for inactive user: {user_id}")


# Global rate limiter for encryption operations
encryption_rate_limiter = UserRateLimiter(
    max_calls_per_user=100,  # 100 operations per hour
    time_window=3600,        # 1 hour
    burst_size=10           # Allow burst of 10 operations
)


def rate_limit(
    limiter: Optional[UserRateLimiter] = None,
    user_id_getter: Optional[Callable] = None,
    raise_on_limit: bool = True
):
    """Decorator for rate limiting functions.
    
    Args:
        limiter: Rate limiter to use (defaults to encryption_rate_limiter)
        user_id_getter: Function to get user ID from arguments
        raise_on_limit: Whether to raise exception on limit
        
    Returns:
        Decorated function
    """
    if limiter is None:
        limiter = encryption_rate_limiter
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get user ID
            if user_id_getter:
                user_id = user_id_getter(*args, **kwargs)
            else:
                # Try to get from first argument if it has user_context
                if args and hasattr(args[0], 'user_context'):
                    user_id = args[0].user_context.user_id
                else:
                    user_id = "anonymous"
            
            # Check rate limit
            if not limiter.is_allowed(user_id):
                wait_time = limiter.get_limiter(user_id).wait_if_needed()
                
                # Audit log rate limit exceeded
                audit.log_rate_limit(
                    user_id=user_id,
                    operation=func.__name__,
                    allowed=False,
                    wait_time=wait_time
                )
                
                if raise_on_limit:
                    raise RateLimitExceeded(
                        f"Rate limit exceeded for user {user_id}. "
                        f"Please wait {wait_time:.1f} seconds."
                    )
                else:
                    logger.warning(f"Rate limit exceeded for user {user_id}")
                    return None
            
            # Execute function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator