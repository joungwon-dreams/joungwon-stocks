"""
Retry Logic - Handle transient failures with exponential backoff
"""
import asyncio
import logging
from functools import wraps
from typing import Callable, Type, Tuple

logger = logging.getLogger(__name__)


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for async functions to retry on failure with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each attempt (exponential backoff)
        exceptions: Tuple of exception types to catch and retry

    Usage:
        @async_retry(max_attempts=3, delay=1.0, backoff=2.0)
        async def fetch_data():
            # Your code that might fail
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )

                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # Should never reach here, but just in case
            raise last_exception

        return wrapper
    return decorator


class RetryConfig:
    """Configuration for retry behavior"""

    # Network-related errors (connection, timeout)
    NETWORK_EXCEPTIONS = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )

    # Default retry configs for different scenarios
    QUICK_RETRY = {
        'max_attempts': 2,
        'delay': 0.5,
        'backoff': 1.5
    }

    STANDARD_RETRY = {
        'max_attempts': 3,
        'delay': 1.0,
        'backoff': 2.0
    }

    PERSISTENT_RETRY = {
        'max_attempts': 5,
        'delay': 2.0,
        'backoff': 2.0
    }


# Convenience decorators
def quick_retry(func):
    """Quick retry for minor transient failures"""
    return async_retry(**RetryConfig.QUICK_RETRY)(func)


def standard_retry(func):
    """Standard retry for most use cases"""
    return async_retry(**RetryConfig.STANDARD_RETRY)(func)


def persistent_retry(func):
    """Persistent retry for critical operations"""
    return async_retry(**RetryConfig.PERSISTENT_RETRY)(func)
