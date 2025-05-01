"""Tests for web retrieval API endpoints."""
import json
import uuid
from datetime import datetime
from typing import Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import AnyHttpUrl
from redis import Redis

from app.api.web import (
    CitationManager,
    ContentExtractor,
    WebCache,
    WebFetcher,
    get_citation_manager,
    get_content_extractor,
    get_web_cache,
    get_web_fetcher,
)
from app.main import app
from app.models.citation import Citation
from app.web import CitationNotFoundError, ExtractionError, FetchError


@pytest.fixture
def test_client() -> TestClient:
    """Create a test client.

    Returns:
        TestClient: FastAPI test client
    """
    return TestClient(app)


@pytest.fixture
def mock_web_fetcher() -> MagicMock:
    """Create a mock WebFetcher.

    Returns:
        MagicMock: Mock WebFetcher
    """
    return MagicMock(spec=WebFetcher)


@pytest.fixture
def mock_content_extractor() -> MagicMock:
    """Create a mock ContentExtractor.

    Returns:
        MagicMock: Mock ContentExtractor
    """
    return MagicMock(spec=ContentExtractor)


@pytest.fixture
def mock_web_cache() -> MagicMock:
    """Create a mock WebCache.

    Returns:
        MagicMock: Mock WebCache
    """
    return MagicMock(spec=WebCache)


@pytest.fixture
def mock_citation_manager() -> MagicMock:
    """Create a mock CitationManager.

    Returns:
        MagicMock: Mock CitationManager
    """
    return MagicMock(spec=CitationManager)


@pytest.fixture
def sample_url() -> str:
    """Create a sample URL.

    Returns:
        str: Sample URL
    """
    return "https://example.com/article"


@pytest.fixture
def sample_html() -> str:
    """Create sample HTML content.

    Returns:
        str: Sample HTML
    """
    return "<html><body><h1>Test Article</h1><p>Test content</p></body></html>"


@pytest.fixture
def sample_extracted_content(sample_url: str) -> Dict:
    """Create sample extracted content.

    Args:
        sample_url (str): Sample URL

    Returns:
        Dict: Sample content
    """
    return {
        "url": sample_url,
        "title": "Test Article",
        "author": "John Doe",
        "content": "Test content",
        "publication_date": datetime.utcnow(),
    }


@pytest.fixture
def sample_citation(sample_url: str) -> Citation:
    """Create a sample citation.

    Args:
        sample_url (str): Sample URL

    Returns:
        Citation: Sample citation
    """
    return Citation(
        url=AnyHttpUrl(sample_url),
        title="Test Article",
        author="John Doe",
        publication_date=datetime.utcnow(),
        excerpt="Test content",
    )


def test_get_web_fetcher() -> None:
    """Test get_web_fetcher dependency."""
    redis_mock = MagicMock(spec=Redis)
    fetcher = get_web_fetcher(redis_mock)
    assert isinstance(fetcher, WebFetcher)


def test_get_content_extractor() -> None:
    """Test get_content_extractor dependency."""
    extractor = get_content_extractor()
    assert isinstance(extractor, ContentExtractor)


def test_get_web_cache() -> None:
    """Test get_web_cache dependency."""
    redis_mock = MagicMock(spec=Redis)
    cache = get_web_cache(redis_mock)
    assert isinstance(cache, WebCache)


def test_get_citation_manager() -> None:
    """Test get_citation_manager dependency."""
    redis_mock = MagicMock(spec=Redis)
    manager = get_citation_manager(redis_mock)
    assert isinstance(manager, CitationManager)


@pytest.mark.asyncio
async def test_fetch_web_content_cached(
    test_client: TestClient,
    mock_web_cache: MagicMock,
    sample_url: str,
    sample_extracted_content: Dict,
    sample_citation: Citation,
) -> None:
    """Test fetching cached web content.

    Args:
        test_client (TestClient): FastAPI test client
        mock_web_cache (MagicMock): Mock WebCache
        sample_url (str): Sample URL
        sample_extracted_content (Dict): Sample content
        sample_citation (Citation): Sample citation
    """
    cached_data = {
        "url": sample_url,
        "title": sample_extracted_content["title"],
        "author": sample_extracted_content["author"],
        "content": sample_extracted_content["content"],
        "citation": sample_citation,
    }
    mock_web_cache.get_cached_content.return_value = cached_data

    with (
        patch("app.api.web.get_web_cache", return_value=mock_web_cache),
        patch("app.api.web.get_web_fetcher"),
        patch("app.api.web.get_content_extractor"),
        patch("app.api.web.get_citation_manager"),
    ):
        response = test_client.post(
            "/api/web/fetch",
            json={"url": sample_url, "force_refresh": False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["url"] == sample_url
    assert data["title"] == sample_extracted_content["title"]
    assert data["content"] == sample_extracted_content["content"]
    assert data["citation"]["title"] == sample_citation.title


@pytest.mark.asyncio
async def test_fetch_web_content_fresh(
    test_client: TestClient,
    mock_web_fetcher: MagicMock,
    mock_content_extractor: MagicMock,
    mock_web_cache: MagicMock,
    mock_citation_manager: MagicMock,
    sample_url: str,
    sample_html: str,
    sample_extracted_content: Dict,
    sample_citation: Citation,
) -> None:
    """Test fetching fresh web content.

    Args:
        test_client (TestClient): FastAPI test client
        mock_web_fetcher (MagicMock): Mock WebFetcher
        mock_content_extractor (MagicMock): Mock ContentExtractor
        mock_web_cache (MagicMock): Mock WebCache
        mock_citation_manager (MagicMock): Mock CitationManager
        sample_url (str): Sample URL
        sample_html (str): Sample HTML
        sample_extracted_content (Dict): Sample content
        sample_citation (Citation): Sample citation
    """
    mock_web_cache.get_cached_content.return_value = None
    mock_web_fetcher.fetch_url.return_value = sample_html
    mock_content_extractor.extract_article.return_value = sample_extracted_content
    mock_citation_manager.create_citation.return_value = sample_citation

    with (
        patch("app.api.web.get_web_cache", return_value=mock_web_cache),
        patch("app.api.web.get_web_fetcher", return_value=mock_web_fetcher),
        patch("app.api.web.get_content_extractor", return_value=mock_content_extractor),
        patch("app.api.web.get_citation_manager", return_value=mock_citation_manager),
    ):
        response = test_client.post(
            "/api/web/fetch",
            json={"url": sample_url, "force_refresh": True},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["url"] == sample_url
    assert data["title"] == sample_extracted_content["title"]
    assert data["content"] == sample_extracted_content["content"]
    assert data["citation"]["title"] == sample_citation.title

    mock_web_fetcher.fetch_url.assert_called_once_with(sample_url)
    mock_content_extractor.extract_article.assert_called_once_with(sample_html, sample_url)
    mock_web_cache.cache_content.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_web_content_fetch_error(
    test_client: TestClient,
    mock_web_fetcher: MagicMock,
    mock_web_cache: MagicMock,
    sample_url: str,
) -> None:
    """Test error handling when fetching web content fails.

    Args:
        test_client (TestClient): FastAPI test client
        mock_web_fetcher (MagicMock): Mock WebFetcher
        mock_web_cache (MagicMock): Mock WebCache
        sample_url (str): Sample URL
    """
    mock_web_cache.get_cached_content.return_value = None
    mock_web_fetcher.fetch_url.side_effect = FetchError("Failed to fetch URL")

    with (
        patch("app.api.web.get_web_cache", return_value=mock_web_cache),
        patch("app.api.web.get_web_fetcher", return_value=mock_web_fetcher),
        patch("app.api.web.get_content_extractor"),
        patch("app.api.web.get_citation_manager"),
    ):
        response = test_client.post(
            "/api/web/fetch",
            json={"url": sample_url, "force_refresh": True},
        )

    assert response.status_code == 400
    assert "Failed to fetch URL" in response.json()["detail"]


@pytest.mark.asyncio
async def test_fetch_web_content_extraction_error(
    test_client: TestClient,
    mock_web_fetcher: MagicMock,
    mock_content_extractor: MagicMock,
    mock_web_cache: MagicMock,
    sample_url: str,
    sample_html: str,
) -> None:
    """Test error handling when content extraction fails.

    Args:
        test_client (TestClient): FastAPI test client
        mock_web_fetcher (MagicMock): Mock WebFetcher
        mock_content_extractor (MagicMock): Mock ContentExtractor
        mock_web_cache (MagicMock): Mock WebCache
        sample_url (str): Sample URL
        sample_html (str): Sample HTML
    """
    mock_web_cache.get_cached_content.return_value = None
    mock_web_fetcher.fetch_url.return_value = sample_html
    mock_content_extractor.extract_article.side_effect = ExtractionError(
        "Failed to extract content"
    )

    with (
        patch("app.api.web.get_web_cache", return_value=mock_web_cache),
        patch("app.api.web.get_web_fetcher", return_value=mock_web_fetcher),
        patch("app.api.web.get_content_extractor", return_value=mock_content_extractor),
        patch("app.api.web.get_citation_manager"),
    ):
        response = test_client.post(
            "/api/web/fetch",
            json={"url": sample_url, "force_refresh": True},
        )

    assert response.status_code == 400
    assert "Failed to extract content" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_article_citations(
    test_client: TestClient,
    mock_citation_manager: MagicMock,
    sample_citation: Citation,
) -> None:
    """Test getting citations for an article.

    Args:
        test_client (TestClient): FastAPI test client
        mock_citation_manager (MagicMock): Mock CitationManager
        sample_citation (Citation): Sample citation
    """
    article_id = uuid.uuid4()
    mock_citation_manager.get_citations_by_article.return_value = [sample_citation]

    with patch("app.api.web.get_citation_manager", return_value=mock_citation_manager):
        response = test_client.get(f"/api/web/citations/{article_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["citations"]) == 1
    assert data["citations"][0]["title"] == sample_citation.title


@pytest.mark.asyncio
async def test_get_article_citations_error(
    test_client: TestClient,
    mock_citation_manager: MagicMock,
) -> None:
    """Test error handling when getting article citations fails.

    Args:
        test_client (TestClient): FastAPI test client
        mock_citation_manager (MagicMock): Mock CitationManager
    """
    article_id = uuid.uuid4()
    mock_citation_manager.get_citations_by_article.side_effect = CitationError(
        "Failed to get citations"
    )

    with patch("app.api.web.get_citation_manager", return_value=mock_citation_manager):
        response = test_client.get(f"/api/web/citations/{article_id}")

    assert response.status_code == 500
    assert "Failed to retrieve citations" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_citation(
    test_client: TestClient,
    mock_citation_manager: MagicMock,
    sample_citation: Citation,
) -> None:
    """Test getting a specific citation.

    Args:
        test_client (TestClient): FastAPI test client
        mock_citation_manager (MagicMock): Mock CitationManager
        sample_citation (Citation): Sample citation
    """
    citation_id = uuid.uuid4()
    mock_citation_manager.get_citation.return_value = sample_citation

    with patch("app.api.web.get_citation_manager", return_value=mock_citation_manager):
        response = test_client.get(f"/api/web/citation/{citation_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == sample_citation.title


@pytest.mark.asyncio
async def test_get_citation_not_found(
    test_client: TestClient,
    mock_citation_manager: MagicMock,
) -> None:
    """Test getting a non-existent citation.

    Args:
        test_client (TestClient): FastAPI test client
        mock_citation_manager (MagicMock): Mock CitationManager
    """
    citation_id = uuid.uuid4()
    mock_citation_manager.get_citation.side_effect = CitationNotFoundError(
        f"Citation {citation_id} not found"
    )

    with patch("app.api.web.get_citation_manager", return_value=mock_citation_manager):
        response = test_client.get(f"/api/web/citation/{citation_id}")

    assert response.status_code == 404
    assert "Citation not found" in response.json()["detail"] 