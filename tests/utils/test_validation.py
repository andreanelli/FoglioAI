"""Tests for validation utilities."""
import base64

import pytest

from app.utils.errors import ValidationError
from app.utils.validation import validate_article_status, validate_image_data, validate_url


def test_validate_url_valid() -> None:
    """Test URL validation with valid URLs."""
    assert validate_url("https://example.com")
    assert validate_url("http://example.com/path")
    assert validate_url("https://sub.example.com/path?query=value")


def test_validate_url_invalid() -> None:
    """Test URL validation with invalid URLs."""
    assert not validate_url("not-a-url")
    assert not validate_url("ftp://example.com")
    assert not validate_url("//example.com")
    assert not validate_url("https://")


def test_validate_article_status_valid() -> None:
    """Test article status validation with valid statuses."""
    assert validate_article_status("pending")
    assert validate_article_status("in_progress")
    assert validate_article_status("completed")
    assert validate_article_status("failed")


def test_validate_article_status_invalid() -> None:
    """Test article status validation with invalid statuses."""
    assert not validate_article_status("invalid")
    assert not validate_article_status("")
    assert not validate_article_status("PENDING")


def test_validate_image_data_valid() -> None:
    """Test image data validation with valid data."""
    # Create a small valid PNG
    png_data = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    assert validate_image_data(png_data)


def test_validate_image_data_invalid_format() -> None:
    """Test image data validation with invalid format."""
    with pytest.raises(ValidationError, match="Invalid data URL format"):
        validate_image_data("not-a-data-url")


def test_validate_image_data_invalid_base64() -> None:
    """Test image data validation with invalid base64."""
    with pytest.raises(ValidationError, match="Invalid base64 data"):
        validate_image_data("data:image/png;base64,not-base64")


def test_validate_image_data_size_limit() -> None:
    """Test image data validation with size limit."""
    # Create data that exceeds size limit
    large_data = "data:image/png;base64," + base64.b64encode(b"x" * 1000).decode()

    with pytest.raises(ValidationError, match="exceeds maximum"):
        validate_image_data(large_data, max_size=100)


def test_validate_image_data_mime_type() -> None:
    """Test image data validation with MIME type restriction."""
    png_data = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )

    # Should pass with correct MIME type
    assert validate_image_data(png_data, allowed_mime_types=["image/png"])

    # Should fail with incorrect MIME type
    with pytest.raises(ValidationError, match="MIME type image/png not allowed"):
        validate_image_data(png_data, allowed_mime_types=["image/jpeg"]) 