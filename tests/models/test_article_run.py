"""Tests for article run model."""
import uuid
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.models.agent_memo import AgentMemo
from app.models.article_run import ArticleRun, ArticleRunStatus
from app.models.citation import Citation
from app.models.visual import Visual, VisualType


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


@pytest.fixture
def sample_visual() -> Visual:
    """Create a sample visual.

    Returns:
        Visual: Sample visual
    """
    return Visual(
        type=VisualType.IMAGE,
        source_data={"prompt": "Test prompt"},
        generated_content="base64_encoded_data",
        caption="Test caption",
        alt_text="Test alt text",
    )


@pytest.fixture
def sample_agent_memo(sample_citation: Citation) -> AgentMemo:
    """Create a sample agent memo.

    Args:
        sample_citation (Citation): Sample citation

    Returns:
        AgentMemo: Sample agent memo
    """
    return AgentMemo(
        agent_name="TestAgent",
        agent_role="TestRole",
        content="Test content",
        citations=[sample_citation],
    )


def test_article_run_creation() -> None:
    """Test creating an article run."""
    article_run = ArticleRun(user_query="Test query")
    assert article_run.id is not None
    assert article_run.created_at is not None
    assert article_run.status == ArticleRunStatus.PENDING
    assert article_run.user_query == "Test query"
    assert article_run.final_output is None
    assert article_run.agent_memos == []
    assert article_run.citations == []
    assert article_run.visuals == []
    assert article_run.error_message is None


def test_article_run_with_all_fields(
    sample_agent_memo: AgentMemo,
    sample_citation: Citation,
    sample_visual: Visual,
) -> None:
    """Test creating an article run with all fields.

    Args:
        sample_agent_memo (AgentMemo): Sample agent memo
        sample_citation (Citation): Sample citation
        sample_visual (Visual): Sample visual
    """
    article_run = ArticleRun(
        id=uuid.uuid4(),
        created_at=datetime.utcnow(),
        status=ArticleRunStatus.COMPLETED,
        user_query="Test query",
        final_output="Test output",
        agent_memos=[sample_agent_memo],
        citations=[sample_citation],
        visuals=[sample_visual],
    )

    assert article_run.id is not None
    assert article_run.created_at is not None
    assert article_run.status == ArticleRunStatus.COMPLETED
    assert article_run.user_query == "Test query"
    assert article_run.final_output == "Test output"
    assert len(article_run.agent_memos) == 1
    assert len(article_run.citations) == 1
    assert len(article_run.visuals) == 1


def test_article_run_validation_error() -> None:
    """Test article run validation error."""
    with pytest.raises(ValidationError):
        ArticleRun()  # Missing required user_query


def test_article_run_status_update() -> None:
    """Test updating article run status."""
    article_run = ArticleRun(user_query="Test query")
    assert article_run.status == ArticleRunStatus.PENDING

    article_run.status = ArticleRunStatus.IN_PROGRESS
    assert article_run.status == ArticleRunStatus.IN_PROGRESS

    article_run.status = ArticleRunStatus.COMPLETED
    assert article_run.status == ArticleRunStatus.COMPLETED


def test_article_run_add_memo(sample_agent_memo: AgentMemo) -> None:
    """Test adding a memo to an article run.

    Args:
        sample_agent_memo (AgentMemo): Sample agent memo
    """
    article_run = ArticleRun(user_query="Test query")
    article_run.agent_memos.append(sample_agent_memo)
    assert len(article_run.agent_memos) == 1
    assert article_run.agent_memos[0] == sample_agent_memo


def test_article_run_add_citation(sample_citation: Citation) -> None:
    """Test adding a citation to an article run.

    Args:
        sample_citation (Citation): Sample citation
    """
    article_run = ArticleRun(user_query="Test query")
    article_run.citations.append(sample_citation)
    assert len(article_run.citations) == 1
    assert article_run.citations[0] == sample_citation


def test_article_run_add_visual(sample_visual: Visual) -> None:
    """Test adding a visual to an article run.

    Args:
        sample_visual (Visual): Sample visual
    """
    article_run = ArticleRun(user_query="Test query")
    article_run.visuals.append(sample_visual)
    assert len(article_run.visuals) == 1
    assert article_run.visuals[0] == sample_visual


def test_article_run_error_handling() -> None:
    """Test article run error handling."""
    article_run = ArticleRun(user_query="Test query")
    article_run.status = ArticleRunStatus.FAILED
    article_run.error_message = "Test error"
    assert article_run.status == ArticleRunStatus.FAILED
    assert article_run.error_message == "Test error"


def test_article_run_json_serialization(
    sample_agent_memo: AgentMemo,
    sample_citation: Citation,
    sample_visual: Visual,
) -> None:
    """Test article run JSON serialization.

    Args:
        sample_agent_memo (AgentMemo): Sample agent memo
        sample_citation (Citation): Sample citation
        sample_visual (Visual): Sample visual
    """
    article_run = ArticleRun(
        user_query="Test query",
        final_output="Test output",
        agent_memos=[sample_agent_memo],
        citations=[sample_citation],
        visuals=[sample_visual],
    )

    json_data = article_run.model_dump_json()
    assert isinstance(json_data, str)

    loaded_article_run = ArticleRun.model_validate_json(json_data)
    assert loaded_article_run.user_query == article_run.user_query
    assert loaded_article_run.final_output == article_run.final_output
    assert len(loaded_article_run.agent_memos) == len(article_run.agent_memos)
    assert len(loaded_article_run.citations) == len(article_run.citations)
    assert len(loaded_article_run.visuals) == len(article_run.visuals) 