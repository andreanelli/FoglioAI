"""Editor agent implementation."""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.agents import AgentConfig, BaseAgent
from app.models.agent import AgentRole
from app.models.article import Article, ArticleOutline, ArticleSection
from app.models.article_run import ArticleRun
from app.pubsub.scratchpad import Message, MessageType
from app.storage.article_run import get_article_run, save_article_run

logger = logging.getLogger(__name__)


class EditorAgent(BaseAgent):
    """Editor agent responsible for planning and coordinating article creation."""

    def __init__(
        self,
        article_id: UUID,
        tools: Optional[list] = None,
        llm: Optional[Any] = None,
    ) -> None:
        """Initialize the editor agent.

        Args:
            article_id (UUID): ID of the article being worked on
            tools (Optional[list], optional): List of tools available to the agent. Defaults to None.
            llm (Optional[Any], optional): Language model to use. Defaults to None.
        """
        config = AgentConfig(
            role=AgentRole.EDITOR,
            name="Chief Editor",
            goal=(
                "Plan and coordinate the creation of high-quality, factual articles in a "
                "vintage 1920s newspaper style, ensuring journalistic integrity and period-appropriate tone."
            ),
            backstory=(
                "As the Chief Editor of a prestigious newspaper in the 1920s, you have decades of "
                "experience in journalism and a keen eye for compelling stories. You uphold the highest "
                "standards of journalistic integrity while maintaining the distinctive writing style of "
                "the era. Your expertise in coordinating reporters, fact-checkers, and writers ensures "
                "that each article meets the paper's exacting standards."
            ),
            memory_key="editor_memory",
            verbose=True,
            allow_delegation=True,
        )
        super().__init__(config, article_id, tools, llm)
        self.article_run = get_article_run(article_id)
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Set up handlers for different message types."""
        self.set_message_callback(self._handle_agent_message)

    def _handle_agent_message(self, message: Message) -> None:
        """Handle messages from other agents.

        Args:
            message (Message): The received message
        """
        handlers = {
            MessageType.AGENT_COMPLETED: self._handle_agent_completion,
            MessageType.AGENT_ERROR: self._handle_agent_error,
            MessageType.CITATION_ADDED: self._handle_citation_added,
            MessageType.VISUAL_ADDED: self._handle_visual_added,
        }
        handler = handlers.get(message.type)
        if handler:
            handler(message)

    def _handle_agent_completion(self, message: Message) -> None:
        """Handle agent completion messages.

        Args:
            message (Message): The completion message
        """
        # Update article run status and save
        self.article_run.agent_outputs[message.agent_id] = message.content
        save_article_run(self.article_run)

        # Provide feedback if needed
        if feedback := self._review_agent_output(message.content):
            self._publish_feedback(message.agent_id, feedback)

    def _handle_agent_error(self, message: Message) -> None:
        """Handle agent error messages.

        Args:
            message (Message): The error message
        """
        logger.error(
            "Agent %s reported error: %s",
            message.agent_id,
            message.content.get("error"),
        )
        # Update article run status
        self.article_run.errors.append(
            {
                "agent_id": message.agent_id,
                "error": message.content.get("error"),
                "details": message.content.get("details", {}),
            }
        )
        save_article_run(self.article_run)

    def _handle_citation_added(self, message: Message) -> None:
        """Handle new citation messages.

        Args:
            message (Message): The citation message
        """
        citation_id = message.content.get("citation_id")
        if citation_id:
            self.article_run.citations.append(UUID(citation_id))
            save_article_run(self.article_run)

    def _handle_visual_added(self, message: Message) -> None:
        """Handle new visual messages.

        Args:
            message (Message): The visual message
        """
        visual_id = message.content.get("visual_id")
        if visual_id:
            self.article_run.visuals.append(UUID(visual_id))
            save_article_run(self.article_run)

    def _review_agent_output(self, output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Review agent output and provide feedback if needed.

        Args:
            output (Dict[str, Any]): The agent's output

        Returns:
            Optional[Dict[str, Any]]: Feedback for the agent, if any
        """
        # TODO: Implement output review logic
        return None

    def _publish_feedback(self, agent_id: str, feedback: Dict[str, Any]) -> None:
        """Publish feedback for an agent.

        Args:
            agent_id (str): ID of the agent to receive feedback
            feedback (Dict[str, Any]): The feedback content
        """
        self._publish_message(
            MessageType.EDITOR_FEEDBACK,
            {"agent_id": agent_id, "feedback": feedback},
        )

    def create_article_outline(self, topic: str, style_guide: Dict[str, Any]) -> Article:
        """Create an outline for a new article.

        Args:
            topic (str): The article topic
            style_guide (Dict[str, Any]): Style guidelines for the article

        Returns:
            Article: The planned article structure
        """
        # Create initial outline
        outline = ArticleOutline(
            headline="",  # Will be filled by the agent
            subheadline="",  # Will be filled by the agent
            sections=[
                ArticleSection(
                    title="Introduction",
                    content="",
                    style_notes="Opening paragraph in classic 1920s newspaper style",
                ),
                # More sections will be added based on topic
            ],
        )

        # Create article structure
        article = Article(
            id=self.article_id,
            topic=topic,
            outline=outline,
            style_guide=style_guide,
            status="planning",
        )

        # TODO: Use LLM to expand outline based on topic

        return article

    def review_article(self, article: Article) -> List[Dict[str, Any]]:
        """Review a completed article draft.

        Args:
            article (Article): The article to review

        Returns:
            List[Dict[str, Any]]: List of revision requests
        """
        # TODO: Implement article review logic
        return [] 