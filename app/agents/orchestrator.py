"""Agent orchestrator implementation."""
import asyncio
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from crewai import Crew, Process, Task

from .editor import EditorAgent
from .researcher import ResearcherAgent
from .writer import WriterAgent
from app.models.article import Article
from app.models.article_run import ArticleRun
from app.models.citation import Citation
from app.storage.article_run import get_article_run, save_article_run

logger = logging.getLogger(__name__)


class ArticleOrchestrator:
    """Orchestrator for managing article generation workflow."""

    def __init__(
        self,
        article_id: UUID,
        llm: Optional[Any] = None,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            article_id (UUID): ID of the article being worked on
            llm (Optional[Any], optional): Language model to use. Defaults to None.
        """
        self.article_id = article_id
        self.llm = llm
        self.article_run = get_article_run(article_id)

        # Initialize agents
        self.editor = EditorAgent(article_id, llm=llm)
        self.researcher = ResearcherAgent(article_id, llm=llm)
        self.writer = WriterAgent(article_id, llm=llm)

    async def generate_article(self, topic: str, style_guide: Dict[str, Any]) -> Article:
        """Generate an article using the agent workflow.

        Args:
            topic (str): Topic to write about
            style_guide (Dict[str, Any]): Style guidelines to follow

        Returns:
            Article: The generated article

        Raises:
            Exception: If article generation fails
        """
        try:
            # Update article run status
            self.article_run.status = "in_progress"
            save_article_run(self.article_run)

            # Create initial article outline
            article = self.editor.create_article_outline(topic, style_guide)

            # Create CrewAI crew and tasks
            crew = Crew(
                agents=[self.editor, self.researcher, self.writer],
                tasks=self._create_tasks(article),
                process=Process.sequential,  # Run tasks in sequence
                verbose=True,
            )

            # Execute the workflow
            try:
                await crew.run()
                self.article_run.status = "completed"
            except Exception as e:
                logger.error("Crew execution failed: %s", e)
                self.article_run.status = "failed"
                self.article_run.errors.append({
                    "agent_id": "orchestrator",
                    "error": str(e),
                })
                raise

            # Save final state
            save_article_run(self.article_run)

            return article
        except Exception as e:
            logger.error("Article generation failed: %s", e)
            self.article_run.status = "failed"
            self.article_run.errors.append({
                "agent_id": "orchestrator",
                "error": str(e),
            })
            save_article_run(self.article_run)
            raise
        finally:
            # Clean up resources
            await self.cleanup()

    def _create_tasks(self, article: Article) -> List[Task]:
        """Create CrewAI tasks for article generation.

        Args:
            article (Article): Article being generated

        Returns:
            List[Task]: List of tasks to execute
        """
        tasks = []

        # Research task
        tasks.append(
            Task(
                description=(
                    f"Research the topic '{article.topic}' and gather reliable sources. "
                    "Focus on factual accuracy and comprehensive coverage."
                ),
                agent=self.researcher,
                expected_output=List[Citation],
                context={
                    "article_id": str(self.article_id),
                    "topic": article.topic,
                },
            )
        )

        # Writing tasks
        for section in article.outline.sections:
            tasks.append(
                Task(
                    description=(
                        f"Write the section '{section.title}' in authentic 1920s "
                        "newspaper style, incorporating research findings and maintaining "
                        "factual accuracy."
                    ),
                    agent=self.writer,
                    expected_output=str,
                    context={
                        "article_id": str(self.article_id),
                        "section": section.model_dump(),
                        "style_guide": article.style_guide,
                    },
                )
            )

        # Review task
        tasks.append(
            Task(
                description=(
                    "Review the complete article for accuracy, style consistency, "
                    "and adherence to 1920s newspaper conventions."
                ),
                agent=self.editor,
                expected_output=List[Dict[str, Any]],
                context={
                    "article_id": str(self.article_id),
                    "article": article.model_dump(),
                },
            )
        )

        return tasks

    async def cleanup(self) -> None:
        """Clean up resources used by the orchestrator."""
        # Clean up agent resources
        self.editor.cleanup()
        self.researcher.cleanup()
        self.writer.cleanup()

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress of article generation.

        Returns:
            Dict[str, Any]: Progress information
        """
        return {
            "status": self.article_run.status,
            "completed_tasks": len(
                [
                    output
                    for output in self.article_run.agent_outputs.values()
                    if output.get("status") == "completed"
                ]
            ),
            "total_tasks": len(self._create_tasks(Article(
                id=self.article_id,
                topic="",  # Dummy topic for task count
                outline=None,
                style_guide={},
                status="",
            ))),
            "errors": self.article_run.errors,
        } 