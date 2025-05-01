"""Base agent class for FoglioAI."""
import logging
from typing import Any, Callable, Dict, Optional
from uuid import UUID

from crewai import Agent
from pydantic import BaseModel

from app.models.agent import AgentRole
from app.pubsub.scratchpad import Message, MessageType, agent_scratchpad
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
            if self._message_callback:
                self._message_callback(message)

    def set_message_callback(self, callback: Callable[[Message], None]) -> None:
        """Set callback for handling messages.

        Args:
            callback (Callable[[Message], None]): Function to call when messages are received
        """
        self._message_callback = callback

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

    def cleanup(self) -> None:
        """Clean up agent resources."""
        if hasattr(self, "memory_key"):
            redis_client.client.delete(self.memory_key)
        agent_scratchpad.unsubscribe_from_article(self.article_id) 