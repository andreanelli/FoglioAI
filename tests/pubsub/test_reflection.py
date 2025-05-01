"""Tests for the reflection functionality in the scratchpad."""
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

import pytest

from app.pubsub.scratchpad import (
    AgentScratchpad,
    Message,
    MessageType,
    ReflectionRequest,
    ReflectionStatus,
    ReflectionPriority,
)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("app.pubsub.scratchpad.redis.Redis.from_url") as mock:
        redis_instance = AsyncMock()
        redis_instance.publish = AsyncMock()
        redis_instance.close = AsyncMock()
        mock.return_value = redis_instance
        yield redis_instance


@pytest.fixture
async def scratchpad(mock_redis):
    """Create and connect a scratchpad instance."""
    pad = AgentScratchpad()
    await pad.connect()
    yield pad
    await pad.disconnect()


@pytest.mark.asyncio
async def test_request_reflection(scratchpad):
    """Test requesting a reflection."""
    # Create test data
    article_id = uuid.uuid4()
    memo_id = uuid.uuid4()
    source_agent_id = "editor"
    target_agent_id = "politics_left"
    content = "This memo contains political analysis that needs reflection."
    prompt = "Please evaluate the political bias in this memo."
    
    # Mock the publish_message method
    scratchpad.publish_message = AsyncMock()
    
    # Request reflection
    reflection_id = await scratchpad.request_reflection(
        article_id=article_id,
        memo_id=memo_id,
        source_agent_id=source_agent_id,
        target_agent_id=target_agent_id,
        content=content,
        prompt=prompt,
        priority=ReflectionPriority.HIGH,
    )
    
    # Verify reflection is tracked
    reflection = scratchpad._reflection_tracker.get_reflection(reflection_id)
    assert reflection is not None
    assert reflection.article_id == article_id
    assert reflection.memo_id == memo_id
    assert reflection.source_agent_id == source_agent_id
    assert reflection.target_agent_id == target_agent_id
    assert reflection.content == content
    assert reflection.prompt == prompt
    assert reflection.priority == ReflectionPriority.HIGH
    assert reflection.status == ReflectionStatus.PENDING
    
    # Verify message was published
    scratchpad.publish_message.assert_called_once()
    message = scratchpad.publish_message.call_args[0][0]
    assert message.type == MessageType.REFLECTION_REQUEST
    assert message.agent_id == source_agent_id
    assert message.article_id == article_id
    assert message.reflection_id == reflection_id
    assert message.target_agent_id == target_agent_id
    assert message.content["memo_id"] == str(memo_id)
    assert message.content["content"] == content
    assert message.content["prompt"] == prompt
    assert message.metadata["priority"] == ReflectionPriority.HIGH.value


@pytest.mark.asyncio
async def test_submit_reflection(scratchpad):
    """Test submitting a reflection response."""
    # Create test data
    article_id = uuid.uuid4()
    memo_id = uuid.uuid4()
    source_agent_id = "editor"
    target_agent_id = "politics_left"
    content = "This memo contains political analysis that needs reflection."
    reflection_content = "The memo shows a slight progressive bias in its analysis."
    
    # Mock the publish_message method
    scratchpad.publish_message = AsyncMock()
    
    # Create and add a reflection request
    reflection = ReflectionRequest(
        reflection_id=uuid.uuid4(),
        article_id=article_id,
        memo_id=memo_id,
        source_agent_id=source_agent_id,
        target_agent_id=target_agent_id,
        content=content,
    )
    scratchpad._reflection_tracker.add_reflection(reflection)
    
    # Submit reflection
    await scratchpad.submit_reflection(
        reflection_id=reflection.reflection_id,
        agent_id=target_agent_id,
        content=reflection_content,
        metadata={"bias_score": 0.3},
    )
    
    # Verify reflection status is updated
    updated_reflection = scratchpad._reflection_tracker.get_reflection(reflection.reflection_id)
    assert updated_reflection.status == ReflectionStatus.COMPLETED
    
    # Verify message was published
    scratchpad.publish_message.assert_called_once()
    message = scratchpad.publish_message.call_args[0][0]
    assert message.type == MessageType.REFLECTION_RESPONSE
    assert message.agent_id == target_agent_id
    assert message.article_id == article_id
    assert message.reflection_id == reflection.reflection_id
    assert message.target_agent_id == source_agent_id
    assert message.content["memo_id"] == str(memo_id)
    assert message.content["reflection"] == reflection_content
    assert message.metadata["bias_score"] == 0.3


@pytest.mark.asyncio
async def test_get_pending_reflections(scratchpad):
    """Test getting pending reflections for an agent."""
    # Create test data
    agent_id = "politics_left"
    article_id = uuid.uuid4()
    
    # Create reflection requests with different priorities
    reflections = [
        ReflectionRequest(
            article_id=article_id,
            memo_id=uuid.uuid4(),
            source_agent_id="editor",
            target_agent_id=agent_id,
            content="Content 1",
            priority=ReflectionPriority.MEDIUM,
        ),
        ReflectionRequest(
            article_id=article_id,
            memo_id=uuid.uuid4(),
            source_agent_id="editor",
            target_agent_id=agent_id,
            content="Content 2",
            priority=ReflectionPriority.HIGH,
        ),
        ReflectionRequest(
            article_id=article_id,
            memo_id=uuid.uuid4(),
            source_agent_id="editor",
            target_agent_id=agent_id,
            content="Content 3",
            priority=ReflectionPriority.LOW,
        ),
    ]
    
    # Add reflections to tracker
    for reflection in reflections:
        scratchpad._reflection_tracker.add_reflection(reflection)
    
    # Get pending reflections
    pending = await scratchpad.get_pending_reflections(agent_id)
    
    # Verify reflections are returned in order of priority
    assert len(pending) == 3
    assert pending[0].priority == ReflectionPriority.HIGH
    assert pending[1].priority == ReflectionPriority.MEDIUM
    assert pending[2].priority == ReflectionPriority.LOW


@pytest.mark.asyncio
async def test_reflection_status_updates(scratchpad):
    """Test updating reflection statuses."""
    # Create test data
    article_id = uuid.uuid4()
    agent_id = "politics_left"
    
    # Create reflection request
    reflection = ReflectionRequest(
        article_id=article_id,
        memo_id=uuid.uuid4(),
        source_agent_id="editor",
        target_agent_id=agent_id,
        content="Content",
    )
    
    # Add reflection to tracker
    scratchpad._reflection_tracker.add_reflection(reflection)
    
    # Mark as in-progress
    await scratchpad.mark_reflection_in_progress(reflection.reflection_id)
    assert scratchpad._reflection_tracker.get_reflection(reflection.reflection_id).status == ReflectionStatus.IN_PROGRESS
    
    # Mock the publish_message method
    scratchpad.publish_message = AsyncMock()
    
    # Mark as skipped
    await scratchpad.mark_reflection_skipped(reflection.reflection_id, "Agent is busy")
    assert scratchpad._reflection_tracker.get_reflection(reflection.reflection_id).status == ReflectionStatus.SKIPPED
    
    # Verify error message was published
    scratchpad.publish_message.assert_called_once()
    message = scratchpad.publish_message.call_args[0][0]
    assert message.type == MessageType.REFLECTION_ERROR
    assert message.agent_id == agent_id
    assert message.content["reason"] == "Agent is busy"


@pytest.mark.asyncio
async def test_get_reflection_stats(scratchpad):
    """Test getting reflection statistics."""
    # Create test data
    article_id = uuid.uuid4()
    other_article_id = uuid.uuid4()
    
    # Create reflection requests with different statuses
    reflections = [
        ReflectionRequest(
            article_id=article_id,
            memo_id=uuid.uuid4(),
            source_agent_id="editor",
            target_agent_id="politics_left",
            content="Content 1",
            status=ReflectionStatus.PENDING,
        ),
        ReflectionRequest(
            article_id=article_id,
            memo_id=uuid.uuid4(),
            source_agent_id="editor",
            target_agent_id="politics_right",
            content="Content 2",
            status=ReflectionStatus.IN_PROGRESS,
        ),
        ReflectionRequest(
            article_id=article_id,
            memo_id=uuid.uuid4(),
            source_agent_id="editor",
            target_agent_id="historian",
            content="Content 3",
            status=ReflectionStatus.COMPLETED,
        ),
        ReflectionRequest(
            article_id=article_id,
            memo_id=uuid.uuid4(),
            source_agent_id="editor",
            target_agent_id="geopolitics",
            content="Content 4",
            status=ReflectionStatus.FAILED,
        ),
        ReflectionRequest(
            article_id=article_id,
            memo_id=uuid.uuid4(),
            source_agent_id="editor",
            target_agent_id="editor",
            content="Content 5",
            status=ReflectionStatus.SKIPPED,
        ),
        # Add a reflection for a different article
        ReflectionRequest(
            article_id=other_article_id,
            memo_id=uuid.uuid4(),
            source_agent_id="editor",
            target_agent_id="politics_left",
            content="Content 6",
            status=ReflectionStatus.PENDING,
        ),
    ]
    
    # Add reflections to tracker
    for reflection in reflections:
        scratchpad._reflection_tracker.add_reflection(reflection)
    
    # Get stats
    stats = await scratchpad.get_reflection_stats(article_id)
    
    # Verify stats
    assert stats["total"] == 5
    assert stats["pending"] == 1
    assert stats["in_progress"] == 1
    assert stats["completed"] == 1
    assert stats["failed"] == 1
    assert stats["skipped"] == 1
    
    # Verify stats for the other article
    other_stats = await scratchpad.get_reflection_stats(other_article_id)
    assert other_stats["total"] == 1
    assert other_stats["pending"] == 1


@pytest.mark.asyncio
async def test_publish_message_with_reflection(scratchpad, mock_redis):
    """Test publishing a message with reflection information."""
    # Create test data
    article_id = uuid.uuid4()
    reflection_id = uuid.uuid4()
    agent_id = "politics_left"
    target_agent_id = "editor"
    
    # Add subscribers
    article_callback = MagicMock()
    reflection_callback = MagicMock()
    scratchpad.subscribe_to_article(article_id, article_callback, "article_sub")
    scratchpad.subscribe_to_reflection(reflection_id, reflection_callback, "reflection_sub")
    
    # Create and publish a message
    message = Message(
        type=MessageType.REFLECTION_RESPONSE,
        agent_id=agent_id,
        article_id=article_id,
        reflection_id=reflection_id,
        target_agent_id=target_agent_id,
        content={
            "memo_id": str(uuid.uuid4()),
            "reflection": "This is a reflection response.",
        },
    )
    
    await scratchpad.publish_message(message)
    
    # Verify both callbacks were called
    article_callback.assert_called_once_with(message)
    reflection_callback.assert_called_once_with(message)
    
    # Verify publish to Redis was called twice (once for article, once for reflection)
    assert mock_redis.publish.call_count == 2
    # First call should be to the article channel
    assert mock_redis.publish.call_args_list[0][0][0] == f"article:{article_id}"
    # Second call should be to the reflection channel
    assert mock_redis.publish.call_args_list[1][0][0] == f"reflection:{reflection_id}"


@pytest.mark.asyncio
async def test_subscribe_unsubscribe_reflection(scratchpad):
    """Test subscribing and unsubscribing from reflection events."""
    # Create test data
    reflection_id = uuid.uuid4()
    callback = MagicMock()
    
    # Subscribe
    scratchpad.subscribe_to_reflection(reflection_id, callback, "sub_id")
    assert reflection_id in scratchpad._reflection_callbacks
    assert "sub_id" in scratchpad._reflection_callbacks[reflection_id]
    
    # Unsubscribe with ID
    scratchpad.unsubscribe_from_reflection(reflection_id, "sub_id")
    assert reflection_id in scratchpad._reflection_callbacks
    assert "sub_id" not in scratchpad._reflection_callbacks[reflection_id]
    
    # Subscribe again
    scratchpad.subscribe_to_reflection(reflection_id, callback, "sub_id")
    
    # Unsubscribe without ID
    scratchpad.unsubscribe_from_reflection(reflection_id)
    assert reflection_id not in scratchpad._reflection_callbacks 