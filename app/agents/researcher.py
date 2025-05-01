"""Researcher agent implementation."""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import AnyHttpUrl

from app.agents import AgentConfig, BaseAgent
from app.models.agent import AgentRole
from app.models.citation import Citation
from app.pubsub.scratchpad import Message, MessageType
from app.redis_client import redis_client
from app.web import (
    CitationManager,
    ContentExtractor,
    ExtractionError,
    FetchError,
    WebCache,
    WebFetcher,
)

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """Researcher agent responsible for gathering and analyzing source material."""

    def __init__(
        self,
        article_id: UUID,
        tools: Optional[list] = None,
        llm: Optional[Any] = None,
    ) -> None:
        """Initialize the researcher agent.

        Args:
            article_id (UUID): ID of the article being worked on
            tools (Optional[list], optional): List of tools available to the agent. Defaults to None.
            llm (Optional[Any], optional): Language model to use. Defaults to None.
        """
        config = AgentConfig(
            role=AgentRole.HISTORIAN,  # Using historian role for research
            name="Chief Researcher",
            goal=(
                "Gather, analyze, and verify information from reliable sources, ensuring "
                "factual accuracy and proper citation in a style befitting a 1920s newspaper."
            ),
            backstory=(
                "As the Chief Researcher for a prestigious 1920s newspaper, you have "
                "developed a keen eye for reliable sources and factual reporting. Your "
                "extensive network of contacts and deep understanding of current events "
                "allows you to gather accurate information quickly. You take pride in "
                "maintaining the paper's reputation for truthful reporting."
            ),
            memory_key="researcher_memory",
            verbose=True,
            allow_delegation=True,
        )
        super().__init__(config, article_id, tools, llm)

        # Initialize web tools
        self.web_cache = WebCache(redis_client.client)
        self.web_fetcher = WebFetcher()
        self.content_extractor = ContentExtractor()
        self.citation_manager = CitationManager(redis_client.client)

        # Set up message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Set up handlers for different message types."""
        self.set_message_callback(self._handle_agent_message)

    def _handle_agent_message(self, message: Message) -> None:
        """Handle messages from other agents.

        Args:
            message (Message): The received message
        """
        if message.type == MessageType.EDITOR_FEEDBACK:
            self._handle_editor_feedback(message)

    def _handle_editor_feedback(self, message: Message) -> None:
        """Handle feedback from the editor.

        Args:
            message (Message): The feedback message
        """
        if message.content.get("agent_id") == self.config.name:
            feedback = message.content.get("feedback", {})
            # TODO: Process editor feedback and adjust research accordingly
            logger.info("Received editor feedback: %s", feedback)

    async def research_topic(self, topic: str, num_sources: int = 3) -> List[Citation]:
        """Research a topic and gather relevant sources.

        Args:
            topic (str): Topic to research
            num_sources (int, optional): Number of sources to gather. Defaults to 3.

        Returns:
            List[Citation]: List of citations for gathered sources

        Raises:
            Exception: If research fails
        """
        try:
            # Report start of research
            self.publish_progress({"status": "started", "topic": topic})

            citations = []
            for url in await self._find_relevant_urls(topic, num_sources):
                try:
                    citation = await self._process_url(url)
                    if citation:
                        citations.append(citation)
                        # Notify about new citation
                        self._publish_message(
                            MessageType.CITATION_ADDED,
                            {"citation_id": str(citation.id)},
                        )
                except (FetchError, ExtractionError) as e:
                    logger.warning("Failed to process URL %s: %s", url, e)
                    continue

            # Report research completion
            self.publish_completion({
                "status": "completed",
                "citations": [str(c.id) for c in citations],
            })

            return citations
        except Exception as e:
            logger.error("Research failed: %s", e)
            self.publish_error(str(e))
            raise

    async def _find_relevant_urls(self, topic: str, num_sources: int) -> List[AnyHttpUrl]:
        """Find relevant URLs for a topic.

        Args:
            topic (str): Topic to research
            num_sources (int): Number of sources to find

        Returns:
            List[AnyHttpUrl]: List of relevant URLs
        """
        # TODO: Implement URL discovery using search tools
        # For now, return an empty list
        return []

    async def _process_url(self, url: AnyHttpUrl) -> Optional[Citation]:
        """Process a URL and create a citation.

        Args:
            url (AnyHttpUrl): URL to process

        Returns:
            Optional[Citation]: Created citation if successful, None otherwise

        Raises:
            FetchError: If URL fetching fails
            ExtractionError: If content extraction fails
        """
        # Check cache first
        cached_content = await self.web_cache.get(url)
        if not cached_content:
            # Fetch and cache if not found
            content = await self.web_fetcher.fetch(url)
            await self.web_cache.set(url, content)
        else:
            content = cached_content

        # Extract relevant content
        extracted = await self.content_extractor.extract(content)
        if not extracted:
            logger.warning("No content extracted from %s", url)
            return None

        # Create citation
        citation = self.citation_manager.create_citation(
            url=url,
            content={
                "title": extracted.get("title", ""),
                "author": extracted.get("author"),
                "publication_date": extracted.get("date"),
            },
            excerpt=extracted.get("excerpt", ""),
        )

        # Associate with article
        self.citation_manager.add_citation_to_article(self.article_id, citation.id)

        return citation

    def analyze_sources(self, citations: List[Citation]) -> Dict[str, Any]:
        """Analyze gathered sources for reliability and relevance.

        Args:
            citations (List[Citation]): Citations to analyze

        Returns:
            Dict[str, Any]: Analysis results
        """
        # TODO: Implement source analysis
        return {
            "num_sources": len(citations),
            "source_quality": "high",  # Placeholder
            "coverage": "comprehensive",  # Placeholder
        }

    def fact_check(self, statement: str, citations: List[Citation]) -> Dict[str, Any]:
        """Check a statement against gathered sources.

        Args:
            statement (str): Statement to check
            citations (List[Citation]): Citations to check against

        Returns:
            Dict[str, Any]: Fact-checking results
        """
        # TODO: Implement fact checking
        return {
            "verified": True,  # Placeholder
            "confidence": 0.9,  # Placeholder
            "supporting_citations": [str(c.id) for c in citations],
        } 