"""Tests for article composition API endpoints."""
import asyncio
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sse_starlette.sse import EventSourceResponse

from app.api.compose import router
from app.models.article import Article
from app.models.article_run import ArticleRun, ArticleRunStatus
from app.models.compose import ArticleProgress, ArticleStatusResponse, ComposeRequest
from app.pubsub.scratchpad import Message, MessageType

# Create test app
app = FastAPI()
app.include_router(router)


@pytest.fixture
def article_id() -> uuid.UUID:
    """Article ID fixture."""
    return uuid.uuid4()


@pytest.fixture
def article_run(article_id: uuid.UUID) -> ArticleRun:
    """Article run fixture."""
    return ArticleRun(
        id=article_id,
        created_at=datetime.utcnow(),
        status=ArticleRunStatus.PENDING,
        user_query="Test query",
        agent_outputs={},
        errors=[],
        citations=[],
    )


@pytest.mark.asyncio
async def test_compose_article_success(article_id: uuid.UUID) -> None:
    """Test successful article composition request."""
    # Mock service
    with patch("app.api.compose.ArticleGenerationService") as mock_service_cls:
        mock_service = MagicMock()
        mock_service.start_generation = AsyncMock(return_value=article_id)
        mock_service.cleanup = AsyncMock()
        mock_service_cls.return_value = mock_service

        # Make request
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/compose",
                json={
                    "topic": "Test Topic",
                    "style_guide": {"tone": "formal"},
                },
            )

        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["article_id"] == str(article_id)

        # Verify service calls
        mock_service.start_generation.assert_called_once_with(
            topic="Test Topic",
            style_guide={"tone": "formal"},
        )


@pytest.mark.asyncio
async def test_compose_article_failure() -> None:
    """Test failed article composition request."""
    # Mock service
    with patch("app.api.compose.ArticleGenerationService") as mock_service_cls:
        mock_service = MagicMock()
        mock_service.start_generation = AsyncMock(side_effect=Exception("Test error"))
        mock_service_cls.return_value = mock_service

        # Make request
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/compose",
                json={
                    "topic": "Test Topic",
                },
            )

        # Check response
        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Test error"


@pytest.mark.asyncio
async def test_compose_article_rate_limit() -> None:
    """Test rate limiting for article composition."""
    # Mock service
    with patch("app.api.compose.ArticleGenerationService") as mock_service_cls:
        mock_service = MagicMock()
        mock_service.start_generation = AsyncMock(return_value=uuid.uuid4())
        mock_service_cls.return_value = mock_service

        # Make requests
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make 11 requests (1 over limit)
            responses = []
            for _ in range(11):
                response = await client.post(
                    "/api/compose",
                    json={"topic": "Test Topic"},
                )
                responses.append(response)

        # First 10 should succeed
        for response in responses[:10]:
            assert response.status_code == 200

        # 11th should fail with rate limit error
        assert responses[10].status_code == 429
        assert "rate limit exceeded" in responses[10].json()["detail"].lower()


@pytest.mark.asyncio
async def test_article_events_timeout() -> None:
    """Test timeout handling for article events."""
    # Mock service
    with patch("app.api.compose.ArticleGenerationService") as mock_service_cls:
        mock_service = MagicMock()

        async def slow_events(article_id: uuid.UUID) -> AsyncGenerator[Message, None]:
            # Simulate slow event generation
            await asyncio.sleep(2)  # Longer than test timeout
            yield Message(
                type=MessageType.PROGRESS,
                agent_id="test",
                article_id=article_id,
                content={"message": "Test"},
            )

        mock_service.subscribe_to_events = slow_events
        mock_service_cls.return_value = mock_service

        # Override timeout for test
        with patch("app.api.compose.GENERATION_TIMEOUT", 1):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    f"/api/compose/{uuid.uuid4()}/events",
                )

                # Should get timeout error
                assert response.status_code == 200
                assert "timeout" in response.text.lower()


@pytest.mark.asyncio
async def test_get_article_status_not_found(article_id: uuid.UUID) -> None:
    """Test getting status of non-existent article."""
    # Mock storage
    with patch("app.api.compose.get_article_run", return_value=None):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(f"/api/compose/{article_id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Article not found"


@pytest.mark.asyncio
async def test_get_article_html_not_ready(article_id: uuid.UUID, article_run: ArticleRun) -> None:
    """Test getting HTML for incomplete article."""
    article_run.status = ArticleRunStatus.IN_PROGRESS

    # Mock storage
    with patch("app.api.compose.get_article_run", return_value=article_run):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(f"/api/compose/{article_id}/html")

        assert response.status_code == 400
        assert response.json()["detail"] == "Article not ready"


@pytest.mark.asyncio
async def test_get_article_html_success(article_id: uuid.UUID, article_run: ArticleRun) -> None:
    """Test successful HTML retrieval."""
    article_run.status = ArticleRunStatus.COMPLETED
    article_run.article = Article(
        id=article_id,
        title="Test Article",
        content="Test content",
        topic="Test topic",
    )

    # Mock storage and renderer
    with (
        patch("app.api.compose.get_article_run", return_value=article_run),
        patch("app.api.compose.template_renderer") as mock_renderer,
    ):
        mock_renderer.render_article.return_value = "<html>Test</html>"

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(f"/api/compose/{article_id}/html")

        assert response.status_code == 200
        assert response.text == "<html>Test</html>"
        mock_renderer.render_article.assert_called_once_with(article_run.article)


@pytest.mark.asyncio
async def test_get_article_status_success(
    article_id: uuid.UUID,
    article_run: ArticleRun,
) -> None:
    """Test successful article status request."""
    # Mock storage
    with patch("app.api.compose.get_article_run", return_value=article_run):
        # Make request
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(f"/api/compose/{article_id}")

        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["article_id"] == str(article_id)
        assert data["status"] == "pending"
        assert data["progress"] == {
            "total": 0,
            "completed": 0,
            "percentage": 0,
        }
        assert data["errors"] == []


@pytest.mark.asyncio
async def test_get_article_events_success(
    article_id: uuid.UUID,
    article_run: ArticleRun,
) -> None:
    """Test successful article events request."""
    # Mock message generator
    async def mock_message_generator() -> AsyncGenerator[Dict[str, str], None]:
        yield {
            "event": "agent_started",
            "data": json.dumps({
                "type": "agent_started",
                "content": {"agent_id": "test_agent"},
            }),
        }
        yield {
            "event": "completed",
            "data": json.dumps({
                "type": "completed",
                "content": {"status": "success"},
            }),
        }

    # Mock service
    with (
        patch("app.api.compose.get_article_run", return_value=article_run),
        patch("app.api.compose._event_generator", side_effect=mock_message_generator),
    ):
        # Make request
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(f"/api/compose/{article_id}/events")

        # Check response
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"


@pytest.mark.asyncio
async def test_get_article_events_not_found(article_id: uuid.UUID) -> None:
    """Test article events request for non-existent article."""
    # Mock storage
    with patch("app.api.compose.get_article_run", return_value=None):
        # Make request
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(f"/api/compose/{article_id}/events")

        # Check response
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Article not found"


@pytest.mark.asyncio
async def test_get_article_html_not_found(client: AsyncClient):
    """Test getting HTML for non-existent article."""
    article_id = uuid.uuid4()

    # Mock article run not found
    with patch("app.api.compose.get_article_run") as mock_get_run:
        mock_get_run.return_value = None

        # Make request
        response = await client.get(f"/api/compose/{article_id}/html")

        assert response.status_code == 404
        assert response.json()["detail"] == "Article not found"


@pytest.mark.asyncio
async def test_get_article_html_missing_data(client: AsyncClient):
    """Test getting HTML with missing article data."""
    article_id = uuid.uuid4()

    # Mock completed run but missing article
    with patch("app.api.compose.get_article_run") as mock_get_run:
        mock_get_run.return_value = MagicMock(
            status="completed",
            article=None,
        )

        # Make request
        response = await client.get(f"/api/compose/{article_id}/html")

        assert response.status_code == 500
        assert response.json()["detail"] == "Article data not found" 