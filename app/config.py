"""Application configuration module."""
from functools import lru_cache
from typing import Optional

import redis
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Redis settings
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # API settings
    log_level: str = "info"
    environment: str = "development"

    # Model settings
    mistral_api_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # Allow extra fields
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Settings: Application settings instance
    """
    return Settings()


def get_redis_client() -> redis.Redis:
    """Get Redis client instance.

    Returns:
        redis.Redis: Redis client instance
    """
    settings = get_settings()
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password,
        decode_responses=True,
    )


# Export settings instance
settings = get_settings() 