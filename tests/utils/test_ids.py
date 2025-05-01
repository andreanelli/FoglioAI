"""Tests for ID generation utilities."""
import uuid

from app.utils.ids import (
    generate_article_id,
    generate_citation_id,
    generate_memo_id,
    generate_visual_id,
)


def test_generate_article_id() -> None:
    """Test article ID generation."""
    id1 = generate_article_id()
    id2 = generate_article_id()

    assert isinstance(id1, uuid.UUID)
    assert isinstance(id2, uuid.UUID)
    assert id1 != id2


def test_generate_memo_id() -> None:
    """Test memo ID generation."""
    id1 = generate_memo_id()
    id2 = generate_memo_id()

    assert isinstance(id1, uuid.UUID)
    assert isinstance(id2, uuid.UUID)
    assert id1 != id2


def test_generate_citation_id() -> None:
    """Test citation ID generation."""
    id1 = generate_citation_id()
    id2 = generate_citation_id()

    assert isinstance(id1, uuid.UUID)
    assert isinstance(id2, uuid.UUID)
    assert id1 != id2


def test_generate_visual_id() -> None:
    """Test visual ID generation."""
    id1 = generate_visual_id()
    id2 = generate_visual_id()

    assert isinstance(id1, uuid.UUID)
    assert isinstance(id2, uuid.UUID)
    assert id1 != id2 