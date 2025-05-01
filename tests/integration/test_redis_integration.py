"""Integration tests for Redis functionality."""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator

import pytest
import redis
from fakeredis import FakeRedis

from app.models.agent_memo import AgentMemo
from app.models.article_run import ArticleRun, ArticleRunStatus
from app.models.citation import Citation
from app.models.visual import Visual, VisualType
from app.pubsub.scratchpad import Message, MessageType, agent_scratchpad
from app.storage.redis import RedisStorage
from app.utils.time import calculate_ttl


@pytest.fixture
def redis_client() -> Generator[FakeRedis, None, None]:
    """Create a fake Redis client.

    Yields:
        FakeRedis: Fake Redis client
    """
    client = FakeRedis(decode_responses=True)
    yield client
    client.flushall()


@pytest.fixture
def storage(redis_client: FakeRedis) -> RedisStorage:
    """Create a RedisStorage instance.

    Args:
        redis_client (FakeRedis): Fake Redis client

    Returns:
        RedisStorage: Storage instance
    """
    return RedisStorage(redis_client)


@pytest.fixture
def article_run() -> ArticleRun:
    """Create a test article run.

    Returns:
        ArticleRun: Test article run
    """
    return ArticleRun(
        user_query="Test query",
        status=ArticleRunStatus.PENDING,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def agent_memo(article_run: ArticleRun) -> AgentMemo:
    """Create a test agent memo.

    Args:
        article_run (ArticleRun): Test article run

    Returns:
        AgentMemo: Test agent memo
    """
    return AgentMemo(
        agent_id="test_agent",
        content="Test memo",
        article_id=article_run.id,
        timestamp=datetime.utcnow(),
    )


@pytest.fixture
def citation(article_run: ArticleRun) -> Citation:
    """Create a test citation.

    Args:
        article_run (ArticleRun): Test article run

    Returns:
        Citation: Test citation
    """
    return Citation(
        url="https://example.com",
        title="Test Citation",
        content="Test content",
        article_id=article_run.id,
        publication_date=datetime.utcnow(),
    )


@pytest.fixture
def visual(article_run: ArticleRun) -> Visual:
    """Create a test visual.

    Args:
        article_run (ArticleRun): Test article run

    Returns:
        Visual: Test visual
    """
    return Visual(
        type=VisualType.IMAGE,
        data="data:image/png;base64,test",
        caption="Test caption",
        article_id=article_run.id,
    )


def test_article_run_lifecycle(
    storage: RedisStorage,
    article_run: ArticleRun,
    agent_memo: AgentMemo,
    citation: Citation,
    visual: Visual,
) -> None:
    """Test complete article run lifecycle.

    Args:
        storage (RedisStorage): Storage instance
        article_run (ArticleRun): Test article run
        agent_memo (AgentMemo): Test agent memo
        citation (Citation): Test citation
        visual (Visual): Test visual
    """
    # Save article run
    storage.save_article_run(article_run)

    # Verify retrieval
    retrieved = storage.get_article_run(article_run.id)
    assert retrieved is not None
    assert retrieved.model_dump() == article_run.model_dump()

    # Add memo
    storage.save_agent_memo(agent_memo, article_run.id)

    # Verify memo retrieval
    memos = storage.get_agent_memos(article_run.id)
    assert len(memos) == 1
    assert memos[0].model_dump() == agent_memo.model_dump()

    # Add citation
    storage.save_citation(citation, article_run.id)

    # Verify citation retrieval
    citations = storage.get_citations(article_run.id)
    assert len(citations) == 1
    assert citations[0].model_dump() == citation.model_dump()

    # Update article status
    article_run.status = ArticleRunStatus.COMPLETED
    storage.save_article_run(article_run)

    # Verify updated status
    retrieved = storage.get_article_run(article_run.id)
    assert retrieved is not None
    assert retrieved.status == ArticleRunStatus.COMPLETED


@pytest.mark.asyncio
async def test_agent_communication(
    redis_client: FakeRedis, article_run: ArticleRun
) -> None:
    """Test agent communication using pub/sub.

    Args:
        redis_client (FakeRedis): Fake Redis client
        article_run (ArticleRun): Test article run
    """
    received_messages = []

    def message_callback(message: Message) -> None:
        received_messages.append(message)

    # Subscribe to article channel
    agent_scratchpad.subscribe_to_article(article_run.id, message_callback)

    # Publish test messages
    messages = [
        Message(
            type=MessageType.AGENT_STARTED,
            agent_id="agent1",
            article_id=article_run.id,
            content={"status": "starting"},
        ),
        Message(
            type=MessageType.AGENT_PROGRESS,
            agent_id="agent1",
            article_id=article_run.id,
            content={"progress": 50},
        ),
        Message(
            type=MessageType.AGENT_COMPLETED,
            agent_id="agent1",
            article_id=article_run.id,
            content={"result": "success"},
        ),
    ]

    for msg in messages:
        agent_scratchpad.publish_message(msg)

    # Allow time for message processing
    await asyncio.sleep(0.1)

    # Verify message history
    history = agent_scratchpad.get_message_history(article_run.id)
    assert len(history) == len(messages)
    for sent, received in zip(messages, history):
        assert sent.type == received.type
        assert sent.agent_id == received.agent_id
        assert sent.content == received.content

    # Clean up
    agent_scratchpad.clear_message_history(article_run.id)
    agent_scratchpad.unsubscribe_from_article(article_run.id)


def test_concurrent_article_processing(
    storage: RedisStorage, redis_client: FakeRedis
) -> None:
    """Test concurrent article processing.

    Args:
        storage (RedisStorage): Storage instance
        redis_client (FakeRedis): Fake Redis client
    """
    # Create multiple article runs
    articles = [
        ArticleRun(
            user_query=f"Query {i}",
            status=ArticleRunStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        for i in range(3)
    ]

    # Save all articles
    for article in articles:
        storage.save_article_run(article)

    # Add memos and citations to each article
    for article in articles:
        memo = AgentMemo(
            agent_id="test_agent",
            content=f"Memo for {article.id}",
            article_id=article.id,
            timestamp=datetime.utcnow(),
        )
        citation = Citation(
            url="https://example.com",
            title=f"Citation for {article.id}",
            content="Test content",
            article_id=article.id,
            publication_date=datetime.utcnow(),
        )
        storage.save_agent_memo(memo, article.id)
        storage.save_citation(citation, article.id)

    # Verify each article's data
    for article in articles:
        # Check article
        retrieved = storage.get_article_run(article.id)
        assert retrieved is not None
        assert retrieved.model_dump() == article.model_dump()

        # Check memos
        memos = storage.get_agent_memos(article.id)
        assert len(memos) == 1
        assert memos[0].article_id == article.id

        # Check citations
        citations = storage.get_citations(article.id)
        assert len(citations) == 1
        assert citations[0].article_id == article.id


def test_error_recovery(storage: RedisStorage, redis_client: FakeRedis) -> None:
    """Test error recovery scenarios.

    Args:
        storage (RedisStorage): Storage instance
        redis_client (FakeRedis): Fake Redis client
    """
    article = ArticleRun(
        user_query="Test query",
        status=ArticleRunStatus.IN_PROGRESS,
        created_at=datetime.utcnow(),
    )

    # Test non-existent article
    assert storage.get_article_run(uuid.uuid4()) is None

    # Test recovery from failed state
    storage.save_article_run(article)
    article.status = ArticleRunStatus.FAILED
    article.error_message = "Test error"
    storage.save_article_run(article)

    # Verify failed state
    retrieved = storage.get_article_run(article.id)
    assert retrieved is not None
    assert retrieved.status == ArticleRunStatus.FAILED
    assert retrieved.error_message == "Test error"

    # Test recovery
    article.status = ArticleRunStatus.IN_PROGRESS
    article.error_message = None
    storage.save_article_run(article)

    # Verify recovery
    retrieved = storage.get_article_run(article.id)
    assert retrieved is not None
    assert retrieved.status == ArticleRunStatus.IN_PROGRESS
    assert retrieved.error_message is None


def test_data_persistence(storage: RedisStorage, redis_client: FakeRedis) -> None:
    """Test data persistence with TTL.

    Args:
        storage (RedisStorage): Storage instance
        redis_client (FakeRedis): Fake Redis client
    """
    article = ArticleRun(
        user_query="Test query",
        status=ArticleRunStatus.PENDING,
        created_at=datetime.utcnow(),
    )

    # Save with custom TTL
    ttl = calculate_ttl(base_ttl=timedelta(minutes=5))
    storage.save_article_run(article, ttl=ttl)

    # Verify TTL is set
    key = f"article_run:{article.id}"
    remaining_ttl = redis_client.ttl(key)
    assert remaining_ttl > 0
    assert remaining_ttl <= 300  # 5 minutes in seconds 