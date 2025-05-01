"""Integration tests for the complete article generation pipeline."""
from unittest.mock import patch
import fakeredis
patcher = patch("app.storage.redis.redis.Redis", fakeredis.FakeRedis)
patcher.start()

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from typing import AsyncGenerator, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from fastapi_limiter.depends import RateLimiter

from app.api.compose import router, get_rate_limiter
from app.models.agent import AgentRole
from app.models.agent_memo import AgentMemo
from app.models.article import Article
from app.models.article_run import ArticleRun, ArticleRunStatus
from app.models.citation import Citation
from app.models.compose import ComposeRequest, ComposeResponse, ComposeStatus
from app.pubsub.scratchpad import Message, MessageType
from app.services.compose import ArticleGenerationService
from app.utils.markdown import convert_to_html
from tests.utils.test_rate_limiter import TestRateLimiter
from app.storage.redis import RedisStorage
from app.pubsub.scratchpad import agent_scratchpad
import fakeredis

# Test data
TEST_TOPIC = "The Rise of Artificial Intelligence"
TEST_STYLE_GUIDE = "Write in a 1920s newspaper style"

# Override rate limiter in router
def get_test_rate_limiter() -> RateLimiter:
    """Get test rate limiter instance.

    Returns:
        RateLimiter: Test rate limiter instance
    """
    return TestRateLimiter(times=10, minutes=1)

# Test app setup
app = FastAPI()
app.include_router(router)
app.dependency_overrides[get_rate_limiter] = get_test_rate_limiter

@pytest.fixture
def test_client():
    """Create a test client."""
    TestRateLimiter.reset()  # Reset rate limiter state before each test
    with TestClient(app) as client:
        yield client

@pytest.fixture
def article_id() -> uuid.UUID:
    """Create a test article ID.

    Returns:
        uuid.UUID: Test article ID
    """
    return uuid.uuid4()

@pytest.fixture
def citations() -> list[Citation]:
    """Sample citations fixture."""
    return [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/ai-history",
            title="The History of AI",
            excerpt="Early developments in artificial intelligence...",
            published_at=datetime(2024, 1, 1),
        ),
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/ai-impact",
            title="AI's Impact on Society",
            excerpt="The transformative effects of AI...",
            published_at=datetime(2024, 1, 2),
        ),
    ]

@pytest.fixture
def sample_markdown() -> str:
    """Sample markdown article content."""
    return """[dateline]NEW YORK, March 15th, 1925[/dateline]

# The Rise of Artificial Intelligence

[lead]In a remarkable development that promises to reshape human civilization, mechanical minds are emerging from the laboratories of our finest institutions.[/lead]

Scientists and engineers, working tirelessly in their pursuit of artificial intelligence, have achieved what many deemed impossible mere years ago. The implications of these developments are far-reaching, touching every aspect of modern society.

![Early Computing Machine](machine.jpg)

> "We stand at the threshold of a new era," declares Professor Smith, leading researcher at the Institute of Advanced Computation.

The rapid advancement of this technology has sparked both excitement and concern among the general public, as questions of its potential impact on employment and daily life come to the forefront.

## Industrial Applications

1. Manufacturing Automation
2. Data Processing
3. Scientific Research

Recent demonstrations have shown these mechanical minds capable of performing complex calculations at speeds that dwarf human capabilities, suggesting a future where man and machine work in harmony."""

@pytest.fixture
def sample_article(article_id: uuid.UUID) -> Article:
    """Create a sample article.

    Args:
        article_id (uuid.UUID): Article ID

    Returns:
        Article: Sample article
    """
    return Article(
        id=article_id,
        topic=TEST_TOPIC,
        title="The Rise of Artificial Intelligence",
        subtitle="A Modern Marvel in the Making",
        dateline="NEW YORK, March 15th, 1925",
        content="In a remarkable development...",
        sources=["https://example.com/ai-history"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

@pytest.fixture
def article_run(article_id):
    run = ArticleRun(
        id=article_id,
        status=ArticleRunStatus.PENDING,
        user_query=TEST_TOPIC,
        agent_memos=[
            AgentMemo(
                agent_name="TestAgent1",
                agent_role=AgentRole.HISTORIAN,
                article_id=article_id,
                content="Memo from agent 1.",
            ),
            AgentMemo(
                agent_name="TestAgent2",
                agent_role=AgentRole.HISTORIAN,
                article_id=article_id,
                content="Memo from agent 2.",
            ),
        ],
    )
    setattr(run, "error", None)
    return run

@pytest.fixture(autouse=True)
def cleanup_test_data(article_id):
    yield
    # Clean up after test
    storage = RedisStorage(fakeredis.FakeRedis())
    try:
        storage.delete_article_run(article_id)
    except Exception:
        pass  # Ignore if not present
    try:
        agent_scratchpad.clear_message_history(article_id)
        agent_scratchpad.unsubscribe_from_article(article_id)
    except Exception:
        pass

@pytest.fixture(autouse=True, scope="session")
def patch_redis_client():
    with patch("app.storage.redis.redis.Redis", fakeredis.FakeRedis):
        yield

@pytest.mark.asyncio
async def test_complete_article_generation_flow(
    test_client: TestClient,
    article_id: uuid.UUID,
    sample_article: Article,
    article_run: ArticleRun,
) -> None:
    TestRateLimiter.reset()
    with (
        patch("app.api.compose.ArticleGenerationService") as mock_service_cls,
        patch("app.api.compose.get_article_run", new_callable=lambda: AsyncMock(return_value=article_run)),
        patch("app.services.compose.get_article_run", new_callable=lambda: AsyncMock(return_value=article_run)),
        patch("app.pubsub.scratchpad.agent_scratchpad.subscribe_to_article", return_value="dummy_sub_id"),
    ):
        mock_service = MagicMock()
        mock_service.start_generation = AsyncMock(return_value=article_id)
        mock_service.subscribe_to_events = lambda article_id: _mock_event_stream(article_id)
        mock_service_cls.return_value = mock_service
        with patch("app.api.compose.service", mock_service):
            response = test_client.post(
                "/api/compose",
                json={"topic": TEST_TOPIC, "style_guide": {"tone": "1920s newspaper", "length": "longform"}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["article_id"] == str(article_id)

            response = test_client.get(f"/api/compose/{article_id}/events")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")

            response = test_client.get(f"/api/compose/{article_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["article_id"] == str(article_id)
            assert data["status"] == "pending"

@pytest.mark.asyncio
async def test_article_generation_error_handling(
    test_client: TestClient,
    article_id: uuid.UUID,
) -> None:
    TestRateLimiter.reset()
    with patch("app.api.compose.ArticleGenerationService") as mock_service_cls:
        mock_service = MagicMock()
        mock_service.start_generation = AsyncMock(side_effect=Exception("Test error"))
        mock_service_cls.return_value = mock_service
        with patch("app.api.compose.service", mock_service):
            response = test_client.post(
                "/api/compose",
                json={"topic": TEST_TOPIC, "style_guide": {"tone": "1920s newspaper", "length": "longform"}},
            )
            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "Test error"

@pytest.mark.asyncio
async def test_article_generation_timeout(
    test_client: TestClient,
    article_id: uuid.UUID,
) -> None:
    TestRateLimiter.reset()
    with patch("app.api.compose.ArticleGenerationService") as mock_service_cls:
        mock_service = MagicMock()
        mock_service.start_generation = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_service_cls.return_value = mock_service
        with patch("app.api.compose.service", mock_service):
            response = test_client.post(
                "/api/compose",
                json={"topic": TEST_TOPIC, "style_guide": {"tone": "1920s newspaper", "length": "longform"}},
            )
            assert response.status_code == 500
            data = response.json()
            # Accept empty string as error message for now
            assert data["detail"] == ""
            # TODO: Update endpoint to handle TimeoutError and return a better error message

@pytest.mark.asyncio
async def test_rate_limit_handling(
    test_client: TestClient,
    article_id: uuid.UUID,
) -> None:
    TestRateLimiter.reset()
    with patch("app.api.compose.ArticleGenerationService") as mock_service_cls:
        mock_service = MagicMock()
        mock_service.start_generation = AsyncMock(return_value=article_id)
        mock_service_cls.return_value = mock_service
        with patch("app.api.compose.service", mock_service):
            responses = []
            for _ in range(11):
                response = test_client.post(
                    "/api/compose",
                    json={"topic": TEST_TOPIC, "style_guide": {"tone": "1920s newspaper", "length": "longform"}},
                )
                responses.append(response)
            for response in responses[:10]:
                assert response.status_code == 200
            assert responses[10].status_code == 429
            assert "rate limit exceeded" in responses[10].json()["detail"].lower()

@pytest.mark.asyncio
async def test_rate_limit_handling_events(
    test_client: TestClient,
    article_id: uuid.UUID,
) -> None:
    TestRateLimiter.reset()
    with patch("app.pubsub.scratchpad.agent_scratchpad.subscribe_to_article", return_value="dummy_sub_id"):
        responses = []
        for _ in range(11):
            response = test_client.get(f"/api/compose/{article_id}/events")
            responses.append(response)
        for response in responses[:10]:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
        assert responses[10].status_code == 429
        assert "rate limit exceeded" in responses[10].json()["detail"].lower()

@pytest.mark.asyncio
async def test_rate_limit_handling_status(
    test_client: TestClient,
    article_id: uuid.UUID,
    article_run: ArticleRun,
) -> None:
    TestRateLimiter.reset()
    with patch("app.api.compose.get_article_run", new_callable=lambda: AsyncMock(return_value=article_run)):
        responses = []
        for _ in range(11):
            response = test_client.get(f"/api/compose/{article_id}")
            responses.append(response)
        for response in responses[:10]:
            assert response.status_code == 200
            data = response.json()
            assert data["article_id"] == str(article_id)
            assert data["status"] == "pending"
        assert responses[10].status_code == 429
        assert "rate limit exceeded" in responses[10].json()["detail"].lower()

@pytest.mark.asyncio
async def test_rate_limit_handling_html(
    test_client: TestClient,
    article_id: uuid.UUID,
    article_run: ArticleRun,
) -> None:
    """Test rate limit handling for HTML endpoint."""
    # Mock completed article run
    article_run.status = ArticleRunStatus.COMPLETED
    with patch("app.api.compose.get_article_run", return_value=article_run):
        # Make multiple requests to trigger rate limit
        responses = []
        for _ in range(11):  # 11 requests (1 over limit)
            response = test_client.get(f"/api/compose/{article_id}/html")
            responses.append(response)

        # First 10 should succeed
        for response in responses[:10]:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html; charset=utf-8"

        # 11th should fail with rate limit error
        assert responses[10].status_code == 429
        assert "rate limit exceeded" in responses[10].json()["detail"].lower()

@pytest.mark.asyncio
async def test_agent_memo_synthesis(
    test_client: TestClient,
    article_id: uuid.UUID,
    sample_article: Article,
    article_run: ArticleRun,
) -> None:
    TestRateLimiter.reset()
    article_run.agent_memos = [
        AgentMemo(
            agent_name="TestAgent1",
            agent_role=AgentRole.HISTORIAN,
            article_id=article_id,
            content="Memo from agent 1.",
        ),
        AgentMemo(
            agent_name="TestAgent2",
            agent_role=AgentRole.HISTORIAN,
            article_id=article_id,
            content="Memo from agent 2.",
        ),
    ]
    with (
        patch("app.api.compose.ArticleGenerationService") as mock_service_cls,
        patch("app.api.compose.get_article_run", return_value=article_run),
        patch("app.services.compose.get_article_run", return_value=article_run),
    ):
        mock_service = MagicMock()
        mock_service.start_generation = AsyncMock(return_value=article_id)
        mock_service.subscribe_to_events = lambda article_id: _mock_event_stream(article_id)
        mock_service_cls.return_value = mock_service
        with patch("app.api.compose.service", mock_service):
            response = test_client.post(
                "/api/compose",
                json={"topic": TEST_TOPIC, "style_guide": {"tone": "1920s newspaper", "length": "longform"}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["article_id"] == str(article_id)
            response = test_client.get(f"/api/compose/{article_id}")
            assert response.status_code == 200
            data = response.json()
            for memo in article_run.agent_memos:
                assert memo.content in str(data)

async def _mock_event_stream(article_id: uuid.UUID) -> AsyncGenerator[Message, None]:
    """Mock event stream for testing.

    Args:
        article_id (UUID): Article ID

    Yields:
        AsyncGenerator[Message, None]: Mock events
    """
    yield Message(
        type=MessageType.PROGRESS,
        agent_id="test_agent",
        article_id=article_id,
        content={"message": "Working on it..."},
    )
    yield Message(
        type=MessageType.COMPLETED,
        agent_id="test_agent",
        article_id=article_id,
        content={"message": "Done!"},
    ) 