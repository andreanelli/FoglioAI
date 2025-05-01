"""Tests for Redis storage implementation."""
import uuid
from datetime import datetime, timedelta
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
import redis
from fakeredis import FakeRedis

from app.models.agent_memo import AgentMemo
from app.models.article_run import ArticleRun, ArticleRunStatus
from app.models.citation import Citation
from app.models.visual import Visual, VisualType
from app.storage.redis import RedisStorage, StorageError


@pytest.fixture
def redis_client() -> Generator[FakeRedis, None, None]:
    """Create a fake Redis client.

    Yields:
        FakeRedis: Fake Redis client
    """
    client = FakeRedis()
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
def sample_article_run() -> ArticleRun:
    """Create a sample article run.

    Returns:
        ArticleRun: Sample article run
    """
    return ArticleRun(
        user_query="Test query",
        final_output="Test output",
        status=ArticleRunStatus.COMPLETED,
    )


@pytest.fixture
def sample_agent_memo() -> AgentMemo:
    """Create a sample agent memo.

    Returns:
        AgentMemo: Sample agent memo
    """
    return AgentMemo(
        agent_name="TestAgent",
        agent_role="TestRole",
        content="Test content",
    )


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


def test_save_and_get_article_run(
    storage: RedisStorage, sample_article_run: ArticleRun
) -> None:
    """Test saving and retrieving an article run.

    Args:
        storage (RedisStorage): Storage instance
        sample_article_run (ArticleRun): Sample article run
    """
    storage.save_article_run(sample_article_run)
    retrieved = storage.get_article_run(sample_article_run.id)
    assert retrieved is not None
    assert retrieved.id == sample_article_run.id
    assert retrieved.user_query == sample_article_run.user_query
    assert retrieved.final_output == sample_article_run.final_output
    assert retrieved.status == sample_article_run.status


def test_save_and_get_agent_memo(
    storage: RedisStorage, sample_agent_memo: AgentMemo
) -> None:
    """Test saving and retrieving an agent memo.

    Args:
        storage (RedisStorage): Storage instance
        sample_agent_memo (AgentMemo): Sample agent memo
    """
    article_id = uuid.uuid4()
    storage.save_agent_memo(sample_agent_memo, article_id)
    memos = storage.get_agent_memos(article_id)
    assert len(memos) == 1
    assert memos[0].id == sample_agent_memo.id
    assert memos[0].agent_name == sample_agent_memo.agent_name
    assert memos[0].content == sample_agent_memo.content


def test_save_and_get_citation(
    storage: RedisStorage, sample_citation: Citation
) -> None:
    """Test saving and retrieving a citation.

    Args:
        storage (RedisStorage): Storage instance
        sample_citation (Citation): Sample citation
    """
    article_id = uuid.uuid4()
    storage.save_citation(sample_citation, article_id)
    citations = storage.get_citations(article_id)
    assert len(citations) == 1
    assert citations[0].id == sample_citation.id
    assert citations[0].url == sample_citation.url
    assert citations[0].title == sample_citation.title


def test_save_and_get_visual(storage: RedisStorage, sample_visual: Visual) -> None:
    """Test saving and retrieving a visual.

    Args:
        storage (RedisStorage): Storage instance
        sample_visual (Visual): Sample visual
    """
    article_id = uuid.uuid4()
    storage.save_visual(sample_visual, article_id)
    visuals = storage.get_visuals(article_id)
    assert len(visuals) == 1
    assert visuals[0].id == sample_visual.id
    assert visuals[0].type == sample_visual.type
    assert visuals[0].caption == sample_visual.caption


def test_delete_article_run(
    storage: RedisStorage,
    sample_article_run: ArticleRun,
    sample_agent_memo: AgentMemo,
    sample_citation: Citation,
    sample_visual: Visual,
) -> None:
    """Test deleting an article run and all associated data.

    Args:
        storage (RedisStorage): Storage instance
        sample_article_run (ArticleRun): Sample article run
        sample_agent_memo (AgentMemo): Sample agent memo
        sample_citation (Citation): Sample citation
        sample_visual (Visual): Sample visual
    """
    # Save all data
    storage.save_article_run(sample_article_run)
    storage.save_agent_memo(sample_agent_memo, sample_article_run.id)
    storage.save_citation(sample_citation, sample_article_run.id)
    storage.save_visual(sample_visual, sample_article_run.id)

    # Verify data is saved
    assert storage.get_article_run(sample_article_run.id) is not None
    assert len(storage.get_agent_memos(sample_article_run.id)) == 1
    assert len(storage.get_citations(sample_article_run.id)) == 1
    assert len(storage.get_visuals(sample_article_run.id)) == 1

    # Delete article run
    storage.delete_article_run(sample_article_run.id)

    # Verify all data is deleted
    assert storage.get_article_run(sample_article_run.id) is None
    assert len(storage.get_agent_memos(sample_article_run.id)) == 0
    assert len(storage.get_citations(sample_article_run.id)) == 0
    assert len(storage.get_visuals(sample_article_run.id)) == 0


def test_ttl_expiration(
    storage: RedisStorage, sample_article_run: ArticleRun, redis_client: FakeRedis
) -> None:
    """Test TTL expiration for stored data.

    Args:
        storage (RedisStorage): Storage instance
        sample_article_run (ArticleRun): Sample article run
        redis_client (FakeRedis): Fake Redis client
    """
    ttl = timedelta(seconds=1)
    storage.save_article_run(sample_article_run, ttl=ttl)

    key = f"article_run:{sample_article_run.id}"
    assert redis_client.ttl(key) > 0

    # FakeRedis doesn't support real-time TTL expiration,
    # so we just verify the TTL is set correctly


def test_compression(storage: RedisStorage, sample_article_run: ArticleRun) -> None:
    """Test data compression.

    Args:
        storage (RedisStorage): Storage instance
        sample_article_run (ArticleRun): Sample article run
    """
    # Add some large content to test compression
    sample_article_run.final_output = "x" * 1000

    storage.save_article_run(sample_article_run)
    retrieved = storage.get_article_run(sample_article_run.id)
    assert retrieved is not None
    assert retrieved.final_output == sample_article_run.final_output


def test_redis_error_handling(storage: RedisStorage) -> None:
    """Test error handling for Redis operations.

    Args:
        storage (RedisStorage): Storage instance
    """
    with patch.object(storage.redis, "get", side_effect=redis.RedisError):
        with pytest.raises(StorageError):
            storage.get_article_run(uuid.uuid4())

    with patch.object(storage.redis, "setex", side_effect=redis.RedisError):
        with pytest.raises(StorageError):
            storage.save_article_run(ArticleRun(user_query="Test"))


def test_get_nonexistent_data(storage: RedisStorage) -> None:
    """Test retrieving non-existent data.

    Args:
        storage (RedisStorage): Storage instance
    """
    article_id = uuid.uuid4()
    assert storage.get_article_run(article_id) is None
    assert storage.get_agent_memos(article_id) == []
    assert storage.get_citations(article_id) == []
    assert storage.get_visuals(article_id) == []


def test_sorting(
    storage: RedisStorage,
    sample_article_run: ArticleRun,
    sample_agent_memo: AgentMemo,
    sample_citation: Citation,
    sample_visual: Visual,
) -> None:
    """Test sorting of retrieved data.

    Args:
        storage (RedisStorage): Storage instance
        sample_article_run (ArticleRun): Sample article run
        sample_agent_memo (AgentMemo): Sample agent memo
        sample_citation (Citation): Sample citation
        sample_visual (Visual): Sample visual
    """
    # Create additional items with different timestamps
    memo2 = AgentMemo(
        agent_name="TestAgent2",
        agent_role="TestRole2",
        content="Test content 2",
        timestamp=datetime.utcnow() + timedelta(hours=1),
    )

    citation2 = Citation(
        url="https://example.com/article2",
        title="Test Article 2",
        author="Jane Doe",
        publication_date=datetime.utcnow() + timedelta(days=1),
        excerpt="Test excerpt 2",
    )

    visual2 = Visual(
        type=VisualType.CHART,
        source_data={"data": [1, 2, 3]},
        generated_content="base64_encoded_data_2",
        caption="Test caption 2",
        alt_text="Test alt text 2",
        created_at=datetime.utcnow() + timedelta(minutes=30),
    )

    # Save all items
    storage.save_agent_memo(sample_agent_memo, sample_article_run.id)
    storage.save_agent_memo(memo2, sample_article_run.id)
    storage.save_citation(sample_citation, sample_article_run.id)
    storage.save_citation(citation2, sample_article_run.id)
    storage.save_visual(sample_visual, sample_article_run.id)
    storage.save_visual(visual2, sample_article_run.id)

    # Verify sorting
    memos = storage.get_agent_memos(sample_article_run.id)
    assert len(memos) == 2
    assert memos[0].timestamp <= memos[1].timestamp

    citations = storage.get_citations(sample_article_run.id)
    assert len(citations) == 2
    assert citations[0].publication_date <= citations[1].publication_date

    visuals = storage.get_visuals(sample_article_run.id)
    assert len(visuals) == 2
    assert visuals[0].created_at <= visuals[1].created_at 