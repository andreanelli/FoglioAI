"""Tests for error handling utilities."""
import time
from unittest.mock import MagicMock, patch

import pytest
import redis

from app.utils.errors import RetryError, ValidationError, retry


def test_retry_success() -> None:
    """Test successful retry."""
    mock_func = MagicMock()
    mock_func.return_value = "success"

    decorated = retry()(mock_func)
    result = decorated()

    assert result == "success"
    mock_func.assert_called_once()


def test_retry_eventual_success() -> None:
    """Test eventual success after retries."""
    mock_func = MagicMock()
    mock_func.side_effect = [redis.RedisError("fail"), redis.RedisError("fail"), "success"]

    decorated = retry(retries=3, delay=0.1)(mock_func)
    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 3


def test_retry_failure() -> None:
    """Test failure after all retries."""
    mock_func = MagicMock()
    mock_func.side_effect = redis.RedisError("fail")

    decorated = retry(retries=2, delay=0.1)(mock_func)

    with pytest.raises(RetryError, match="Failed after 2 attempts"):
        decorated()

    assert mock_func.call_count == 2


def test_retry_custom_exceptions() -> None:
    """Test retry with custom exceptions."""
    mock_func = MagicMock()
    mock_func.side_effect = ValueError("fail")

    decorated = retry(retries=2, delay=0.1, exceptions=(ValueError,))(mock_func)

    with pytest.raises(RetryError, match="Failed after 2 attempts"):
        decorated()

    assert mock_func.call_count == 2


def test_retry_backoff() -> None:
    """Test retry backoff timing."""
    mock_func = MagicMock()
    mock_func.side_effect = [redis.RedisError("fail"), redis.RedisError("fail"), "success"]
    mock_sleep = MagicMock()

    with patch("time.sleep", mock_sleep):
        decorated = retry(retries=3, delay=1.0, backoff=2.0)(mock_func)
        result = decorated()

    assert result == "success"
    assert mock_func.call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1.0)  # First retry
    mock_sleep.assert_any_call(2.0)  # Second retry with backoff 