"""Test configuration and fixtures."""
import pytest
import fakeredis

from app.config import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Get test settings.

    Returns:
        Settings: Test settings instance
    """
    return Settings(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        redis_password=None,
        environment="test",
    )


@pytest.fixture
def redis_mock() -> fakeredis.FakeRedis:
    """Get a fake Redis client for testing.

    Returns:
        fakeredis.FakeRedis: Fake Redis client
    """
    return fakeredis.FakeRedis(decode_responses=True) 