"""Validation utilities."""
import base64
import re
from typing import Optional
from urllib.parse import urlparse

from app.models.article_run import ArticleRunStatus
from app.utils.errors import ValidationError


def validate_url(url: str) -> bool:
    """Validate a URL.

    Args:
        url (str): URL to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def validate_article_status(status: str) -> bool:
    """Validate an article status.

    Args:
        status (str): Status to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        ArticleRunStatus(status)
        return True
    except ValueError:
        return False


def validate_image_data(
    data: str,
    max_size: Optional[int] = None,
    allowed_mime_types: Optional[list[str]] = None,
) -> bool:
    """Validate base64-encoded image data.

    Args:
        data (str): Base64-encoded image data
        max_size (Optional[int], optional): Maximum size in bytes. Defaults to None.
        allowed_mime_types (Optional[list[str]], optional): Allowed MIME types.
            Defaults to None.

    Returns:
        bool: True if valid, False otherwise

    Raises:
        ValidationError: If validation fails
    """
    # Check if it's a valid data URL
    if not data.startswith("data:"):
        raise ValidationError("Invalid data URL format")

    # Split header and data
    try:
        header, encoded = data.split(",", 1)
    except ValueError:
        raise ValidationError("Invalid data URL format")

    # Validate MIME type
    mime_match = re.match(r"data:([^;]+);base64", header)
    if not mime_match:
        raise ValidationError("Invalid MIME type format")

    mime_type = mime_match.group(1)
    if allowed_mime_types and mime_type not in allowed_mime_types:
        raise ValidationError(f"MIME type {mime_type} not allowed")

    # Validate base64 data
    try:
        decoded = base64.b64decode(encoded)
    except Exception as e:
        raise ValidationError(f"Invalid base64 data: {str(e)}")

    # Check size
    if max_size and len(decoded) > max_size:
        raise ValidationError(
            f"Image size {len(decoded)} bytes exceeds maximum {max_size} bytes"
        )

    return True 