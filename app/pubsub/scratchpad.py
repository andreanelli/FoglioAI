"""Scratchpad module for agent communication."""
import enum
import json
import logging
from typing import Any, Callable, Dict, Optional
from uuid import UUID

import redis.asyncio as redis
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class MessageType(str, enum.Enum):
    """Message type enum."""

    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    ERROR = "error"


class Message(BaseModel):
    """Message model."""

    type: MessageType
    agent_id: str
    article_id: UUID
    content: Dict[str, str]


class AgentScratchpad:
    """Agent scratchpad for communication."""

    def __init__(self) -> None:
        """Initialize the scratchpad."""
        self._redis: Optional[redis.Redis] = None
        self._subscribers: Dict[UUID, Dict[str, Callable[[Message], None]]] = {}

    async def connect(self) -> None:
        """Connect to Redis."""
        if not self._redis:
            self._redis = redis.Redis.from_url(settings.redis_url)

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def subscribe_to_article(
        self,
        article_id: UUID,
        callback: Callable[[Message], None],
        subscriber_id: Optional[str] = None,
    ) -> None:
        """Subscribe to article events.

        Args:
            article_id (UUID): ID of the article
            callback (Callable[[Message], None]): Callback function
            subscriber_id (Optional[str], optional): Subscriber ID. Defaults to None.
        """
        if article_id not in self._subscribers:
            self._subscribers[article_id] = {}

        # Use subscriber_id or generate one
        sub_id = subscriber_id or str(UUID())
        self._subscribers[article_id][sub_id] = callback

    def unsubscribe_from_article(
        self,
        article_id: UUID,
        subscriber_id: Optional[str] = None,
    ) -> None:
        """Unsubscribe from article events.

        Args:
            article_id (UUID): ID of the article
            subscriber_id (Optional[str], optional): Subscriber ID. Defaults to None.
        """
        if article_id in self._subscribers:
            if subscriber_id:
                self._subscribers[article_id].pop(subscriber_id, None)
            else:
                self._subscribers.pop(article_id, None)

    def publish_message(self, message: Message) -> None:
        """Publish a message.

        Args:
            message (Message): Message to publish
        """
        # Notify subscribers
        if message.article_id in self._subscribers:
            for callback in self._subscribers[message.article_id].values():
                try:
                    callback(message)
                except Exception as e:
                    logger.error("Error in subscriber callback: %s", e)

        # Publish to Redis
        if self._redis:
            try:
                channel = f"article:{message.article_id}"
                asyncio.create_task(
                    self._redis.publish(channel, message.model_dump_json())
                )
            except Exception as e:
                logger.error("Error publishing to Redis: %s", e)


# Global scratchpad instance
agent_scratchpad = AgentScratchpad() 