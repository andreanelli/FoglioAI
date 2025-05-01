"""Tests for web fetcher module."""
import pytest
import requests
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError

from app.web.fetcher import FetchError, InvalidURLError, WebFetcher


@pytest.fixture
def fetcher() -> WebFetcher:
    """Create a web fetcher instance.

    Returns:
        WebFetcher: Web fetcher instance
    """
    return WebFetcher()


def test_is_valid_url(fetcher: WebFetcher) -> None:
    """Test URL validation.

    Args:
        fetcher (WebFetcher): Web fetcher instance
    """
    assert fetcher.is_valid_url("https://example.com")
    assert fetcher.is_valid_url("http://example.com/path?query=value")
    assert not fetcher.is_valid_url("not-a-url")
    assert not fetcher.is_valid_url("ftp://example.com")
    assert not fetcher.is_valid_url("")


def test_sanitize_url(fetcher: WebFetcher) -> None:
    """Test URL sanitization.

    Args:
        fetcher (WebFetcher): Web fetcher instance
    """
    assert fetcher.sanitize_url(" https://example.com ") == "https://example.com"
    with pytest.raises(InvalidURLError):
        fetcher.sanitize_url("not-a-url")


def test_get_domain(fetcher: WebFetcher) -> None:
    """Test domain extraction.

    Args:
        fetcher (WebFetcher): Web fetcher instance
    """
    assert fetcher.get_domain("https://example.com/path") == "example.com"
    assert fetcher.get_domain("http://sub.example.com") == "sub.example.com"


def test_fetch_url_success(fetcher: WebFetcher, requests_mock) -> None:
    """Test successful URL fetch.

    Args:
        fetcher (WebFetcher): Web fetcher instance
        requests_mock: Requests mock fixture
    """
    url = "https://example.com"
    html_content = "<html><body>Test</body></html>"
    requests_mock.get(
        url,
        text=html_content,
        headers={"content-type": "text/html"},
    )

    response = fetcher.fetch_url(url)
    assert response.text == html_content
    assert response.headers["content-type"] == "text/html"


def test_fetch_url_retry(fetcher: WebFetcher, requests_mock) -> None:
    """Test URL fetch retry logic.

    Args:
        fetcher (WebFetcher): Web fetcher instance
        requests_mock: Requests mock fixture
    """
    url = "https://example.com"
    html_content = "<html><body>Test</body></html>"

    # Mock first two requests to fail, third succeeds
    requests_mock.get(
        url,
        [
            {"status_code": 500},
            {"status_code": 500},
            {
                "text": html_content,
                "headers": {"content-type": "text/html"},
            },
        ],
    )

    response = fetcher.fetch_url(url)
    assert response.text == html_content
    assert requests_mock.call_count == 3


def test_fetch_url_failure(fetcher: WebFetcher, requests_mock) -> None:
    """Test URL fetch failure.

    Args:
        fetcher (WebFetcher): Web fetcher instance
        requests_mock: Requests mock fixture
    """
    url = "https://example.com"
    requests_mock.get(url, status_code=404)

    with pytest.raises(FetchError):
        fetcher.fetch_url(url)


def test_validate_response(fetcher: WebFetcher) -> None:
    """Test response validation.

    Args:
        fetcher (WebFetcher): Web fetcher instance
    """
    valid_response = requests.Response()
    valid_response.headers["content-type"] = "text/html"
    valid_response._content = b"<html></html>"  # type: ignore
    assert fetcher.validate_response(valid_response)

    invalid_response = requests.Response()
    invalid_response.headers["content-type"] = "application/json"
    invalid_response._content = b"{}"  # type: ignore
    assert not fetcher.validate_response(invalid_response)

    empty_response = requests.Response()
    empty_response.headers["content-type"] = "text/html"
    empty_response._content = b""  # type: ignore
    assert not fetcher.validate_response(empty_response)


def test_get_soup_success(fetcher: WebFetcher) -> None:
    """Test successful HTML parsing.

    Args:
        fetcher (WebFetcher): Web fetcher instance
    """
    response = requests.Response()
    response.headers["content-type"] = "text/html"
    response._content = b"<html><body>Test</body></html>"  # type: ignore

    soup = fetcher.get_soup(response)
    assert isinstance(soup, BeautifulSoup)
    assert soup.body.text == "Test"


def test_get_soup_invalid_content(fetcher: WebFetcher) -> None:
    """Test HTML parsing with invalid content.

    Args:
        fetcher (WebFetcher): Web fetcher instance
    """
    response = requests.Response()
    response.headers["content-type"] = "application/json"
    response._content = b"{}"  # type: ignore

    with pytest.raises(FetchError, match="Invalid response content"):
        fetcher.get_soup(response)


def test_get_soup_parse_error(fetcher: WebFetcher) -> None:
    """Test HTML parsing error.

    Args:
        fetcher (WebFetcher): Web fetcher instance
    """
    response = requests.Response()
    response.headers["content-type"] = "text/html"
    response._content = b"Invalid HTML"  # type: ignore

    # This should not raise an error as BeautifulSoup is quite forgiving
    soup = fetcher.get_soup(response)
    assert isinstance(soup, BeautifulSoup)
    assert soup.text == "Invalid HTML" 