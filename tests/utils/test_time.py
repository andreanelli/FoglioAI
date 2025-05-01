"""Tests for time handling utilities."""
from datetime import datetime, timedelta

import pytest
import pytz

from app.utils.time import calculate_ttl, format_timestamp, parse_timestamp


def test_format_timestamp() -> None:
    """Test timestamp formatting."""
    dt = datetime(2024, 3, 15, 12, 30, 45, tzinfo=pytz.UTC)
    formatted = format_timestamp(dt)
    assert formatted == "2024-03-15T12:30:45+00:00"


def test_format_timestamp_with_timezone() -> None:
    """Test timestamp formatting with timezone."""
    dt = datetime(2024, 3, 15, 12, 30, 45, tzinfo=pytz.UTC)
    formatted = format_timestamp(dt, timezone="America/New_York")
    assert formatted.startswith("2024-03-15T")
    assert "-04:00" in formatted or "-05:00" in formatted  # Depending on DST


def test_format_timestamp_naive() -> None:
    """Test timestamp formatting with naive datetime."""
    dt = datetime(2024, 3, 15, 12, 30, 45)
    formatted = format_timestamp(dt)
    assert formatted == "2024-03-15T12:30:45+00:00"


def test_parse_timestamp() -> None:
    """Test timestamp parsing."""
    timestamp = "2024-03-15T12:30:45+00:00"
    dt = parse_timestamp(timestamp)
    assert dt.year == 2024
    assert dt.month == 3
    assert dt.day == 15
    assert dt.hour == 12
    assert dt.minute == 30
    assert dt.second == 45
    assert dt.tzinfo is not None


def test_parse_timestamp_with_timezone() -> None:
    """Test timestamp parsing with timezone."""
    timestamp = "2024-03-15T12:30:45+00:00"
    dt = parse_timestamp(timestamp, timezone="America/New_York")
    assert dt.tzinfo is not None
    assert dt.tzinfo.zone == "America/New_York"


def test_parse_timestamp_invalid() -> None:
    """Test parsing invalid timestamp."""
    with pytest.raises(ValueError):
        parse_timestamp("invalid")


def test_calculate_ttl() -> None:
    """Test TTL calculation."""
    ttl = calculate_ttl()
    assert ttl == timedelta(days=7)


def test_calculate_ttl_with_min() -> None:
    """Test TTL calculation with minimum."""
    base_ttl = timedelta(days=1)
    min_ttl = timedelta(days=3)
    ttl = calculate_ttl(base_ttl=base_ttl, min_ttl=min_ttl)
    assert ttl == timedelta(days=3)


def test_calculate_ttl_with_max() -> None:
    """Test TTL calculation with maximum."""
    base_ttl = timedelta(days=10)
    max_ttl = timedelta(days=7)
    ttl = calculate_ttl(base_ttl=base_ttl, max_ttl=max_ttl)
    assert ttl == timedelta(days=7)


def test_calculate_ttl_with_min_max() -> None:
    """Test TTL calculation with minimum and maximum."""
    base_ttl = timedelta(days=5)
    min_ttl = timedelta(days=3)
    max_ttl = timedelta(days=7)
    ttl = calculate_ttl(base_ttl=base_ttl, min_ttl=min_ttl, max_ttl=max_ttl)
    assert ttl == timedelta(days=5) 