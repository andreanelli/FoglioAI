"""Tests for citation manager module."""
import uuid
from datetime import datetime
from typing import Generator
from unittest.mock import MagicMock

import pytest
import redis
from pydantic import AnyHttpUrl

from app.models.citation import Citation
from app.web.citations import CitationError, CitationManager, CitationNotFoundError


@pytest.fixture
def redis_mock() -> MagicMock:
    """Create a mock Redis client.

    Returns:
        MagicMock: Mock Redis client
    """
    return MagicMock(spec=redis.Redis)


@pytest.fixture
def citation_manager(redis_mock: MagicMock) -> CitationManager:
    """Create a CitationManager instance with mock Redis.

    Args:
        redis_mock (MagicMock): Mock Redis client

    Returns:
        CitationManager: Citation manager instance
    """
    return CitationManager(redis_mock)


@pytest.fixture
def sample_url() -> AnyHttpUrl:
    """Create a sample URL.

    Returns:
        AnyHttpUrl: Sample URL
    """
    return AnyHttpUrl("https://example.com/article")


@pytest.fixture
def sample_content() -> dict:
    """Create sample content metadata.

    Returns:
        dict: Sample content
    """
    return {
        "title": "Test Article",
        "author": "John Doe",
        "publication_date": datetime.utcnow(),
    }


@pytest.fixture
def sample_citation(sample_url: AnyHttpUrl, sample_content: dict) -> Citation:
    """Create a sample citation.

    Args:
        sample_url (AnyHttpUrl): Sample URL
        sample_content (dict): Sample content

    Returns:
        Citation: Sample citation
    """
    return Citation(
        url=sample_url,
        title=sample_content["title"],
        author=sample_content["author"],
        publication_date=sample_content["publication_date"],
        excerpt="Test excerpt",
    )


def test_create_citation(
    citation_manager: CitationManager,
    sample_url: AnyHttpUrl,
    sample_content: dict,
    redis_mock: MagicMock,
) -> None:
    """Test creating a citation.

    Args:
        citation_manager (CitationManager): Citation manager instance
        sample_url (AnyHttpUrl): Sample URL
        sample_content (dict): Sample content
        redis_mock (MagicMock): Mock Redis client
    """
    citation = citation_manager.create_citation(
        url=sample_url,
        content=sample_content,
        excerpt="Test excerpt",
    )

    assert citation.url == sample_url
    assert citation.title == sample_content["title"]
    assert citation.author == sample_content["author"]
    assert citation.publication_date == sample_content["publication_date"]
    assert citation.excerpt == "Test excerpt"

    # Verify Redis storage
    redis_mock.set.assert_called_once()
    args = redis_mock.set.call_args[0]
    assert args[0].startswith("citation:")
    assert "Test excerpt" in args[1]  # Citation JSON should contain the excerpt
    assert args[2] == 86400  # TTL


def test_create_citation_error(
    citation_manager: CitationManager,
    sample_url: AnyHttpUrl,
    sample_content: dict,
    redis_mock: MagicMock,
) -> None:
    """Test error handling when creating a citation.

    Args:
        citation_manager (CitationManager): Citation manager instance
        sample_url (AnyHttpUrl): Sample URL
        sample_content (dict): Sample content
        redis_mock (MagicMock): Mock Redis client
    """
    redis_mock.set.side_effect = redis.RedisError("Connection failed")

    with pytest.raises(CitationError, match="Failed to create citation"):
        citation_manager.create_citation(
            url=sample_url,
            content=sample_content,
            excerpt="Test excerpt",
        )


def test_get_citation(
    citation_manager: CitationManager,
    sample_citation: Citation,
    redis_mock: MagicMock,
) -> None:
    """Test retrieving a citation.

    Args:
        citation_manager (CitationManager): Citation manager instance
        sample_citation (Citation): Sample citation
        redis_mock (MagicMock): Mock Redis client
    """
    redis_mock.get.return_value = sample_citation.model_dump_json()

    citation = citation_manager.get_citation(sample_citation.id)

    assert citation is not None
    assert citation.id == sample_citation.id
    assert citation.url == sample_citation.url
    assert citation.title == sample_citation.title
    assert citation.excerpt == sample_citation.excerpt

    redis_mock.get.assert_called_once_with(f"citation:{sample_citation.id}")


def test_get_citation_not_found(
    citation_manager: CitationManager,
    redis_mock: MagicMock,
) -> None:
    """Test retrieving a non-existent citation.

    Args:
        citation_manager (CitationManager): Citation manager instance
        redis_mock (MagicMock): Mock Redis client
    """
    redis_mock.get.return_value = None
    citation_id = uuid.uuid4()

    with pytest.raises(CitationNotFoundError, match=f"Citation {citation_id} not found"):
        citation_manager.get_citation(citation_id)


def test_get_citations_by_article(
    citation_manager: CitationManager,
    sample_citation: Citation,
    redis_mock: MagicMock,
) -> None:
    """Test retrieving citations for an article.

    Args:
        citation_manager (CitationManager): Citation manager instance
        sample_citation (Citation): Sample citation
        redis_mock (MagicMock): Mock Redis client
    """
    article_id = uuid.uuid4()
    redis_mock.smembers.return_value = {str(sample_citation.id).encode()}
    redis_mock.get.return_value = sample_citation.model_dump_json()

    citations = citation_manager.get_citations_by_article(article_id)

    assert len(citations) == 1
    assert citations[0].id == sample_citation.id

    redis_mock.smembers.assert_called_once_with(f"article:citations:{article_id}")
    redis_mock.get.assert_called_once_with(f"citation:{sample_citation.id}")


def test_get_citations_by_article_empty(
    citation_manager: CitationManager,
    redis_mock: MagicMock,
) -> None:
    """Test retrieving citations for an article with no citations.

    Args:
        citation_manager (CitationManager): Citation manager instance
        redis_mock (MagicMock): Mock Redis client
    """
    article_id = uuid.uuid4()
    redis_mock.smembers.return_value = set()

    citations = citation_manager.get_citations_by_article(article_id)

    assert len(citations) == 0
    redis_mock.smembers.assert_called_once_with(f"article:citations:{article_id}")


def test_update_citation(
    citation_manager: CitationManager,
    sample_citation: Citation,
    redis_mock: MagicMock,
) -> None:
    """Test updating a citation.

    Args:
        citation_manager (CitationManager): Citation manager instance
        sample_citation (Citation): Sample citation
        redis_mock (MagicMock): Mock Redis client
    """
    redis_mock.exists.return_value = True
    citation_manager.update_citation(sample_citation)

    redis_mock.exists.assert_called_once_with(f"citation:{sample_citation.id}")
    redis_mock.set.assert_called_once()
    args = redis_mock.set.call_args[0]
    assert args[0] == f"citation:{sample_citation.id}"
    assert args[2] == 86400  # TTL


def test_update_citation_not_found(
    citation_manager: CitationManager,
    sample_citation: Citation,
    redis_mock: MagicMock,
) -> None:
    """Test updating a non-existent citation.

    Args:
        citation_manager (CitationManager): Citation manager instance
        sample_citation (Citation): Sample citation
        redis_mock (MagicMock): Mock Redis client
    """
    redis_mock.exists.return_value = False

    with pytest.raises(CitationNotFoundError, match=f"Citation {sample_citation.id} not found"):
        citation_manager.update_citation(sample_citation)


def test_add_citation_to_article(
    citation_manager: CitationManager,
    sample_citation: Citation,
    redis_mock: MagicMock,
) -> None:
    """Test adding a citation to an article.

    Args:
        citation_manager (CitationManager): Citation manager instance
        sample_citation (Citation): Sample citation
        redis_mock (MagicMock): Mock Redis client
    """
    article_id = uuid.uuid4()
    redis_mock.exists.return_value = True

    citation_manager.add_citation_to_article(article_id, sample_citation.id)

    redis_mock.exists.assert_called_once_with(f"citation:{sample_citation.id}")
    redis_mock.sadd.assert_called_once_with(
        f"article:citations:{article_id}",
        str(sample_citation.id),
    )
    redis_mock.expire.assert_called_once_with(f"article:citations:{article_id}", 86400)


def test_add_citation_to_article_not_found(
    citation_manager: CitationManager,
    redis_mock: MagicMock,
) -> None:
    """Test adding a non-existent citation to an article.

    Args:
        citation_manager (CitationManager): Citation manager instance
        redis_mock (MagicMock): Mock Redis client
    """
    article_id = uuid.uuid4()
    citation_id = uuid.uuid4()
    redis_mock.exists.return_value = False

    with pytest.raises(CitationNotFoundError, match=f"Citation {citation_id} not found"):
        citation_manager.add_citation_to_article(article_id, citation_id)


def test_remove_citation_from_article(
    citation_manager: CitationManager,
    sample_citation: Citation,
    redis_mock: MagicMock,
) -> None:
    """Test removing a citation from an article.

    Args:
        citation_manager (CitationManager): Citation manager instance
        sample_citation (Citation): Sample citation
        redis_mock (MagicMock): Mock Redis client
    """
    article_id = uuid.uuid4()

    citation_manager.remove_citation_from_article(article_id, sample_citation.id)

    redis_mock.srem.assert_called_once_with(
        f"article:citations:{article_id}",
        str(sample_citation.id),
    )


def test_delete_citation(
    citation_manager: CitationManager,
    sample_citation: Citation,
    redis_mock: MagicMock,
) -> None:
    """Test deleting a citation.

    Args:
        citation_manager (CitationManager): Citation manager instance
        sample_citation (Citation): Sample citation
        redis_mock (MagicMock): Mock Redis client
    """
    redis_mock.exists.return_value = True

    citation_manager.delete_citation(sample_citation.id)

    redis_mock.exists.assert_called_once_with(f"citation:{sample_citation.id}")
    redis_mock.delete.assert_called_once_with(f"citation:{sample_citation.id}")


def test_delete_citation_not_found(
    citation_manager: CitationManager,
    redis_mock: MagicMock,
) -> None:
    """Test deleting a non-existent citation.

    Args:
        citation_manager (CitationManager): Citation manager instance
        redis_mock (MagicMock): Mock Redis client
    """
    citation_id = uuid.uuid4()
    redis_mock.exists.return_value = False

    with pytest.raises(CitationNotFoundError, match=f"Citation {citation_id} not found"):
        citation_manager.delete_citation(citation_id) 