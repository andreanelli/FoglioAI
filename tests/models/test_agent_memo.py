"""Tests for agent memo model."""
import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.agent import AgentRole
from app.models.agent_memo import AgentMemo
from app.models.citation import Citation


@pytest.fixture
def sample_citation() -> Citation:
    """Create a sample citation.

    Returns:
        Citation: Sample citation
    """
    return Citation(
        url="https://example.com/article",
        title="Test Article",
        author="John Doe",
        publication_date=datetime.utcnow(),
        excerpt="Test excerpt",
    )


def test_agent_memo_creation() -> None:
    """Test creating an agent memo."""
    article_id = uuid.uuid4()
    memo = AgentMemo(
        agent_name="TestAgent",
        agent_role=AgentRole.HISTORIAN,
        article_id=article_id,
        content="Test content",
    )
    assert memo.id is not None
    assert memo.timestamp is not None
    assert memo.agent_name == "TestAgent"
    assert memo.agent_role == AgentRole.HISTORIAN
    assert memo.article_id == article_id
    assert memo.content == "Test content"
    assert memo.citations == []
    assert memo.parent_memo_id is None
    assert memo.is_reflection is False
    assert memo.confidence_score == 1.0


def test_agent_memo_with_all_fields(sample_citation: Citation) -> None:
    """Test creating an agent memo with all fields.

    Args:
        sample_citation (Citation): Sample citation
    """
    parent_id = uuid.uuid4()
    article_id = uuid.uuid4()
    memo = AgentMemo(
        id=uuid.uuid4(),
        agent_name="TestAgent",
        agent_role=AgentRole.HISTORIAN,
        article_id=article_id,
        timestamp=datetime.utcnow(),
        content="Test content",
        citations=[sample_citation],
        parent_memo_id=parent_id,
        is_reflection=True,
        confidence_score=0.8,
    )

    assert memo.id is not None
    assert memo.timestamp is not None
    assert memo.agent_name == "TestAgent"
    assert memo.agent_role == AgentRole.HISTORIAN
    assert memo.article_id == article_id
    assert memo.content == "Test content"
    assert len(memo.citations) == 1
    assert memo.parent_memo_id == parent_id
    assert memo.is_reflection is True
    assert memo.confidence_score == 0.8


def test_agent_memo_validation_error() -> None:
    """Test agent memo validation error."""
    with pytest.raises(ValidationError):
        AgentMemo()  # Missing required fields

    with pytest.raises(ValidationError):
        AgentMemo(
            agent_name="TestAgent",
            agent_role=AgentRole.HISTORIAN,
            content="Test content",
            confidence_score=1.5,  # Invalid score > 1.0
        )

    with pytest.raises(ValidationError):
        AgentMemo(
            agent_name="TestAgent",
            agent_role=AgentRole.HISTORIAN,
            content="Test content",
            confidence_score=-0.1,  # Invalid score < 0.0
        )

    with pytest.raises(ValidationError):
        AgentMemo(
            agent_name="TestAgent",
            agent_role="invalid_role",  # Invalid role
            content="Test content",
            article_id=uuid.uuid4(),
        )


def test_agent_memo_add_citation(sample_citation: Citation) -> None:
    """Test adding a citation to an agent memo.

    Args:
        sample_citation (Citation): Sample citation
    """
    article_id = uuid.uuid4()
    memo = AgentMemo(
        agent_name="TestAgent",
        agent_role=AgentRole.HISTORIAN,
        article_id=article_id,
        content="Test content",
    )
    memo.citations.append(sample_citation)
    assert len(memo.citations) == 1
    assert memo.citations[0] == sample_citation


def test_agent_memo_reflection() -> None:
    """Test creating a reflection memo."""
    parent_id = uuid.uuid4()
    article_id = uuid.uuid4()
    memo = AgentMemo(
        agent_name="TestAgent",
        agent_role=AgentRole.HISTORIAN,
        article_id=article_id,
        content="Test reflection",
        parent_memo_id=parent_id,
        is_reflection=True,
        confidence_score=0.9,
    )
    assert memo.parent_memo_id == parent_id
    assert memo.is_reflection is True
    assert memo.confidence_score == 0.9


def test_agent_memo_json_serialization(sample_citation: Citation) -> None:
    """Test agent memo JSON serialization.

    Args:
        sample_citation (Citation): Sample citation
    """
    parent_id = uuid.uuid4()
    article_id = uuid.uuid4()
    memo = AgentMemo(
        agent_name="TestAgent",
        agent_role=AgentRole.HISTORIAN,
        article_id=article_id,
        content="Test content",
        citations=[sample_citation],
        parent_memo_id=parent_id,
        is_reflection=True,
        confidence_score=0.8,
    )

    json_data = memo.model_dump_json()
    assert isinstance(json_data, str)

    loaded_memo = AgentMemo.model_validate_json(json_data)
    assert loaded_memo.agent_name == memo.agent_name
    assert loaded_memo.agent_role == memo.agent_role
    assert loaded_memo.article_id == memo.article_id
    assert loaded_memo.content == memo.content
    assert len(loaded_memo.citations) == len(memo.citations)
    assert loaded_memo.parent_memo_id == memo.parent_memo_id
    assert loaded_memo.is_reflection == memo.is_reflection
    assert loaded_memo.confidence_score == memo.confidence_score 