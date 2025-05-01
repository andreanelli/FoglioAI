"""Error handling utilities."""
import functools
import logging
import time
from typing import Any, Callable, Optional, Type, TypeVar

import redis

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ValidationError(Exception):
    """Base exception for validation errors."""

    pass


class RetryError(Exception):
    """Exception raised when retry attempts are exhausted."""

    pass


def retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (redis.RedisError,),
) -> Callable:
    """Retry decorator for Redis operations.

    Args:
        retries (int, optional): Maximum number of retries. Defaults to 3.
        delay (float, optional): Initial delay between retries in seconds. Defaults to 1.0.
        backoff (float, optional): Backoff multiplier for delay. Defaults to 2.0.
        exceptions (tuple[Type[Exception], ...], optional): Exceptions to catch.
            Defaults to (redis.RedisError,).

    Returns:
        Callable: Decorated function

    Raises:
        RetryError: If all retry attempts are exhausted
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_error: Optional[Exception] = None

            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt == retries - 1:
                        break

                    logger.warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %.1f seconds...",
                        attempt + 1,
                        retries,
                        func.__name__,
                        str(e),
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

            raise RetryError(
                f"Failed after {retries} attempts: {str(last_error)}"
            ) from last_error

        return wrapper

    return decorator 