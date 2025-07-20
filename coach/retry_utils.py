"""Retry utilities for handling transient failures."""

import logging
from typing import Type, Tuple, Callable, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_log,
    after_log,
)

from coach.exceptions import StorageException

logger = logging.getLogger(__name__)


# Default retry configuration
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_WAIT_MIN = 1  # 1 second
DEFAULT_WAIT_MAX = 10  # 10 seconds
DEFAULT_WAIT_MULTIPLIER = 2


def is_retryable_exception(exception: Exception) -> bool:
    """Determine if an exception is retryable.
    
    Args:
        exception: The exception to check
        
    Returns:
        True if the exception is retryable, False otherwise
    """
    # Network-related errors
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return True
    
    # Storage exceptions with specific messages
    if isinstance(exception, StorageException):
        error_msg = str(exception).lower()
        retryable_keywords = [
            "timeout",
            "connection",
            "temporary",
            "unavailable",
            "rate limit",
            "throttl",
            "retry",
            "503",
            "504",
            "429"
        ]
        return any(keyword in error_msg for keyword in retryable_keywords)
    
    # Google Cloud specific retryable errors
    exception_name = type(exception).__name__
    if exception_name in ["ServiceUnavailable", "TooManyRequests", "InternalServerError"]:
        return True
    
    return False


def retry_on_transient_errors(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    wait_min: int = DEFAULT_WAIT_MIN,
    wait_max: int = DEFAULT_WAIT_MAX,
    wait_multiplier: int = DEFAULT_WAIT_MULTIPLIER,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """Create a retry decorator for transient errors.
    
    Args:
        max_attempts: Maximum number of retry attempts
        wait_min: Minimum wait time between retries (seconds)
        wait_max: Maximum wait time between retries (seconds)
        wait_multiplier: Exponential backoff multiplier
        retry_exceptions: Tuple of exception types to retry on
        
    Returns:
        Retry decorator
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=wait_multiplier,
            min=wait_min,
            max=wait_max
        ),
        retry=retry_if_exception_type(retry_exceptions) | retry_if_exception(is_retryable_exception),
        before=before_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG),
        reraise=True
    )


def retry_if_exception(predicate: Callable[[Exception], bool]) -> Any:
    """Retry if the exception matches the predicate.
    
    Args:
        predicate: Function that returns True if exception should be retried
        
    Returns:
        Tenacity retry condition
    """
    def check_exception(retry_state) -> bool:
        if retry_state.outcome.failed:
            return predicate(retry_state.outcome.exception())
        return False
    
    return check_exception


# Pre-configured decorators for common use cases
retry_storage_operation = retry_on_transient_errors(
    retry_exceptions=(StorageException, ConnectionError, TimeoutError)
)

retry_network_operation = retry_on_transient_errors(
    max_attempts=5,
    wait_min=2,
    wait_max=30,
    retry_exceptions=(ConnectionError, TimeoutError)
)