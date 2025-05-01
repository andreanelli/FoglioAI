"""Tests for content extractor module."""
from datetime import datetime, timezone
from typing import Dict

import pytest
from bs4 import BeautifulSoup

from app.web.extractor import ContentExtractor, ExtractionError


@pytest.fixture
def extractor() -> ContentExtractor:
    """Create a content extractor instance.

    Returns:
        ContentExtractor: Content extractor instance
    """
    return ContentExtractor()


@pytest.fixture
def sample_html() -> str:
    """Create sample HTML content.

    Returns:
        str: Sample HTML content
    """
    return """
    <html>
        <head>
            <title>Test Article</title>
            <meta property="og:title" content="OpenGraph Title">
            <meta property="og:author" content="John Doe">
            <meta property="article:published_time" content="2024-03-01T12:00:00Z">
        </head>
        <body>
            <h1>Article Heading</h1>
            <div class="content">
                <p>This is a test article with some content that needs to be long enough to pass validation.
                   The content should be meaningful and provide enough context for the article extraction
                   to work properly. We need to ensure that the content meets the minimum length requirements
                   set in the ContentExtractor class.</p>
                <p>It has multiple paragraphs and <a href="/relative">relative links</a> to demonstrate
                   the link rewriting functionality. We also want to test how the extractor handles
                   different HTML elements and ensures proper content cleaning.</p>
                <p>This paragraph contains an <img src="/test.jpg" alt="Test Image"> image with a relative
                   path that should be rewritten to an absolute URL. The image should be preserved in
                   the extracted content while maintaining its context.</p>
                <script>alert('test');</script>
                <iframe src="test.html"></iframe>
            </div>
        </body>
    </html>
    """


def test_extract_article_success(extractor: ContentExtractor, sample_html: str) -> None:
    """Test successful article extraction.

    Args:
        extractor (ContentExtractor): Content extractor instance
        sample_html (str): Sample HTML content
    """
    url = "https://example.com/article"
    result = extractor.extract_article(sample_html, url)

    assert result["title"] == "OpenGraph Title"
    assert result["author"] == "John Doe"
    assert isinstance(result["publication_date"], datetime)
    assert result["url"] == url
    assert "content" in result
    assert "test article" in result["content"].lower()
    assert "script" not in result["content"].lower()
    assert "iframe" not in result["content"].lower()


def test_extract_article_invalid_content(extractor: ContentExtractor) -> None:
    """Test article extraction with invalid content.

    Args:
        extractor (ContentExtractor): Content extractor instance
    """
    with pytest.raises(ExtractionError):
        extractor.extract_article("<html></html>", "https://example.com")


def test_extract_metadata(extractor: ContentExtractor, sample_html: str) -> None:
    """Test metadata extraction.

    Args:
        extractor (ContentExtractor): Content extractor instance
        sample_html (str): Sample HTML content
    """
    url = "https://example.com/article"
    soup = BeautifulSoup(sample_html, "html.parser")
    metadata = extractor.extract_metadata(soup, url)

    assert metadata["title"] == "OpenGraph Title"
    assert metadata["author"] == "John Doe"
    assert metadata["url"] == url
    assert isinstance(metadata["publication_date"], datetime)
    assert metadata["publication_date"].replace(tzinfo=timezone.utc).isoformat() == "2024-03-01T12:00:00+00:00"


def test_clean_content(extractor: ContentExtractor) -> None:
    """Test content cleaning.

    Args:
        extractor (ContentExtractor): Content extractor instance
    """
    base_url = "https://example.com"
    html = """
    <div>
        <p>Test content</p>
        <script>alert('test');</script>
        <img src="/image.jpg">
        <a href="/link">Link</a>
        <iframe src="test.html"></iframe>
        <form>
            <input type="text">
        </form>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    content = extractor.clean_content(soup, base_url)

    assert "Test content" in content
    assert "script" not in content.lower()
    assert "iframe" not in content.lower()
    assert "form" not in content.lower()


def test_validate_content(extractor: ContentExtractor) -> None:
    """Test content validation.

    Args:
        extractor (ContentExtractor): Content extractor instance
    """
    assert extractor._validate_content("A" * extractor.MIN_CONTENT_LENGTH)
    assert not extractor._validate_content("Too short")
    assert not extractor._validate_content("")


def test_extract_title_fallbacks(extractor: ContentExtractor) -> None:
    """Test title extraction fallbacks.

    Args:
        extractor (ContentExtractor): Content extractor instance
    """
    # Test OpenGraph title
    html = '<meta property="og:title" content="OG Title">'
    soup = BeautifulSoup(html, "html.parser")
    assert extractor._extract_title(soup) == "OG Title"

    # Test title tag
    html = "<title>Page Title</title>"
    soup = BeautifulSoup(html, "html.parser")
    assert extractor._extract_title(soup) == "Page Title"

    # Test h1 tag
    html = "<h1>Heading Title</h1>"
    soup = BeautifulSoup(html, "html.parser")
    assert extractor._extract_title(soup) == "Heading Title"

    # Test no title
    html = "<div>No title here</div>"
    soup = BeautifulSoup(html, "html.parser")
    assert extractor._extract_title(soup) is None


def test_extract_author_fallbacks(extractor: ContentExtractor) -> None:
    """Test author extraction fallbacks.

    Args:
        extractor (ContentExtractor): Content extractor instance
    """
    # Test meta tag
    html = '<meta property="author" content="Meta Author">'
    soup = BeautifulSoup(html, "html.parser")
    assert extractor._extract_author(soup) == "Meta Author"

    # Test schema.org
    html = '<span itemprop="author">Schema Author</span>'
    soup = BeautifulSoup(html, "html.parser")
    assert extractor._extract_author(soup) == "Schema Author"

    # Test class
    html = '<div class="author">Class Author</div>'
    soup = BeautifulSoup(html, "html.parser")
    assert extractor._extract_author(soup) == "Class Author"

    # Test no author
    html = "<div>No author here</div>"
    soup = BeautifulSoup(html, "html.parser")
    assert extractor._extract_author(soup) is None


def test_extract_date_fallbacks(extractor: ContentExtractor) -> None:
    """Test date extraction fallbacks.

    Args:
        extractor (ContentExtractor): Content extractor instance
    """
    # Test meta tag
    html = '<meta property="article:published_time" content="2024-03-01T12:00:00Z">'
    soup = BeautifulSoup(html, "html.parser")
    date = extractor._extract_date(soup)
    assert date is not None
    assert date.replace(tzinfo=timezone.utc).isoformat() == "2024-03-01T12:00:00+00:00"

    # Test time tag
    html = '<time datetime="2024-03-01T12:00:00Z">March 1, 2024</time>'
    soup = BeautifulSoup(html, "html.parser")
    date = extractor._extract_date(soup)
    assert date is not None
    assert date.replace(tzinfo=timezone.utc).isoformat() == "2024-03-01T12:00:00+00:00"

    # Test invalid date
    html = '<meta property="article:published_time" content="invalid">'
    soup = BeautifulSoup(html, "html.parser")
    assert extractor._extract_date(soup) is None

    # Test no date
    html = "<div>No date here</div>"
    soup = BeautifulSoup(html, "html.parser")
    assert extractor._extract_date(soup) is None 