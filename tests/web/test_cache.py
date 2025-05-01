"""Tests for web cache module."""
import json
import zlib
from datetime import timedelta
from typing import Any, Dict

import pytest
import redis
from redis.exceptions import RedisError

from app.web.cache import WebCache, WebCacheError


@pytest.fixture
def redis_mock(mocker):
    """Mock Redis client.

    Args:
        mocker: Pytest mocker fixture

    Returns:
        MagicMock: Mocked Redis client
    """
    mock = mocker.MagicMock(spec=redis.Redis)
    mock.ping.return_value = True
    return mock


@pytest.fixture
def cache(mocker, redis_mock) -> WebCache:
    """Create a web cache instance with mocked Redis.

    Args:
        mocker: Pytest mocker fixture
        redis_mock: Mocked Redis client

    Returns:
        WebCache: Web cache instance
    """
    mocker.patch("redis.Redis", return_value=redis_mock)
    return WebCache()


def test_init_success(cache: WebCache) -> None:
    """Test successful cache initialization.

    Args:
        cache (WebCache): Web cache instance
    """
    assert cache.ttl == WebCache.DEFAULT_TTL
    assert cache.redis is not None


def test_init_custom_ttl() -> None:
    """Test cache initialization with custom TTL."""
    ttl = timedelta(hours=1)
    cache = WebCache(ttl=ttl)
    assert cache.ttl == ttl


def test_init_redis_error(mocker) -> None:
    """Test cache initialization with Redis error.

    Args:
        mocker: Pytest mocker fixture
    """
    mock_redis = mocker.MagicMock(spec=redis.Redis)
    mock_redis.ping.side_effect = RedisError("Connection failed")
    mocker.patch("redis.Redis", return_value=mock_redis)

    with pytest.raises(WebCacheError, match="Failed to connect to Redis"):
        WebCache()


def test_generate_cache_key(cache: WebCache) -> None:
    """Test cache key generation.

    Args:
        cache (WebCache): Web cache instance
    """
    url = "https://example.com"
    key = cache.generate_cache_key(url)
    assert key == f"web:cache:{url}"


def test_get_cached_content_hit(cache: WebCache, redis_mock) -> None:
    """Test successful cache hit.

    Args:
        cache (WebCache): Web cache instance
        redis_mock: Mocked Redis client
    """
    url = "https://example.com"
    content = {"title": "Test", "content": "Content"}
    redis_mock.get.return_value = json.dumps(content).encode()

    result = cache.get_cached_content(url)
    assert result == content
    redis_mock.get.assert_called_once_with(cache.generate_cache_key(url))


def test_get_cached_content_miss(cache: WebCache, redis_mock) -> None:
    """Test cache miss.

    Args:
        cache (WebCache): Web cache instance
        redis_mock: Mocked Redis client
    """
    url = "https://example.com"
    redis_mock.get.return_value = None

    result = cache.get_cached_content(url)
    assert result is None
    redis_mock.get.assert_called_once_with(cache.generate_cache_key(url))


def test_get_cached_content_compressed(cache: WebCache, redis_mock) -> None:
    """Test retrieving compressed cached content.

    Args:
        cache (WebCache): Web cache instance
        redis_mock: Mocked Redis client
    """
    url = "https://example.com"
    content = {"title": "Test", "content": "Content"}
    compressed_data = zlib.compress(json.dumps(content).encode())
    redis_mock.get.return_value = compressed_data

    result = cache.get_cached_content(url)
    assert result == content


def test_get_cached_content_error(cache: WebCache, redis_mock) -> None:
    """Test cache retrieval error.

    Args:
        cache (WebCache): Web cache instance
        redis_mock: Mocked Redis client
    """
    url = "https://example.com"
    redis_mock.get.side_effect = RedisError("Connection failed")

    with pytest.raises(WebCacheError, match="Failed to get cached content"):
        cache.get_cached_content(url)


def test_cache_content_success(cache: WebCache, redis_mock) -> None:
    """Test successful content caching.

    Args:
        cache (WebCache): Web cache instance
        redis_mock: Mocked Redis client
    """
    url = "https://example.com"
    content = {"title": "Test", "content": "Content"}
    ttl = timedelta(hours=1)

    cache.cache_content(url, content, ttl)
    redis_mock.setex.assert_called_once()
    assert redis_mock.setex.call_args[0][0] == cache.generate_cache_key(url)
    assert redis_mock.setex.call_args[0][1] == ttl.total_seconds()


def test_cache_content_compression(cache: WebCache, redis_mock) -> None:
    """Test content compression for large data.

    Args:
        cache (WebCache): Web cache instance
        redis_mock: Mocked Redis client
    """
    url = "https://example.com"
    # Create content larger than compression threshold
    content = {
        "title": "Test",
        "content": "x" * (WebCache.COMPRESSION_THRESHOLD + 1),
    }

    cache.cache_content(url, content)
    redis_mock.setex.assert_called_once()
    # Verify the data was compressed (starts with zlib header)
    assert redis_mock.setex.call_args[0][2].startswith(b"x\x9c")


def test_cache_content_error(cache: WebCache, redis_mock) -> None:
    """Test caching error.

    Args:
        cache (WebCache): Web cache instance
        redis_mock: Mocked Redis client
    """
    url = "https://example.com"
    content: Dict[str, Any] = {"title": "Test"}
    redis_mock.setex.side_effect = RedisError("Connection failed")

    with pytest.raises(WebCacheError, match="Failed to cache content"):
        cache.cache_content(url, content)


def test_invalidate_cache_success(cache: WebCache, redis_mock) -> None:
    """Test successful cache invalidation.

    Args:
        cache (WebCache): Web cache instance
        redis_mock: Mocked Redis client
    """
    url = "https://example.com"
    cache.invalidate_cache(url)
    redis_mock.delete.assert_called_once_with(cache.generate_cache_key(url))


def test_invalidate_cache_error(cache: WebCache, redis_mock) -> None:
    """Test cache invalidation error.

    Args:
        cache (WebCache): Web cache instance
        redis_mock: Mocked Redis client
    """
    url = "https://example.com"
    redis_mock.delete.side_effect = RedisError("Connection failed")

    with pytest.raises(WebCacheError, match="Failed to invalidate cache"):
        cache.invalidate_cache(url)


def test_cleanup_expired_cache(cache: WebCache, redis_mock) -> None:
    """Test cleanup of expired cache entries.

    Args:
        cache (WebCache): Web cache instance
        redis_mock: Mocked Redis client
    """
    # This is a no-op as Redis handles TTL automatically
    cache.cleanup_expired_cache()
    redis_mock.delete.assert_not_called()


def test_close(cache: WebCache, redis_mock) -> None:
    """Test Redis connection closure.

    Args:
        cache (WebCache): Web cache instance
        redis_mock: Mocked Redis client
    """
    cache.close()
    redis_mock.close.assert_called_once() 