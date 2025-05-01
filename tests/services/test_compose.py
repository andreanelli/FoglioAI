"""Tests for article generation service."""
import asyncio
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.article import Article
from app.models.article_run import ArticleRun, ArticleRunStatus
from app.pubsub.scratchpad import Message, MessageType
from app.services.compose import ArticleGenerationService, MAX_CONCURRENT_GENERATIONS

# Test data
TOPIC = "Test Topic"
STYLE_GUIDE = {"tone": "formal"}


@pytest.fixture
def article_id() -> uuid.UUID:
    """Article ID fixture."""
    return uuid.uuid4()


@pytest.fixture
def article_run(article_id: uuid.UUID) -> ArticleRun:
    """Article run fixture."""
    return ArticleRun(
        id=article_id,
        status=ArticleRunStatus.PENDING,
        user_query=TOPIC,
    )


@pytest.fixture
def article(article_id: uuid.UUID) -> Article:
    """Article fixture."""
    return Article(
        id=article_id,
        title="Test Article",
        content="# Test Article\n\nThis is a test article.",
        topic=TOPIC,
        sources=["https://example.com/test"],
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def service() -> ArticleGenerationService:
    """Service fixture."""
    return ArticleGenerationService()


@pytest.mark.asyncio
async def test_start_generation_success(
    service: ArticleGenerationService,
    article_id: uuid.UUID,
    article_run: ArticleRun,
) -> None:
    """Test successful article generation start."""
    # Mock dependencies
    with patch("app.services.compose.generate_article_id", return_value=article_id), patch(
        "app.services.compose.save_article_run"
    ) as mock_save, patch("app.services.compose.ArticleOrchestrator") as mock_orch_cls:
        # Configure mocks
        mock_orch = AsyncMock()
        mock_orch_cls.return_value = mock_orch

        # Start generation
        result = await service.start_generation(TOPIC, STYLE_GUIDE)

        # Check result
        assert result == article_id

        # Verify mocks
        mock_save.assert_called_once()
        mock_orch_cls.assert_called_once_with(article_id)


@pytest.mark.asyncio
async def test_start_generation_max_concurrent(
    service: ArticleGenerationService,
    article_id: uuid.UUID,
) -> None:
    """Test maximum concurrent generations limit."""
    # Set active generations to max
    service._active_generations = MAX_CONCURRENT_GENERATIONS

    # Try to start generation
    with pytest.raises(RuntimeError, match="Maximum concurrent article generations reached"):
        await service.start_generation(TOPIC, STYLE_GUIDE)


@pytest.mark.asyncio
async def test_get_status_success(
    service: ArticleGenerationService,
    article_id: uuid.UUID,
    article_run: ArticleRun,
) -> None:
    """Test successful status retrieval."""
    # Mock dependencies
    with patch("app.services.compose.get_article_run", return_value=article_run):
        # Get status
        result = await service.get_status(article_id)

        # Check result
        assert result == article_run


@pytest.mark.asyncio
async def test_get_status_not_found(
    service: ArticleGenerationService,
    article_id: uuid.UUID,
) -> None:
    """Test status retrieval for non-existent article."""
    # Mock dependencies
    with patch("app.services.compose.get_article_run", return_value=None):
        # Try to get status
        with pytest.raises(ValueError, match=f"Article {article_id} not found"):
            await service.get_status(article_id)


@pytest.mark.asyncio
async def test_get_article_success(
    service: ArticleGenerationService,
    article_id: uuid.UUID,
    article_run: ArticleRun,
    article: Article,
) -> None:
    """Test successful article retrieval."""
    # Update article run status
    article_run.status = ArticleRunStatus.COMPLETED
    article_run.final_output = {
        "title": article.title,
        "content": article.content,
    }

    # Mock dependencies
    with patch("app.services.compose.get_article_run", return_value=article_run):
        # Get article
        result = await service.get_article(article_id)

        # Check result
        assert result.id == article.id
        assert result.title == article.title
        assert result.content == article.content
        assert result.topic == article.topic


@pytest.mark.asyncio
async def test_get_article_not_completed(
    service: ArticleGenerationService,
    article_id: uuid.UUID,
    article_run: ArticleRun,
) -> None:
    """Test article retrieval when not completed."""
    # Mock dependencies
    with patch("app.services.compose.get_article_run", return_value=article_run):
        # Try to get article
        with pytest.raises(ValueError, match=f"Article {article_id} is not completed"):
            await service.get_article(article_id)


@pytest.mark.asyncio
async def test_run_generation_timeout(
    service: ArticleGenerationService,
    article_id: uuid.UUID,
    article_run: ArticleRun,
) -> None:
    """Test article generation timeout."""
    # Mock dependencies
    with patch("app.services.compose.get_article_run", return_value=article_run), patch(
        "app.services.compose.save_article_run"
    ) as mock_save, patch("app.services.compose.ArticleOrchestrator") as mock_orch_cls:
        # Configure mocks
        mock_orch = AsyncMock()
        mock_orch.article_id = article_id
        mock_orch.generate_article = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_orch_cls.return_value = mock_orch

        # Run generation
        await service._run_generation(mock_orch, TOPIC, STYLE_GUIDE)

        # Verify article run was updated
        assert mock_save.call_args.args[0].status == ArticleRunStatus.FAILED
        assert "timeout" in mock_save.call_args.args[0].error_message.lower()


@pytest.mark.asyncio
async def test_run_generation_error(
    service: ArticleGenerationService,
    article_id: uuid.UUID,
    article_run: ArticleRun,
) -> None:
    """Test article generation error."""
    # Mock dependencies
    with patch("app.services.compose.get_article_run", return_value=article_run), patch(
        "app.services.compose.save_article_run"
    ) as mock_save, patch("app.services.compose.ArticleOrchestrator") as mock_orch_cls:
        # Configure mocks
        mock_orch = AsyncMock()
        mock_orch.article_id = article_id
        mock_orch.generate_article = AsyncMock(side_effect=ValueError("Test error"))
        mock_orch_cls.return_value = mock_orch

        # Run generation
        await service._run_generation(mock_orch, TOPIC, STYLE_GUIDE)

        # Verify article run was updated
        assert mock_save.call_args.args[0].status == ArticleRunStatus.FAILED
        assert "test error" in mock_save.call_args.args[0].error_message.lower()


@pytest.mark.asyncio
async def test_cleanup_active_generations(
    service: ArticleGenerationService,
    article_id: uuid.UUID,
    article_run: ArticleRun,
) -> None:
    """Test cleanup of active generations counter."""
    # Mock dependencies
    with patch("app.services.compose.get_article_run", return_value=article_run), patch(
        "app.services.compose.save_article_run"
    ), patch("app.services.compose.ArticleOrchestrator") as mock_orch_cls:
        # Configure mocks
        mock_orch = AsyncMock()
        mock_orch.article_id = article_id
        mock_orch.generate_article = AsyncMock(side_effect=ValueError("Test error"))
        mock_orch_cls.return_value = mock_orch

        # Set initial counter
        service._active_generations = 1

        # Run generation
        await service._run_generation(mock_orch, TOPIC, STYLE_GUIDE)

        # Verify counter was decremented
        assert service._active_generations == 0 