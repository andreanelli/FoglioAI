"""Article generation service."""
import asyncio
import logging
from typing import AsyncGenerator, Dict, Optional
from uuid import UUID

from app.agents.orchestrator import ArticleOrchestrator
from app.models.article import Article
from app.models.article_run import ArticleRun, ArticleRunStatus
from app.pubsub.scratchpad import Message, MessageType, agent_scratchpad
from app.storage.article_run import get_article_run, save_article_run
from app.utils.ids import generate_article_id

logger = logging.getLogger(__name__)

# Maximum concurrent article generations
MAX_CONCURRENT_GENERATIONS = 5
# Timeout for article generation (5 minutes)
GENERATION_TIMEOUT = 300


class ArticleGenerationService:
    """Service for managing article generation."""

    def __init__(self) -> None:
        """Initialize the service."""
        self._subscriptions: Dict[UUID, asyncio.Queue] = {}
        self._active_generations = 0
        self._generation_lock = asyncio.Lock()

    async def start_generation(self, topic: str, style_guide: Dict[str, str]) -> UUID:
        """Start article generation.

        Args:
            topic (str): Topic to write about
            style_guide (Dict[str, str]): Style guidelines to follow

        Returns:
            UUID: ID of the generated article

        Raises:
            Exception: If article generation fails to start
            RuntimeError: If maximum concurrent generations reached
        """
        async with self._generation_lock:
            if self._active_generations >= MAX_CONCURRENT_GENERATIONS:
                raise RuntimeError("Maximum concurrent article generations reached")
            self._active_generations += 1

        try:
            # Generate article ID
            article_id = generate_article_id()

            # Create subscription queue
            self._subscriptions[article_id] = asyncio.Queue()

            # Create initial article run
            article_run = ArticleRun(
                id=article_id,
                status=ArticleRunStatus.PENDING,
                user_query=topic,
            )
            await save_article_run(article_run)

            # Initialize orchestrator
            orchestrator = ArticleOrchestrator(article_id)

            # Start generation in background task
            asyncio.create_task(self._run_generation(orchestrator, topic, style_guide))

            return article_id
        except Exception as e:
            async with self._generation_lock:
                self._active_generations -= 1
            logger.error("Failed to start article generation: %s", e)
            raise

    async def get_status(self, article_id: UUID) -> ArticleRun:
        """Get article generation status.

        Args:
            article_id (UUID): ID of the article

        Returns:
            ArticleRun: Article run status

        Raises:
            ValueError: If article not found
        """
        article_run = await get_article_run(article_id)
        if not article_run:
            raise ValueError(f"Article {article_id} not found")
        return article_run

    async def get_article(self, article_id: UUID) -> Article:
        """Get generated article.

        Args:
            article_id (UUID): ID of the article

        Returns:
            Article: Generated article

        Raises:
            ValueError: If article not found or not completed
        """
        article_run = await get_article_run(article_id)
        if not article_run:
            raise ValueError(f"Article {article_id} not found")

        if article_run.status != ArticleRunStatus.COMPLETED:
            raise ValueError(f"Article {article_id} is not completed")

        return Article(
            id=article_id,
            title=article_run.final_output.get("title", ""),
            content=article_run.final_output.get("content", ""),
            topic=article_run.user_query,
            sources=[cite.url for cite in article_run.citations],
            created_at=article_run.created_at,
            updated_at=article_run.updated_at,
        )

    async def _run_generation(
        self,
        orchestrator: ArticleOrchestrator,
        topic: str,
        style_guide: Dict[str, str],
    ) -> None:
        """Run article generation in background.

        Args:
            orchestrator (ArticleOrchestrator): Article orchestrator
            topic (str): Topic to write about
            style_guide (Dict[str, str]): Style guidelines to follow
        """
        try:
            # Set timeout for generation
            async with asyncio.timeout(GENERATION_TIMEOUT):
                # Generate article
                article = await orchestrator.generate_article(topic, style_guide)

                # Save final output
                article_run = await get_article_run(orchestrator.article_id)
                article_run.final_output = {
                    "title": article.title,
                    "content": article.content,
                }
                article_run.status = ArticleRunStatus.COMPLETED
                await save_article_run(article_run)

                # Publish completion
                await self._publish_message(
                    orchestrator.article_id,
                    MessageType.COMPLETED,
                    {"article_id": str(article.id)},
                )

        except asyncio.TimeoutError:
            logger.error("Article generation timed out for article %s", orchestrator.article_id)
            article_run = await get_article_run(orchestrator.article_id)
            article_run.status = ArticleRunStatus.FAILED
            article_run.error_message = "Article generation timed out"
            await save_article_run(article_run)

            await self._publish_message(
                orchestrator.article_id,
                MessageType.ERROR,
                {"error": "Article generation timed out"},
            )

        except Exception as e:
            logger.error("Article generation failed: %s", e)
            article_run = await get_article_run(orchestrator.article_id)
            article_run.status = ArticleRunStatus.FAILED
            article_run.error_message = str(e)
            await save_article_run(article_run)

            await self._publish_message(
                orchestrator.article_id,
                MessageType.ERROR,
                {"error": str(e)},
            )

        finally:
            # Clean up orchestrator
            await orchestrator.cleanup()

            # Decrement active generations
            async with self._generation_lock:
                self._active_generations -= 1

    async def subscribe_to_events(
        self,
        article_id: UUID,
    ) -> AsyncGenerator[Message, None]:
        """Subscribe to article generation events.

        Args:
            article_id (UUID): ID of the article

        Yields:
            AsyncGenerator[Message, None]: Stream of article events
        """
        # Create subscription queue if needed
        if article_id not in self._subscriptions:
            self._subscriptions[article_id] = asyncio.Queue()

        # Subscribe to article events
        agent_scratchpad.subscribe_to_article(
            article_id,
            lambda msg: self._handle_message(article_id, msg),
        )

        try:
            # Yield messages from queue
            while True:
                message = await self._subscriptions[article_id].get()
                yield message

                # Stop if article is complete or failed
                if message.type in [MessageType.COMPLETED, MessageType.ERROR]:
                    break
        finally:
            # Clean up subscription
            await self.unsubscribe_from_events(article_id)

    async def unsubscribe_from_events(self, article_id: UUID) -> None:
        """Unsubscribe from article events.

        Args:
            article_id (UUID): ID of the article
        """
        # Remove subscription queue
        self._subscriptions.pop(article_id, None)

        # Unsubscribe from article events
        agent_scratchpad.unsubscribe_from_article(article_id)

    def _handle_message(self, article_id: UUID, message: Message) -> None:
        """Handle incoming article messages.

        Args:
            article_id (UUID): ID of the article
            message (Message): The received message
        """
        # Add message to subscription queue
        if queue := self._subscriptions.get(article_id):
            queue.put_nowait(message)

    async def _publish_message(
        self,
        article_id: UUID,
        msg_type: MessageType,
        content: Dict[str, str],
    ) -> None:
        """Publish a message to article subscribers.

        Args:
            article_id (UUID): ID of the article
            msg_type (MessageType): Type of message
            content (Dict[str, str]): Message content
        """
        message = Message(
            type=msg_type,
            agent_id="service",
            article_id=article_id,
            content=content,
        )
        agent_scratchpad.publish_message(message)

    async def cleanup(self) -> None:
        """Clean up service resources."""
        # Clean up all subscriptions
        for article_id in list(self._subscriptions.keys()):
            await self.unsubscribe_from_events(article_id) 