"""Scratchpad module for agent communication."""
import enum
import json
import logging
import uuid
import asyncio
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import UUID

import redis.asyncio as redis
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


class MessageType(str, enum.Enum):
    """Message type enum."""

    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    ERROR = "error"
    # New message types for reflection system
    REFLECTION_REQUEST = "reflection_request"
    REFLECTION_RESPONSE = "reflection_response"
    REFLECTION_COMPLETED = "reflection_completed"
    REFLECTION_ERROR = "reflection_error"
    REFLECTION_SUMMARY = "reflection_summary"
    EDITOR_FEEDBACK = "editor_feedback"
    BIAS_ALERT = "bias_alert"


class ReflectionStatus(str, enum.Enum):
    """Reflection status enum."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ReflectionPriority(int, enum.Enum):
    """Reflection priority enum."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Message(BaseModel):
    """Message model."""

    type: MessageType
    agent_id: str
    article_id: UUID
    content: Dict[str, Any]
    # New fields for reflection system
    reflection_id: Optional[UUID] = None
    target_agent_id: Optional[str] = None
    timestamp: float = Field(default_factory=lambda: asyncio.get_event_loop().time())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReflectionRequest(BaseModel):
    """Reflection request model."""

    reflection_id: UUID = Field(default_factory=uuid.uuid4)
    article_id: UUID
    memo_id: UUID
    source_agent_id: str
    target_agent_id: str
    content: str
    prompt: Optional[str] = None
    priority: ReflectionPriority = ReflectionPriority.MEDIUM
    deadline: Optional[float] = None
    status: ReflectionStatus = ReflectionStatus.PENDING
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReflectionTracker:
    """Tracks reflection requests and their statuses."""

    def __init__(self):
        """Initialize the reflection tracker."""
        self.reflections: Dict[UUID, ReflectionRequest] = {}
        self.agent_queue: Dict[str, Set[UUID]] = {}
        self.completed: Set[UUID] = set()
        self.failed: Set[UUID] = set()

    def add_reflection(self, reflection: ReflectionRequest) -> None:
        """Add a reflection request to the tracker.
        
        Args:
            reflection (ReflectionRequest): The reflection request to add
        """
        self.reflections[reflection.reflection_id] = reflection
        if reflection.target_agent_id not in self.agent_queue:
            self.agent_queue[reflection.target_agent_id] = set()
        self.agent_queue[reflection.target_agent_id].add(reflection.reflection_id)

    def get_reflection(self, reflection_id: UUID) -> Optional[ReflectionRequest]:
        """Get a reflection request by ID.
        
        Args:
            reflection_id (UUID): ID of the reflection request
            
        Returns:
            Optional[ReflectionRequest]: The reflection request if found
        """
        return self.reflections.get(reflection_id)

    def update_status(
        self, reflection_id: UUID, status: ReflectionStatus
    ) -> Optional[ReflectionRequest]:
        """Update the status of a reflection request.
        
        Args:
            reflection_id (UUID): ID of the reflection request
            status (ReflectionStatus): New status
            
        Returns:
            Optional[ReflectionRequest]: Updated reflection request if found
        """
        reflection = self.reflections.get(reflection_id)
        if reflection:
            reflection.status = status
            if status == ReflectionStatus.COMPLETED:
                self.completed.add(reflection_id)
                if reflection.target_agent_id in self.agent_queue:
                    self.agent_queue[reflection.target_agent_id].discard(reflection_id)
            elif status == ReflectionStatus.FAILED:
                self.failed.add(reflection_id)
                if reflection.target_agent_id in self.agent_queue:
                    self.agent_queue[reflection.target_agent_id].discard(reflection_id)
            return reflection
        return None

    def get_agent_queue(self, agent_id: str) -> List[ReflectionRequest]:
        """Get all pending reflection requests for an agent, ordered by priority.
        
        Args:
            agent_id (str): ID of the agent
            
        Returns:
            List[ReflectionRequest]: List of reflection requests ordered by priority
        """
        if agent_id not in self.agent_queue:
            return []
        
        requests = [
            self.reflections[reflection_id]
            for reflection_id in self.agent_queue[agent_id]
            if self.reflections[reflection_id].status == ReflectionStatus.PENDING
        ]
        
        # Sort by priority (high to low) and then by deadline if available
        return sorted(
            requests,
            key=lambda r: (
                -r.priority.value,
                r.deadline or float("inf")
            )
        )

    def get_reflection_stats(self, article_id: UUID) -> Dict[str, int]:
        """Get reflection statistics for an article.
        
        Args:
            article_id (UUID): ID of the article
            
        Returns:
            Dict[str, int]: Dictionary with reflection statistics
        """
        article_reflections = [
            r for r in self.reflections.values() if r.article_id == article_id
        ]
        
        return {
            "total": len(article_reflections),
            "pending": sum(1 for r in article_reflections if r.status == ReflectionStatus.PENDING),
            "in_progress": sum(1 for r in article_reflections if r.status == ReflectionStatus.IN_PROGRESS),
            "completed": sum(1 for r in article_reflections if r.status == ReflectionStatus.COMPLETED),
            "failed": sum(1 for r in article_reflections if r.status == ReflectionStatus.FAILED),
            "skipped": sum(1 for r in article_reflections if r.status == ReflectionStatus.SKIPPED),
        }


class AgentScratchpad:
    """Agent scratchpad for communication."""

    def __init__(self) -> None:
        """Initialize the scratchpad."""
        self._redis: Optional[redis.Redis] = None
        self._subscribers: Dict[UUID, Dict[str, Callable[[Message], None]]] = {}
        self._reflection_tracker = ReflectionTracker()
        self._reflection_callbacks: Dict[UUID, Dict[str, Callable[[Message], None]]] = {}

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
        sub_id = subscriber_id or str(uuid.uuid4())
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

    def subscribe_to_reflection(
        self,
        reflection_id: UUID,
        callback: Callable[[Message], None],
        subscriber_id: Optional[str] = None,
    ) -> None:
        """Subscribe to reflection events.

        Args:
            reflection_id (UUID): ID of the reflection
            callback (Callable[[Message], None]): Callback function
            subscriber_id (Optional[str], optional): Subscriber ID. Defaults to None.
        """
        if reflection_id not in self._reflection_callbacks:
            self._reflection_callbacks[reflection_id] = {}

        # Use subscriber_id or generate one
        sub_id = subscriber_id or str(uuid.uuid4())
        self._reflection_callbacks[reflection_id][sub_id] = callback

    def unsubscribe_from_reflection(
        self,
        reflection_id: UUID,
        subscriber_id: Optional[str] = None,
    ) -> None:
        """Unsubscribe from reflection events.

        Args:
            reflection_id (UUID): ID of the reflection
            subscriber_id (Optional[str], optional): Subscriber ID. Defaults to None.
        """
        if reflection_id in self._reflection_callbacks:
            if subscriber_id:
                self._reflection_callbacks[reflection_id].pop(subscriber_id, None)
            else:
                self._reflection_callbacks.pop(reflection_id, None)

    async def publish_message(self, message: Message) -> None:
        """Publish a message.

        Args:
            message (Message): Message to publish
        """
        # Notify article subscribers
        if message.article_id in self._subscribers:
            for callback in self._subscribers[message.article_id].values():
                try:
                    callback(message)
                except Exception as e:
                    logger.error("Error in article subscriber callback: %s", e)

        # Notify reflection subscribers if this is a reflection-related message
        if message.reflection_id and message.reflection_id in self._reflection_callbacks:
            for callback in self._reflection_callbacks[message.reflection_id].values():
                try:
                    callback(message)
                except Exception as e:
                    logger.error("Error in reflection subscriber callback: %s", e)

            # Update reflection status if needed
            if message.type == MessageType.REFLECTION_RESPONSE:
                self._reflection_tracker.update_status(
                    message.reflection_id, ReflectionStatus.COMPLETED
                )
            elif message.type == MessageType.REFLECTION_ERROR:
                self._reflection_tracker.update_status(
                    message.reflection_id, ReflectionStatus.FAILED
                )

        # Publish to Redis
        if self._redis:
            try:
                channel = f"article:{message.article_id}"
                asyncio.create_task(
                    self._redis.publish(channel, message.model_dump_json())
                )
                
                # If this is a reflection-related message, also publish to the reflection channel
                if message.reflection_id:
                    reflection_channel = f"reflection:{message.reflection_id}"
                    asyncio.create_task(
                        self._redis.publish(reflection_channel, message.model_dump_json())
                    )
            except Exception as e:
                logger.error("Error publishing to Redis: %s", e)

    async def request_reflection(
        self,
        article_id: UUID,
        memo_id: UUID,
        source_agent_id: str,
        target_agent_id: str,
        content: str,
        prompt: Optional[str] = None,
        priority: ReflectionPriority = ReflectionPriority.MEDIUM,
        deadline: Optional[float] = None,
    ) -> UUID:
        """Request a reflection from another agent.

        Args:
            article_id (UUID): ID of the article
            memo_id (UUID): ID of the memo to reflect on
            source_agent_id (str): ID of the requesting agent
            target_agent_id (str): ID of the agent to provide reflection
            content (str): Content to reflect on
            prompt (Optional[str], optional): Specific reflection prompt. Defaults to None.
            priority (ReflectionPriority, optional): Priority level. Defaults to MEDIUM.
            deadline (Optional[float], optional): Deadline timestamp. Defaults to None.

        Returns:
            UUID: ID of the reflection request
        """
        # Create reflection request
        reflection = ReflectionRequest(
            article_id=article_id,
            memo_id=memo_id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            content=content,
            prompt=prompt,
            priority=priority,
            deadline=deadline,
        )
        
        # Add to tracker
        self._reflection_tracker.add_reflection(reflection)
        
        # Create and publish reflection request message
        message = Message(
            type=MessageType.REFLECTION_REQUEST,
            agent_id=source_agent_id,
            article_id=article_id,
            reflection_id=reflection.reflection_id,
            target_agent_id=target_agent_id,
            content={
                "memo_id": str(memo_id),
                "content": content,
                "prompt": prompt or "Please provide your perspective on this memo.",
            },
            metadata={
                "priority": priority.value,
                "deadline": deadline,
            },
        )
        
        await self.publish_message(message)
        
        return reflection.reflection_id

    async def submit_reflection(
        self,
        reflection_id: UUID,
        agent_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Submit a reflection response.

        Args:
            reflection_id (UUID): ID of the reflection request
            agent_id (str): ID of the responding agent
            content (str): Reflection content
            metadata (Optional[Dict[str, Any]], optional): Additional metadata. Defaults to None.
        """
        reflection = self._reflection_tracker.get_reflection(reflection_id)
        if not reflection:
            logger.error(f"Reflection {reflection_id} not found")
            return
        
        # Update reflection status
        self._reflection_tracker.update_status(reflection_id, ReflectionStatus.COMPLETED)
        
        # Create and publish reflection response message
        message = Message(
            type=MessageType.REFLECTION_RESPONSE,
            agent_id=agent_id,
            article_id=reflection.article_id,
            reflection_id=reflection_id,
            target_agent_id=reflection.source_agent_id,
            content={
                "memo_id": str(reflection.memo_id),
                "reflection": content,
            },
            metadata=metadata or {},
        )
        
        await self.publish_message(message)

    async def get_pending_reflections(self, agent_id: str) -> List[ReflectionRequest]:
        """Get pending reflection requests for an agent.

        Args:
            agent_id (str): ID of the agent

        Returns:
            List[ReflectionRequest]: List of pending reflection requests
        """
        return self._reflection_tracker.get_agent_queue(agent_id)

    async def get_reflection_stats(self, article_id: UUID) -> Dict[str, int]:
        """Get reflection statistics for an article.

        Args:
            article_id (UUID): ID of the article

        Returns:
            Dict[str, int]: Dictionary with reflection statistics
        """
        return self._reflection_tracker.get_reflection_stats(article_id)
    
    async def mark_reflection_in_progress(self, reflection_id: UUID) -> None:
        """Mark a reflection as in-progress.

        Args:
            reflection_id (UUID): ID of the reflection
        """
        self._reflection_tracker.update_status(reflection_id, ReflectionStatus.IN_PROGRESS)
    
    async def mark_reflection_skipped(self, reflection_id: UUID, reason: str) -> None:
        """Mark a reflection as skipped.

        Args:
            reflection_id (UUID): ID of the reflection
            reason (str): Reason for skipping
        """
        reflection = self._reflection_tracker.update_status(reflection_id, ReflectionStatus.SKIPPED)
        if reflection:
            # Publish skip notification
            message = Message(
                type=MessageType.REFLECTION_ERROR,
                agent_id=reflection.target_agent_id,
                article_id=reflection.article_id,
                reflection_id=reflection_id,
                target_agent_id=reflection.source_agent_id,
                content={
                    "memo_id": str(reflection.memo_id),
                    "error": "Reflection skipped",
                    "reason": reason,
                },
            )
            await self.publish_message(message)


# Global scratchpad instance
agent_scratchpad = AgentScratchpad() 