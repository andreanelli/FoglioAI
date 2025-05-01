"""Content extractor module."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from readability import Document

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Exception raised for content extraction errors."""

    pass


class ContentExtractor:
    """Content extractor using readability-lxml."""

    MIN_CONTENT_LENGTH = 100  # Minimum content length in characters
    DATE_META_TAGS = [
        "article:published_time",
        "article:modified_time",
        "og:published_time",
        "og:modified_time",
        "datePublished",
        "dateModified",
        "date",
    ]

    def extract_article(self, html: str, url: str) -> Dict[str, Any]:
        """Extract article content and metadata from HTML.

        Args:
            html (str): HTML content to extract from
            url (str): URL of the article for resolving relative links

        Returns:
            Dict[str, Any]: Extracted article data

        Raises:
            ExtractionError: If extraction fails or content is invalid
        """
        try:
            doc = Document(html)
            soup = BeautifulSoup(doc.summary(), "html.parser")
            content = self.clean_content(soup, url)

            if not self._validate_content(content):
                raise ExtractionError("Extracted content is too short or invalid")

            metadata = self.extract_metadata(BeautifulSoup(html, "html.parser"), url)
            metadata["content"] = content

            return metadata
        except Exception as e:
            logger.error(f"Failed to extract article content: {e}")
            raise ExtractionError(f"Failed to extract article content: {e}") from e

    def extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract metadata from HTML.

        Args:
            soup (BeautifulSoup): BeautifulSoup object of the full HTML
            url (str): URL of the article

        Returns:
            Dict[str, Any]: Extracted metadata
        """
        metadata = {
            "title": self._extract_title(soup),
            "author": self._extract_author(soup),
            "publication_date": self._extract_date(soup),
            "url": url,
        }

        return {k: v for k, v in metadata.items() if v is not None}

    def clean_content(self, soup: BeautifulSoup, base_url: str) -> str:
        """Clean and normalize extracted content.

        Args:
            soup (BeautifulSoup): BeautifulSoup object of the extracted content
            base_url (str): Base URL for resolving relative links

        Returns:
            str: Cleaned content
        """
        # Remove unwanted tags
        for tag in soup.find_all(["script", "style", "iframe", "form"]):
            tag.decompose()

        # Fix relative URLs in images and links
        for img in soup.find_all("img", src=True):
            if not img["src"].startswith(("http://", "https://")):
                img["src"] = urljoin(base_url, img["src"])

        for a in soup.find_all("a", href=True):
            if not a["href"].startswith(("http://", "https://")):
                a["href"] = urljoin(base_url, a["href"])

        # Normalize whitespace
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())

    def _validate_content(self, content: str) -> bool:
        """Validate extracted content.

        Args:
            content (str): Content to validate

        Returns:
            bool: True if content is valid, False otherwise
        """
        if not content or len(content) < self.MIN_CONTENT_LENGTH:
            return False

        # Add more validation as needed (e.g., content quality heuristics)
        return True

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article title.

        Args:
            soup (BeautifulSoup): BeautifulSoup object

        Returns:
            Optional[str]: Article title or None if not found
        """
        # Try meta tags first
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        # Try main title tag
        title = soup.find("title")
        if title and title.string:
            return title.string.strip()

        # Try h1
        h1 = soup.find("h1")
        if h1 and h1.string:
            return h1.string.strip()

        return None

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article author.

        Args:
            soup (BeautifulSoup): BeautifulSoup object

        Returns:
            Optional[str]: Article author or None if not found
        """
        # Try meta tags
        for tag in ["author", "article:author", "og:author"]:
            meta = soup.find("meta", property=tag) or soup.find("meta", attrs={"name": tag})
            if meta and meta.get("content"):
                return meta["content"].strip()

        # Try schema.org markup
        author = soup.find("span", itemprop="author")
        if author:
            return author.get_text(strip=True)

        # Try common author class names
        for class_name in ["author", "byline"]:
            author = soup.find(class_=class_name)
            if author:
                return author.get_text(strip=True)

        return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract article publication date.

        Args:
            soup (BeautifulSoup): BeautifulSoup object

        Returns:
            Optional[datetime]: Article publication date or None if not found
        """
        # Try meta tags
        for tag in self.DATE_META_TAGS:
            meta = soup.find("meta", property=tag) or soup.find("meta", attrs={"name": tag})
            if meta and meta.get("content"):
                try:
                    return datetime.fromisoformat(meta["content"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    continue

        # Try time tag
        time = soup.find("time")
        if time and time.get("datetime"):
            try:
                return datetime.fromisoformat(time["datetime"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        return None 