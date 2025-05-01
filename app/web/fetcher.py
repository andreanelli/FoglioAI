"""Web fetcher module."""
import logging
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class WebFetcherError(Exception):
    """Base exception for web fetcher errors."""

    pass


class InvalidURLError(WebFetcherError):
    """Exception raised for invalid URLs."""

    pass


class FetchError(WebFetcherError):
    """Exception raised for failed fetch attempts."""

    pass


class WebFetcher:
    """Web content fetcher with retry logic and error handling."""

    DEFAULT_HEADERS = {
        "User-Agent": "FoglioAI/1.0 (https://github.com/yourusername/FoglioAI)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(
        self,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        """Initialize the web fetcher.

        Args:
            headers (Optional[Dict[str, str]], optional): Custom headers to use for requests.
                Defaults to None.
            timeout (int, optional): Request timeout in seconds. Defaults to 10.
            max_retries (int, optional): Maximum number of retry attempts. Defaults to 3.
        """
        self.headers = headers or self.DEFAULT_HEADERS
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def is_valid_url(self, url: str) -> bool:
        """Check if a URL is valid.

        Args:
            url (str): URL to validate

        Returns:
            bool: True if URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme in ("http", "https"), result.netloc])
        except Exception as e:
            logger.debug(f"URL validation failed for {url}: {e}")
            return False

    def sanitize_url(self, url: str) -> str:
        """Sanitize and normalize a URL.

        Args:
            url (str): URL to sanitize

        Returns:
            str: Sanitized URL

        Raises:
            InvalidURLError: If URL is invalid
        """
        url = url.strip()
        if not self.is_valid_url(url):
            raise InvalidURLError(f"Invalid URL: {url}")
        return url

    def get_domain(self, url: str) -> str:
        """Extract domain from URL.

        Args:
            url (str): URL to extract domain from

        Returns:
            str: Domain name
        """
        return urlparse(url).netloc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    def fetch_url(self, url: str) -> requests.Response:
        """Fetch content from a URL with retry logic.

        Args:
            url (str): URL to fetch

        Returns:
            requests.Response: Response object

        Raises:
            FetchError: If fetch fails after retries
        """
        url = self.sanitize_url(url)
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response
        except RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise FetchError(f"Failed to fetch {url}: {e}") from e

    def validate_response(self, response: requests.Response) -> bool:
        """Validate response content.

        Args:
            response (requests.Response): Response to validate

        Returns:
            bool: True if response is valid, False otherwise
        """
        content_type = response.headers.get("content-type", "").lower()
        return "html" in content_type and len(response.content) > 0

    def get_soup(self, response: requests.Response) -> BeautifulSoup:
        """Create BeautifulSoup object from response.

        Args:
            response (requests.Response): Response to parse

        Returns:
            BeautifulSoup: Parsed HTML

        Raises:
            FetchError: If response is invalid or parsing fails
        """
        if not self.validate_response(response):
            raise FetchError("Invalid response content")

        try:
            return BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            logger.error(f"Failed to parse HTML: {e}")
            raise FetchError(f"Failed to parse HTML: {e}") from e

    def close(self) -> None:
        """Close the session."""
        self.session.close() 