"""Tests for agent scratchpad module."""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from redis import Redis

from app.pubsub.scratchpad import AgentScratchpad, Message, MessageType


@pytest.fixture
def article_id() -> uuid.UUID:
    """Get a test article ID.

    Returns:
        uuid.UUID: Test article ID
    """
    return uuid.uuid4()


@pytest.fixture
def test_message(article_id: uuid.UUID) -> Message:
    """Get a test message.

    Args:
        article_id (uuid.UUID): Article ID

    Returns:
        Message: Test message
    """
    return Message(
        type=MessageType.AGENT_PROGRESS,
        agent_id="test_agent",
        article_id=article_id,
        content={"progress": 50},
    )


@pytest.fixture
def redis_mock() -> MagicMock:
    """Get a mock Redis client.

    Returns:
        MagicMock: Mock Redis client
    """
    mock = MagicMock(spec=Redis)
    mock.pubsub.return_value = MagicMock()
    return mock


@pytest.fixture
def scratchpad(redis_mock: MagicMock) -> AgentScratchpad:
    """Get a test scratchpad instance.

    Args:
        redis_mock (MagicMock): Mock Redis client

    Returns:
        AgentScratchpad: Test scratchpad instance
    """
    return AgentScratchpad(redis_mock)


def test_publish_message(
    scratchpad: AgentScratchpad, test_message: Message, article_id: uuid.UUID
) -> None:
    """Test message publishing.

    Args:
        scratchpad (AgentScratchpad): Test scratchpad instance
        test_message (Message): Test message
        article_id (uuid.UUID): Article ID
    """
    scratchpad.publish_message(test_message)

    # Check that message was stored in history
    history_key = f"article:messages:{article_id}"
    message_json = test_message.model_dump_json()
    scratchpad.redis.rpush.assert_called_once_with(history_key, message_json)

    # Check that message was published
    channel = f"article:{article_id}"
    scratchpad.redis.publish.assert_called_once_with(channel, message_json)


def test_subscribe_to_article(
    scratchpad: AgentScratchpad, article_id: uuid.UUID
) -> None:
    """Test article subscription.

    Args:
        scratchpad (AgentScratchpad): Test scratchpad instance
        article_id (uuid.UUID): Article ID
    """
    callback = MagicMock()
    scratchpad.subscribe_to_article(article_id, callback)

    channel = f"article:{article_id}"
    scratchpad.pubsub.subscribe.assert_called_once()
    assert channel in scratchpad.pubsub.subscribe.call_args[1]


def test_handle_message(
    scratchpad: AgentScratchpad, test_message: Message
) -> None:
    """Test message handling.

    Args:
        scratchpad (AgentScratchpad): Test scratchpad instance
        test_message (Message): Test message
    """
    callback = MagicMock()
    raw_message = {
        "type": "message",
        "data": test_message.model_dump_json(),
    }

    scratchpad._handle_message(raw_message, callback)
    callback.assert_called_once()
    actual_message = callback.call_args[0][0]
    assert isinstance(actual_message, Message)
    assert actual_message.model_dump() == test_message.model_dump()


def test_handle_message_error(scratchpad: AgentScratchpad) -> None:
    """Test message handling error.

    Args:
        scratchpad (AgentScratchpad): Test scratchpad instance
    """
    callback = MagicMock()
    raw_message = {
        "type": "message",
        "data": "invalid json",
    }

    scratchpad._handle_message(raw_message, callback)
    callback.assert_not_called()


def test_get_message_history(
    scratchpad: AgentScratchpad,
    test_message: Message,
    article_id: uuid.UUID,
) -> None:
    """Test message history retrieval.

    Args:
        scratchpad (AgentScratchpad): Test scratchpad instance
        test_message (Message): Test message
        article_id (uuid.UUID): Article ID
    """
    message_json = test_message.model_dump_json()
    scratchpad.redis.lrange.return_value = [message_json]

    messages = scratchpad.get_message_history(article_id)
    assert len(messages) == 1
    assert messages[0].model_dump() == test_message.model_dump()

    history_key = f"article:messages:{article_id}"
    scratchpad.redis.lrange.assert_called_once_with(history_key, 0, -1)


def test_clear_message_history(
    scratchpad: AgentScratchpad, article_id: uuid.UUID
) -> None:
    """Test message history clearing.

    Args:
        scratchpad (AgentScratchpad): Test scratchpad instance
        article_id (uuid.UUID): Article ID
    """
    scratchpad.clear_message_history(article_id)

    history_key = f"article:messages:{article_id}"
    scratchpad.redis.delete.assert_called_once_with(history_key)


def test_unsubscribe_from_article(
    scratchpad: AgentScratchpad, article_id: uuid.UUID
) -> None:
    """Test article unsubscription.

    Args:
        scratchpad (AgentScratchpad): Test scratchpad instance
        article_id (uuid.UUID): Article ID
    """
    scratchpad.unsubscribe_from_article(article_id)

    channel = f"article:{article_id}"
    scratchpad.pubsub.unsubscribe.assert_called_once_with(channel)


def test_close(scratchpad: AgentScratchpad) -> None:
    """Test scratchpad closure.

    Args:
        scratchpad (AgentScratchpad): Test scratchpad instance
    """
    scratchpad.close()
    scratchpad.pubsub.close.assert_called_once() 