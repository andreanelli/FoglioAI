"""Writer agent implementation."""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.agents import AgentConfig, BaseAgent
from app.models.agent import AgentRole
from app.models.article import Article, ArticleSection
from app.models.citation import Citation
from app.pubsub.scratchpad import Message, MessageType
from app.storage.article_run import get_article_run, save_article_run
from app.web import CitationManager

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """Writer agent responsible for crafting article content."""

    def __init__(
        self,
        article_id: UUID,
        tools: Optional[list] = None,
        llm: Optional[Any] = None,
    ) -> None:
        """Initialize the writer agent.

        Args:
            article_id (UUID): ID of the article being worked on
            tools (Optional[list], optional): List of tools available to the agent. Defaults to None.
            llm (Optional[Any], optional): Language model to use. Defaults to None.
        """
        config = AgentConfig(
            role=AgentRole.EDITOR,  # Using editor role for writing
            name="Chief Writer",
            goal=(
                "Craft compelling, factual articles in an authentic 1920s newspaper style, "
                "weaving together research and citations into engaging narratives that "
                "transport readers to the era."
            ),
            backstory=(
                "As the Chief Writer for a distinguished 1920s newspaper, you have mastered "
                "the art of period-appropriate prose. Your articles capture the spirit of "
                "the age while maintaining journalistic excellence. You take pride in your "
                "ability to transform complex information into engaging stories that both "
                "inform and entertain, all while preserving the distinctive voice of the era."
            ),
            memory_key="writer_memory",
            verbose=True,
            allow_delegation=True,
        )
        super().__init__(config, article_id, tools, llm)
        self.article_run = get_article_run(article_id)
        self.citation_manager = CitationManager(redis_client.client)
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
            MessageType.EDITOR_FEEDBACK: self._handle_editor_feedback,
            MessageType.CITATION_ADDED: self._handle_citation_added,
        }
        handler = handlers.get(message.type)
        if handler:
            handler(message)

    def _handle_editor_feedback(self, message: Message) -> None:
        """Handle feedback from the editor.

        Args:
            message (Message): The feedback message
        """
        if message.content.get("agent_id") == self.config.name:
            feedback = message.content.get("feedback", {})
            # TODO: Process editor feedback and revise content accordingly
            logger.info("Received editor feedback: %s", feedback)

    def _handle_citation_added(self, message: Message) -> None:
        """Handle new citation notifications.

        Args:
            message (Message): The citation message
        """
        citation_id = message.content.get("citation_id")
        if citation_id:
            # Update our local cache of available citations
            self.article_run.citations.append(UUID(citation_id))
            save_article_run(self.article_run)

    def write_section(
        self, section: ArticleSection, citations: List[Citation]
    ) -> ArticleSection:
        """Write a section of the article.

        Args:
            section (ArticleSection): Section to write
            citations (List[Citation]): Available citations to use

        Returns:
            ArticleSection: Completed section with content

        Raises:
            Exception: If writing fails
        """
        try:
            # Report start of writing
            self.publish_progress({
                "status": "writing",
                "section": section.title,
            })

            # TODO: Use LLM to generate content in 1920s style
            # For now, use placeholder content
            section.content = self._generate_placeholder_content(section, citations)

            # Report completion
            self.publish_completion({
                "status": "completed",
                "section": section.title,
            })

            return section
        except Exception as e:
            logger.error("Failed to write section %s: %s", section.title, e)
            self.publish_error(str(e))
            raise

    def revise_section(
        self, section: ArticleSection, feedback: Dict[str, Any]
    ) -> ArticleSection:
        """Revise a section based on feedback.

        Args:
            section (ArticleSection): Section to revise
            feedback (Dict[str, Any]): Feedback to incorporate

        Returns:
            ArticleSection: Revised section

        Raises:
            Exception: If revision fails
        """
        try:
            # Report start of revision
            self.publish_progress({
                "status": "revising",
                "section": section.title,
            })

            # TODO: Use LLM to revise content based on feedback
            # For now, just return the original section
            logger.info("Revision requested for section %s: %s", section.title, feedback)

            # Report completion
            self.publish_completion({
                "status": "revised",
                "section": section.title,
            })

            return section
        except Exception as e:
            logger.error("Failed to revise section %s: %s", section.title, e)
            self.publish_error(str(e))
            raise

    def write_headlines(self, article: Article, citations: List[Citation]) -> Article:
        """Write the headline and subheadline.

        Args:
            article (Article): Article to write headlines for
            citations (List[Citation]): Available citations to use

        Returns:
            Article: Article with completed headlines

        Raises:
            Exception: If writing fails
        """
        try:
            # Report start
            self.publish_progress({"status": "writing_headlines"})

            # TODO: Use LLM to generate headlines in 1920s style
            # For now, use placeholder headlines
            article.outline.headline = "PLACEHOLDER HEADLINE"
            article.outline.subheadline = "Placeholder subheadline in 1920s style"

            # Report completion
            self.publish_completion({"status": "headlines_completed"})

            return article
        except Exception as e:
            logger.error("Failed to write headlines: %s", e)
            self.publish_error(str(e))
            raise

    def _generate_placeholder_content(
        self, section: ArticleSection, citations: List[Citation]
    ) -> str:
        """Generate placeholder content for a section.

        Args:
            section (ArticleSection): Section to generate content for
            citations (List[Citation]): Available citations

        Returns:
            str: Generated content
        """
        return (
            f"[Placeholder content for section '{section.title}' "
            f"using {len(citations)} citations in 1920s style]"
        )

    def apply_style_guide(self, content: str, style_guide: Dict[str, Any]) -> str:
        """Apply style guide rules to content.

        Args:
            content (str): Content to style
            style_guide (Dict[str, Any]): Style guidelines to apply

        Returns:
            str: Styled content
        """
        # TODO: Implement style guide application
        return content 