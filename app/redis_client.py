"""Redis client module."""
import redis

from app.config import get_settings


class RedisClient:
    """Redis client wrapper."""

    def __init__(self) -> None:
        """Initialize Redis client."""
        settings = get_settings()
        self._client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True,
        )

    def check_connection(self) -> bool:
        """Check Redis connection.

        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            return self._client.ping()
        except redis.ConnectionError:
            return False

    def close(self) -> None:
        """Close Redis connection."""
        self._client.close()

    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance.

        Returns:
            redis.Redis: Redis client instance
        """
        return self._client


# Create global Redis client instance
redis_client = RedisClient() 