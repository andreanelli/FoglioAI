"""Base agent class for FoglioAI."""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

from crewai import Agent
from pydantic import BaseModel

from app.models.agent import AgentRole
from app.pubsub.scratchpad import (
    Message, 
    MessageType, 
    ReflectionPriority, 
    ReflectionRequest,
    ReflectionStatus,
    agent_scratchpad,
)
from app.redis_client import redis_client

logger = logging.getLogger(__name__)


class AgentConfig(BaseModel):
    """Configuration for a FoglioAI agent."""

    role: AgentRole
    name: str
    goal: str
    backstory: str
    memory_key: Optional[str] = None
    verbose: bool = False
    allow_delegation: bool = True
    # New fields for reflection capabilities
    can_reflect: bool = True
    reflection_quality: float = 0.8  # 0.0 to 1.0 rating of reflection quality


class ReflectionFeedback(BaseModel):
    """Feedback from a reflection."""

    reflection_id: UUID
    memo_id: UUID
    source_agent_id: str
    content: str
    metadata: Dict[str, Any]
    timestamp: float


class BaseAgent(Agent):
    """Base agent class with Redis integration."""

    def __init__(
        self,
        config: AgentConfig,
        article_id: UUID,
        tools: Optional[list] = None,
        llm: Optional[Any] = None,
    ) -> None:
        """Initialize the agent.

        Args:
            config (AgentConfig): Agent configuration
            article_id (UUID): ID of the article being worked on
            tools (Optional[list], optional): List of tools available to the agent. Defaults to None.
            llm (Optional[Any], optional): Language model to use. Defaults to None.
        """
        super().__init__(
            role=config.role.value,
            goal=config.goal,
            backstory=config.backstory,
            memory=bool(config.memory_key),
            verbose=config.verbose,
            allow_delegation=config.allow_delegation,
            tools=tools or [],
            llm=llm,
        )
        self.config = config
        self.article_id = article_id
        self._message_callback: Optional[Callable[[Message], None]] = None
        
        # Reflection tracking
        self._pending_reflection_requests: Set[UUID] = set()
        self._reflection_responses: Dict[UUID, ReflectionFeedback] = {}
        self._reflection_callback: Optional[Callable[[ReflectionRequest], None]] = None

        # Set up Redis memory if configured
        if config.memory_key:
            self._setup_memory(config.memory_key)

        # Subscribe to article messages
        self._setup_communication()

    def _setup_memory(self, memory_key: str) -> None:
        """Set up Redis-based memory for the agent.

        Args:
            memory_key (str): Base key for storing agent memory
        """
        self.memory_key = f"{memory_key}:{self.article_id}"
        # Initialize memory in Redis if it doesn't exist
        if not redis_client.client.exists(self.memory_key):
            redis_client.client.json().set(self.memory_key, "$", {})

    def _setup_communication(self) -> None:
        """Set up communication channels for the agent."""
        agent_scratchpad.subscribe_to_article(
            self.article_id, self._handle_message
        )

    def _handle_message(self, message: Message) -> None:
        """Handle incoming messages from other agents.

        Args:
            message (Message): The received message
        """
        if message.agent_id != self.config.name:  # Ignore own messages
            logger.debug(
                "Agent %s received message type %s from %s",
                self.config.name,
                message.type,
                message.agent_id,
            )
            
            # Handle reflection-related messages
            if message.type == MessageType.REFLECTION_REQUEST and message.target_agent_id == self.config.name:
                self._handle_reflection_request(message)
            elif message.type == MessageType.REFLECTION_RESPONSE and message.target_agent_id == self.config.name:
                self._handle_reflection_response(message)
            elif message.type == MessageType.REFLECTION_ERROR and message.target_agent_id == self.config.name:
                self._handle_reflection_error(message)
            
            # General message handling
            if self._message_callback:
                self._message_callback(message)

    def set_message_callback(self, callback: Callable[[Message], None]) -> None:
        """Set callback for handling messages.

        Args:
            callback (Callable[[Message], None]): Function to call when messages are received
        """
        self._message_callback = callback

    def set_reflection_callback(self, callback: Callable[[ReflectionRequest], None]) -> None:
        """Set callback for handling reflection requests.

        Args:
            callback (Callable[[ReflectionRequest], None]): Function to call when reflection requests are received
        """
        self._reflection_callback = callback

    def publish_progress(self, content: Dict[str, Any]) -> None:
        """Publish a progress update.

        Args:
            content (Dict[str, Any]): Progress information
        """
        self._publish_message(MessageType.AGENT_PROGRESS, content)

    def publish_completion(self, content: Dict[str, Any]) -> None:
        """Publish completion status.

        Args:
            content (Dict[str, Any]): Completion information
        """
        self._publish_message(MessageType.AGENT_COMPLETED, content)

    def publish_error(self, error: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Publish an error message.

        Args:
            error (str): Error message
            details (Optional[Dict[str, Any]], optional): Additional error details. Defaults to None.
        """
        content = {"error": error}
        if details:
            content.update(details)
        self._publish_message(MessageType.AGENT_ERROR, content)

    def _publish_message(self, msg_type: MessageType, content: Dict[str, Any]) -> None:
        """Publish a message to the article channel.

        Args:
            msg_type (MessageType): Type of message
            content (Dict[str, Any]): Message content
        """
        message = Message(
            type=msg_type,
            agent_id=self.config.name,
            article_id=self.article_id,
            content=content,
        )
        agent_scratchpad.publish_message(message)

    async def request_reflection(
        self,
        memo_id: UUID,
        content: str,
        target_agent_id: str,
        prompt: Optional[str] = None,
        priority: ReflectionPriority = ReflectionPriority.MEDIUM,
        deadline: Optional[float] = None,
    ) -> UUID:
        """Request a reflection from another agent.

        Args:
            memo_id (UUID): ID of the memo to reflect on
            content (str): Content to reflect on
            target_agent_id (str): ID of the agent to provide reflection
            prompt (Optional[str], optional): Specific reflection prompt. Defaults to None.
            priority (ReflectionPriority, optional): Priority level. Defaults to MEDIUM.
            deadline (Optional[float], optional): Deadline timestamp. Defaults to None.

        Returns:
            UUID: ID of the reflection request
        """
        reflection_id = await agent_scratchpad.request_reflection(
            article_id=self.article_id,
            memo_id=memo_id,
            source_agent_id=self.config.name,
            target_agent_id=target_agent_id,
            content=content,
            prompt=prompt,
            priority=priority,
            deadline=deadline,
        )
        
        # Track the pending request
        self._pending_reflection_requests.add(reflection_id)
        
        logger.info(
            "Agent %s requested reflection from %s (reflection_id: %s)",
            self.config.name,
            target_agent_id,
            reflection_id,
        )
        
        return reflection_id

    async def request_reflections_from_multiple_agents(
        self,
        memo_id: UUID,
        content: str,
        target_agent_ids: List[str],
        prompt: Optional[str] = None,
        priority: ReflectionPriority = ReflectionPriority.MEDIUM,
        deadline: Optional[float] = None,
    ) -> List[UUID]:
        """Request reflections from multiple agents.

        Args:
            memo_id (UUID): ID of the memo to reflect on
            content (str): Content to reflect on
            target_agent_ids (List[str]): IDs of agents to provide reflections
            prompt (Optional[str], optional): Specific reflection prompt. Defaults to None.
            priority (ReflectionPriority, optional): Priority level. Defaults to MEDIUM.
            deadline (Optional[float], optional): Deadline timestamp. Defaults to None.

        Returns:
            List[UUID]: IDs of the reflection requests
        """
        reflection_ids = []
        
        for target_agent_id in target_agent_ids:
            reflection_id = await self.request_reflection(
                memo_id=memo_id,
                content=content,
                target_agent_id=target_agent_id,
                prompt=prompt,
                priority=priority,
                deadline=deadline,
            )
            reflection_ids.append(reflection_id)
        
        return reflection_ids

    async def submit_reflection(
        self,
        reflection_id: UUID,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Submit a reflection in response to a request.

        Args:
            reflection_id (UUID): ID of the reflection request
            content (str): Reflection content
            metadata (Optional[Dict[str, Any]], optional): Additional metadata. Defaults to None.
        """
        await agent_scratchpad.submit_reflection(
            reflection_id=reflection_id,
            agent_id=self.config.name,
            content=content,
            metadata=metadata or {},
        )
        
        logger.info(
            "Agent %s submitted reflection (reflection_id: %s)",
            self.config.name,
            reflection_id,
        )

    async def skip_reflection(
        self,
        reflection_id: UUID,
        reason: str,
    ) -> None:
        """Skip a reflection request.

        Args:
            reflection_id (UUID): ID of the reflection request
            reason (str): Reason for skipping
        """
        await agent_scratchpad.mark_reflection_skipped(
            reflection_id=reflection_id,
            reason=reason,
        )
        
        logger.info(
            "Agent %s skipped reflection (reflection_id: %s, reason: %s)",
            self.config.name,
            reflection_id,
            reason,
        )

    async def get_pending_reflections(self) -> List[ReflectionRequest]:
        """Get pending reflection requests for this agent.

        Returns:
            List[ReflectionRequest]: List of pending reflection requests
        """
        return await agent_scratchpad.get_pending_reflections(self.config.name)

    def _handle_reflection_request(self, message: Message) -> None:
        """Handle a reflection request from another agent.

        Args:
            message (Message): The reflection request message
        """
        if not self.config.can_reflect:
            # Skip if agent is not configured to provide reflections
            asyncio.create_task(
                agent_scratchpad.mark_reflection_skipped(
                    reflection_id=message.reflection_id,
                    reason=f"Agent {self.config.name} is not configured to provide reflections",
                )
            )
            return
        
        # Get the reflection request details
        memo_id = UUID(message.content.get("memo_id", ""))
        content = message.content.get("content", "")
        prompt = message.content.get("prompt", "")
        
        # Create reflection request object
        reflection_request = ReflectionRequest(
            reflection_id=message.reflection_id,
            article_id=message.article_id,
            memo_id=memo_id,
            source_agent_id=message.agent_id,
            target_agent_id=self.config.name,
            content=content,
            prompt=prompt,
            status=ReflectionStatus.PENDING,
            metadata=message.metadata,
        )
        
        # Mark as in progress
        asyncio.create_task(
            agent_scratchpad.mark_reflection_in_progress(message.reflection_id)
        )
        
        # Call the reflection callback if set
        if self._reflection_callback:
            self._reflection_callback(reflection_request)
        else:
            logger.warning(
                "Agent %s received reflection request but no reflection callback is set",
                self.config.name,
            )

    def _handle_reflection_response(self, message: Message) -> None:
        """Handle a reflection response from another agent.

        Args:
            message (Message): The reflection response message
        """
        if message.reflection_id in self._pending_reflection_requests:
            # Store the reflection feedback
            memo_id = UUID(message.content.get("memo_id", ""))
            reflection_content = message.content.get("reflection", "")
            
            feedback = ReflectionFeedback(
                reflection_id=message.reflection_id,
                memo_id=memo_id,
                source_agent_id=message.agent_id,
                content=reflection_content,
                metadata=message.metadata,
                timestamp=message.timestamp,
            )
            
            self._reflection_responses[message.reflection_id] = feedback
            self._pending_reflection_requests.remove(message.reflection_id)
            
            logger.info(
                "Agent %s received reflection from %s (reflection_id: %s)",
                self.config.name,
                message.agent_id,
                message.reflection_id,
            )

    def _handle_reflection_error(self, message: Message) -> None:
        """Handle a reflection error from another agent.

        Args:
            message (Message): The reflection error message
        """
        if message.reflection_id in self._pending_reflection_requests:
            self._pending_reflection_requests.remove(message.reflection_id)
            
            logger.warning(
                "Agent %s received reflection error from %s: %s",
                self.config.name,
                message.agent_id,
                message.content.get("error", "Unknown error"),
            )

    def get_reflection_feedback(self, memo_id: Optional[UUID] = None) -> List[ReflectionFeedback]:
        """Get reflection feedback for a specific memo or all memos.

        Args:
            memo_id (Optional[UUID], optional): ID of the memo to get feedback for. Defaults to None.

        Returns:
            List[ReflectionFeedback]: List of reflection feedback
        """
        if memo_id:
            return [
                feedback for feedback in self._reflection_responses.values()
                if feedback.memo_id == memo_id
            ]
        else:
            return list(self._reflection_responses.values())

    def has_pending_reflections(self) -> bool:
        """Check if the agent has pending reflection requests.

        Returns:
            bool: True if the agent has pending reflections, False otherwise
        """
        return len(self._pending_reflection_requests) > 0

    def get_reflection_status(self) -> Dict[str, int]:
        """Get the status of reflections.

        Returns:
            Dict[str, int]: Dictionary with reflection statistics
        """
        return {
            "pending": len(self._pending_reflection_requests),
            "completed": len(self._reflection_responses),
        }

    def cleanup(self) -> None:
        """Clean up agent resources."""
        if hasattr(self, "memory_key"):
            redis_client.client.delete(self.memory_key)
        agent_scratchpad.unsubscribe_from_article(self.article_id) 