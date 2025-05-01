"""Custom rate limiter for testing."""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional, Union

from fastapi import HTTPException, Request
from fastapi_limiter.depends import RateLimiter


class TestRateLimiter(RateLimiter):
    """Custom rate limiter for testing that doesn't rely on Redis."""

    # Class-level storage for request counts
    _requests: Dict[str, Dict[datetime, int]] = defaultdict(lambda: defaultdict(int))

    def __init__(self, times: int = 1, minutes: int = 1):
        """Initialize the test rate limiter.

        Args:
            times (int, optional): Number of requests allowed. Defaults to 1.
            minutes (int, optional): Time window in minutes. Defaults to 1.
        """
        self.times = times
        self.minutes = minutes

    async def __call__(self, request: Optional[Union[Request, str]] = None) -> bool:
        """Check if the request should be rate limited.

        Args:
            request (Optional[Union[Request, str]], optional): FastAPI request object or identifier. Defaults to None.

        Returns:
            bool: True if request is allowed, False otherwise

        Raises:
            HTTPException: If rate limit is exceeded
        """
        # Generate a key for the request
        if isinstance(request, Request):
            key = f"{request.client.host}:{request.url.path}"
        elif isinstance(request, str):
            key = request
        else:
            key = "default"

        now = datetime.now().replace(second=0, microsecond=0)
        window_start = now - timedelta(minutes=self.minutes)

        # Clean up old entries
        self._cleanup_old_requests(key, window_start)

        # Count requests in current window
        current_count = sum(
            count
            for timestamp, count in TestRateLimiter._requests[key].items()
            if timestamp >= window_start
        )

        if current_count >= self.times:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
            )

        # Record this request
        TestRateLimiter._requests[key][now] = TestRateLimiter._requests[key].get(now, 0) + 1
        return True

    def _cleanup_old_requests(self, key: str, window_start: datetime) -> None:
        """Remove request counts older than the current window.

        Args:
            key (str): Request key
            window_start (datetime): Start of current window
        """
        TestRateLimiter._requests[key] = {
            timestamp: count
            for timestamp, count in TestRateLimiter._requests[key].items()
            if timestamp >= window_start
        }

    @classmethod
    def reset(cls) -> None:
        """Reset all request counters. Useful between tests."""
        cls._requests.clear() 