"""Redis-based web content cache."""
import json
import logging
import zlib
from datetime import timedelta
from typing import Any, Dict, Optional

import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class WebCacheError(Exception):
    """Base exception for web cache errors."""

    pass


class WebCache:
    """Redis-based cache for web content with compression."""

    # Default TTL for cached content (24 hours)
    DEFAULT_TTL = timedelta(hours=24)

    # Compression threshold in bytes (10KB)
    COMPRESSION_THRESHOLD = 10 * 1024

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """Initialize the web cache.

        Args:
            redis_host (str, optional): Redis host. Defaults to "localhost".
            redis_port (int, optional): Redis port. Defaults to 6379.
            redis_db (int, optional): Redis database number. Defaults to 0.
            redis_password (Optional[str], optional): Redis password. Defaults to None.
            ttl (Optional[timedelta], optional): Default TTL for cached items.
                Defaults to None (uses DEFAULT_TTL).
        """
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=False,  # We need bytes for compression
        )
        self.ttl = ttl or self.DEFAULT_TTL

        # Test Redis connection
        try:
            self.redis.ping()
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise WebCacheError(f"Failed to connect to Redis: {e}") from e

    def generate_cache_key(self, url: str) -> str:
        """Generate a cache key for a URL.

        Args:
            url (str): URL to generate key for

        Returns:
            str: Cache key
        """
        return f"web:cache:{url}"

    def get_cached_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached content for a URL.

        Args:
            url (str): URL to get cached content for

        Returns:
            Optional[Dict[str, Any]]: Cached content or None if not found

        Raises:
            WebCacheError: If there's an error retrieving from cache
        """
        key = self.generate_cache_key(url)
        try:
            data = self.redis.get(key)
            if not data:
                return None

            # Check if data is compressed (starts with the zlib header)
            if data.startswith(b"x\x9c") or data.startswith(b"x\xda"):
                data = zlib.decompress(data)

            return json.loads(data.decode())
        except (RedisError, zlib.error, json.JSONDecodeError) as e:
            logger.error(f"Failed to get cached content for {url}: {e}")
            raise WebCacheError(f"Failed to get cached content for {url}: {e}") from e

    def cache_content(
        self, url: str, content: Dict[str, Any], ttl: Optional[timedelta] = None
    ) -> None:
        """Cache content for a URL.

        Args:
            url (str): URL to cache content for
            content (Dict[str, Any]): Content to cache
            ttl (Optional[timedelta], optional): Custom TTL for this item.
                Defaults to None (uses instance TTL).

        Raises:
            WebCacheError: If there's an error caching the content
        """
        key = self.generate_cache_key(url)
        try:
            # Convert content to JSON bytes
            data = json.dumps(content).encode()

            # Compress if data is large enough
            if len(data) > self.COMPRESSION_THRESHOLD:
                data = zlib.compress(data)

            # Cache with TTL
            self.redis.setex(
                key,
                ttl.total_seconds() if ttl else self.ttl.total_seconds(),
                data,
            )
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Failed to cache content for {url}: {e}")
            raise WebCacheError(f"Failed to cache content for {url}: {e}") from e

    def invalidate_cache(self, url: str) -> None:
        """Invalidate cached content for a URL.

        Args:
            url (str): URL to invalidate cache for

        Raises:
            WebCacheError: If there's an error invalidating the cache
        """
        key = self.generate_cache_key(url)
        try:
            self.redis.delete(key)
        except RedisError as e:
            logger.error(f"Failed to invalidate cache for {url}: {e}")
            raise WebCacheError(f"Failed to invalidate cache for {url}: {e}") from e

    def cleanup_expired_cache(self) -> None:
        """Clean up expired cache entries.

        Note: This is a no-op as Redis automatically removes expired keys.
        It's included for API completeness and potential future use.
        """
        pass  # Redis handles TTL expiration automatically

    def close(self) -> None:
        """Close the Redis connection."""
        self.redis.close() 