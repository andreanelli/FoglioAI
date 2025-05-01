"""Time handling utilities."""
from datetime import datetime, timedelta
from typing import Optional

import pytz


def format_timestamp(dt: datetime, timezone: str = "UTC") -> str:
    """Format a datetime object as an ISO 8601 string.

    Args:
        dt (datetime): Datetime to format
        timezone (str, optional): Timezone name. Defaults to "UTC".

    Returns:
        str: Formatted timestamp
    """
    tz = pytz.timezone(timezone)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    return dt.astimezone(tz).isoformat()


def parse_timestamp(timestamp: str, timezone: str = "UTC") -> datetime:
    """Parse an ISO 8601 timestamp string.

    Args:
        timestamp (str): Timestamp string to parse
        timezone (str, optional): Timezone name. Defaults to "UTC".

    Returns:
        datetime: Parsed datetime object
    """
    tz = pytz.timezone(timezone)
    dt = datetime.fromisoformat(timestamp)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    return dt.astimezone(tz)


def calculate_ttl(
    base_ttl: timedelta = timedelta(days=7),
    min_ttl: Optional[timedelta] = None,
    max_ttl: Optional[timedelta] = None,
) -> timedelta:
    """Calculate TTL with optional bounds.

    Args:
        base_ttl (timedelta, optional): Base TTL. Defaults to 7 days.
        min_ttl (Optional[timedelta], optional): Minimum TTL. Defaults to None.
        max_ttl (Optional[timedelta], optional): Maximum TTL. Defaults to None.

    Returns:
        timedelta: Calculated TTL
    """
    ttl = base_ttl

    if min_ttl is not None:
        ttl = max(ttl, min_ttl)

    if max_ttl is not None:
        ttl = min(ttl, max_ttl)

    return ttl 