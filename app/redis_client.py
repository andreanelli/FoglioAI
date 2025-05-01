"""Redis client module."""
from typing import Optional

import redis
from redis.exceptions import RedisError

from app.config import Settings, get_settings


class RedisClient:
    """Redis client wrapper with connection management."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Initialize Redis client with settings.

        Args:
            settings (Optional[Settings], optional): Application settings. Defaults to None.
        """
        self.settings = settings or get_settings()
        self.client = redis.Redis(
            host=self.settings.redis_host,
            port=self.settings.redis_port,
            db=self.settings.redis_db,
            password=self.settings.redis_password,
            decode_responses=True,
        )

    def check_connection(self) -> bool:
        """Check if Redis connection is healthy.

        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            return self.client.ping()
        except RedisError:
            return False

    def close(self) -> None:
        """Close Redis connection."""
        try:
            self.client.close()
        except RedisError:
            pass


# Global Redis client instance
redis_client = RedisClient() 