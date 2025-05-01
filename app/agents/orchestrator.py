"""Agent orchestrator implementation."""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from crewai import Crew, Process, Task

from .editor import EditorAgent
from .geopolitics import GeopoliticsAgent
from .historian import HistorianAgent
from .politics_left import PoliticsLeftAgent
from .politics_right import PoliticsRightAgent
from .researcher import ResearcherAgent
from .writer import WriterAgent
from app.models.agent import AgentRole
from app.models.article import Article
from app.models.article_run import ArticleRun, ArticleStatus
from app.models.citation import Citation
from app.pubsub.scratchpad import MessageType
from app.storage.article_run import get_article_run, save_article_run
from app.storage.memos import get_memos_by_article
from app.utils.bias import BiasDetector, BiasBalancer
from app.utils.article_balancer import ArticleBalancer

logger = logging.getLogger(__name__)


class OrchestratorConfig:
    """Configuration for the article orchestrator."""
    
    # Minimum reflection quality threshold (0.0-1.0)
    MIN_REFLECTION_QUALITY = 0.7
    
    # Number of reflections to request per memo
    REFLECTIONS_PER_MEMO = 2
    
    # Topics that should include specialized agents
    POLITICAL_TOPICS = {"politics", "election", "government", "policy", "democrat", "republican", "congress", "senate", "house", "president", "campaign", "legislation", "law", "bill", "vote", "voting", "liberal", "conservative"}
    HISTORICAL_TOPICS = {"history", "historical", "past", "ancient", "medieval", "century", "war", "revolution", "empire", "dynasty", "era", "period", "civilization", "heritage", "legacy", "traditional"}
    INTERNATIONAL_TOPICS = {"international", "global", "world", "foreign", "diplomatic", "diplomacy", "nation", "country", "region", "trade", "border", "alliance", "treaty", "relation", "geopolitical", "geopolitics", "UN", "NATO", "EU", "union"}
    
    # Agent selection weights for different topic types
    AGENT_WEIGHTS = {
        "political": {
            AgentRole.POLITICS_LEFT: 0.8,
            AgentRole.POLITICS_RIGHT: 0.8,
            AgentRole.HISTORIAN: 0.6,
            AgentRole.GEOPOLITICS: 0.5,
            AgentRole.RESEARCHER: 1.0,
            AgentRole.WRITER: 1.0,
            AgentRole.EDITOR: 1.0,
        },
        "historical": {
            AgentRole.POLITICS_LEFT: 0.4,
            AgentRole.POLITICS_RIGHT: 0.4,
            AgentRole.HISTORIAN: 1.0,
            AgentRole.GEOPOLITICS: 0.6,
            AgentRole.RESEARCHER: 1.0,
            AgentRole.WRITER: 1.0,
            AgentRole.EDITOR: 1.0,
        },
        "international": {
            AgentRole.POLITICS_LEFT: 0.5,
            AgentRole.POLITICS_RIGHT: 0.5,
            AgentRole.HISTORIAN: 0.7,
            AgentRole.GEOPOLITICS: 1.0,
            AgentRole.RESEARCHER: 1.0,
            AgentRole.WRITER: 1.0,
            AgentRole.EDITOR: 1.0,
        },
        "general": {
            AgentRole.POLITICS_LEFT: 0.3,
            AgentRole.POLITICS_RIGHT: 0.3,
            AgentRole.HISTORIAN: 0.5,
            AgentRole.GEOPOLITICS: 0.5,
            AgentRole.RESEARCHER: 1.0,
            AgentRole.WRITER: 1.0,
            AgentRole.EDITOR: 1.0,
        },
    }


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
        
        # Create all potential agents
        self._initialize_agents()
        
        # Working sets
        self._selected_agents = set()
        self._active_agents = set()
        self._completed_agents = set()
        
        # Reflection tracking
        self._reflection_phase_complete = False
        self._reflection_in_progress = False
        
        # Utilities for bias detection and balancing
        self.bias_detector = BiasDetector()
        self.article_balancer = ArticleBalancer(article_id)

    def _initialize_agents(self) -> None:
        """Initialize all potential agents."""
        # Core agents
        self.editor = EditorAgent(self.article_id, llm=self.llm)
        self.researcher = ResearcherAgent(self.article_id, llm=self.llm)
        self.writer = WriterAgent(self.article_id, llm=self.llm)
        
        # Specialized agents
        self.historian = HistorianAgent(self.article_id, llm=self.llm)
        self.politics_left = PoliticsLeftAgent(self.article_id, llm=self.llm)
        self.politics_right = PoliticsRightAgent(self.article_id, llm=self.llm)
        self.geopolitics = GeopoliticsAgent(self.article_id, llm=self.llm)
        
        # Map of agent names to instances
        self.agent_map = {
            "Chief Editor": self.editor,
            "Researcher": self.researcher,
            "Writer": self.writer,
            "Historian": self.historian,
            "Politics-Left": self.politics_left,
            "Politics-Right": self.politics_right,
            "Geopolitics": self.geopolitics,
        }

    def _select_agents_for_topic(self, topic: str) -> Set[str]:
        """Select appropriate agents based on the article topic.

        Args:
            topic (str): The article topic

        Returns:
            Set[str]: Set of agent names to include in the workflow
        """
        # Determine topic type
        topic_lower = topic.lower()
        topic_type = "general"
        
        if any(keyword in topic_lower for keyword in OrchestratorConfig.POLITICAL_TOPICS):
            topic_type = "political"
        elif any(keyword in topic_lower for keyword in OrchestratorConfig.HISTORICAL_TOPICS):
            topic_type = "historical"
        elif any(keyword in topic_lower for keyword in OrchestratorConfig.INTERNATIONAL_TOPICS):
            topic_type = "international"
        
        # Get weights for this topic type
        weights = OrchestratorConfig.AGENT_WEIGHTS.get(topic_type, OrchestratorConfig.AGENT_WEIGHTS["general"])
        
        # Select agents based on weights
        selected_agents = set()
        
        # Core agents are always included
        selected_agents.add("Chief Editor")
        selected_agents.add("Researcher")
        selected_agents.add("Writer")
        
        # Add specialized agents based on weights
        if weights[AgentRole.HISTORIAN] >= 0.7:
            selected_agents.add("Historian")
        
        if weights[AgentRole.POLITICS_LEFT] >= 0.7 and weights[AgentRole.POLITICS_RIGHT] >= 0.7:
            # For political balance, include both or neither
            selected_agents.add("Politics-Left")
            selected_agents.add("Politics-Right")
        
        if weights[AgentRole.GEOPOLITICS] >= 0.7:
            selected_agents.add("Geopolitics")
        
        # Log selected agents
        logger.info(
            "Selected agents for topic '%s' (type: %s): %s", 
            topic, 
            topic_type, 
            ", ".join(selected_agents)
        )
        
        return selected_agents

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
            self.article_run.status = ArticleStatus.DRAFTING
            save_article_run(self.article_run)
            
            # Select agents based on topic
            self._selected_agents = self._select_agents_for_topic(topic)
            self._active_agents = self._selected_agents.copy()

            # Create initial article outline
            article = self.editor.create_article_outline(topic, style_guide)
            
            # Create CrewAI crew and tasks
            drafting_crew = Crew(
                agents=[self.agent_map[agent_name] for agent_name in self._selected_agents],
                tasks=self._create_drafting_tasks(article),
                process=Process.sequential,  # Run tasks in sequence
                verbose=True,
            )

            # Execute the drafting workflow
            try:
                await drafting_crew.run()
                
                # Start reflection phase
                await self._run_reflection_phase()
                
                # Final synthesis by the editor
                await self._run_synthesis_phase(article)
                
                self.article_run.status = ArticleStatus.COMPLETED
            except Exception as e:
                logger.error("Crew execution failed: %s", e)
                self.article_run.status = ArticleStatus.FAILED
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
            self.article_run.status = ArticleStatus.FAILED
            self.article_run.errors.append({
                "agent_id": "orchestrator",
                "error": str(e),
            })
            save_article_run(self.article_run)
            raise
        finally:
            # Clean up resources
            await self.cleanup()

    def _create_drafting_tasks(self, article: Article) -> List[Task]:
        """Create CrewAI tasks for the drafting phase.

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

        # Add specialized agent tasks based on selected agents
        if "Historian" in self._selected_agents:
            tasks.append(
                Task(
                    description=(
                        f"Provide historical context and analysis for the topic '{article.topic}'. "
                        "Focus on relevant historical background, precedents, and patterns."
                    ),
                    agent=self.historian,
                    expected_output=str,
                    context={
                        "article_id": str(self.article_id),
                        "topic": article.topic,
                    },
                )
            )
        
        if "Politics-Left" in self._selected_agents:
            tasks.append(
                Task(
                    description=(
                        f"Analyze the topic '{article.topic}' from a progressive perspective. "
                        "Provide insights on political implications with clear bias markers."
                    ),
                    agent=self.politics_left,
                    expected_output=str,
                    context={
                        "article_id": str(self.article_id),
                        "topic": article.topic,
                    },
                )
            )
        
        if "Politics-Right" in self._selected_agents:
            tasks.append(
                Task(
                    description=(
                        f"Analyze the topic '{article.topic}' from a conservative perspective. "
                        "Provide insights on political implications with clear bias markers."
                    ),
                    agent=self.politics_right,
                    expected_output=str,
                    context={
                        "article_id": str(self.article_id),
                        "topic": article.topic,
                    },
                )
            )
        
        if "Geopolitics" in self._selected_agents:
            tasks.append(
                Task(
                    description=(
                        f"Analyze the topic '{article.topic}' from an international relations perspective. "
                        "Focus on global implications, power dynamics, and cross-border issues."
                    ),
                    agent=self.geopolitics,
                    expected_output=str,
                    context={
                        "article_id": str(self.article_id),
                        "topic": article.topic,
                    },
                )
            )

        # Writing tasks
        tasks.append(
            Task(
                description=(
                    f"Write an article on '{article.topic}' incorporating all agent memos "
                    "in a modern Washington Post style, maintaining factual accuracy and "
                    "journalistic integrity."
                ),
                agent=self.writer,
                expected_output=str,
                context={
                    "article_id": str(self.article_id),
                    "article": article.model_dump(),
                    "style_guide": article.style_guide,
                },
            )
        )

        return tasks

    async def _run_reflection_phase(self) -> None:
        """Run the reflection phase after the drafting phase is complete."""
        try:
            logger.info("Starting reflection phase for article %s", self.article_id)
            
            # Update article status
            self.article_run.status = ArticleStatus.REFLECTING
            self._reflection_in_progress = True
            save_article_run(self.article_run)
            
            # The Editor agent will coordinate reflections
            # We just need to wait for the reflection process to complete
            
            # Wait for reflection phase to complete (monitored by the Editor)
            max_wait_time = 300  # 5 minutes maximum
            check_interval = 5  # Check every 5 seconds
            
            for _ in range(0, max_wait_time, check_interval):
                # Check if reflection phase is complete
                article_run = get_article_run(self.article_id)
                if article_run.metadata.get("reflection_complete", False):
                    self._reflection_in_progress = False
                    self._reflection_phase_complete = True
                    logger.info("Reflection phase completed for article %s", self.article_id)
                    break
                
                # Wait before checking again
                await asyncio.sleep(check_interval)
            
            if not self._reflection_phase_complete:
                logger.warning("Reflection phase timed out for article %s", self.article_id)
                self._reflection_in_progress = False
        
        except Exception as e:
            logger.error("Reflection phase failed: %s", e)
            self._reflection_in_progress = False
            self.article_run.errors.append({
                "agent_id": "orchestrator",
                "error": f"Reflection phase failed: {str(e)}",
            })
            save_article_run(self.article_run)

    async def _run_synthesis_phase(self, article: Article) -> None:
        """Run the final synthesis phase after reflection.

        Args:
            article (Article): The article being generated
        """
        try:
            logger.info("Starting synthesis phase for article %s", self.article_id)
            
            # Update article status
            self.article_run.status = ArticleStatus.SYNTHESIZING
            save_article_run(self.article_run)
            
            # Analyze bias in the memos and reflections
            bias_analysis = await self.article_balancer.analyze_article_bias()
            
            # Get all memos
            memos = await get_memos_by_article(self.article_id)
            
            # Generate balanced content
            content = await self.article_balancer.generate_balanced_content(memos, bias_analysis)
            
            # Update article with final content
            article.content = content
            
            # Update article run with bias analysis
            self.article_run.metadata["bias_analysis"] = bias_analysis
            self.article_run.final_output = {
                "title": article.title,
                "content": content,
                "bias_analysis": bias_analysis,
            }
            
            save_article_run(self.article_run)
            
            logger.info("Synthesis phase completed for article %s", self.article_id)
            
        except Exception as e:
            logger.error("Synthesis phase failed: %s", e)
            self.article_run.errors.append({
                "agent_id": "orchestrator",
                "error": f"Synthesis phase failed: {str(e)}",
            })
            save_article_run(self.article_run)

    async def cleanup(self) -> None:
        """Clean up resources used by the orchestrator."""
        # Clean up agent resources
        for agent_name, agent in self.agent_map.items():
            agent.cleanup()

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress of article generation.

        Returns:
            Dict[str, Any]: Progress information
        """
        # Calculate tasks completed and total
        total_tasks = len(self._selected_agents) + 2  # +2 for reflection and synthesis
        completed_tasks = len(self._completed_agents)
        
        if self._reflection_phase_complete:
            completed_tasks += 1
        
        if self.article_run.status == ArticleStatus.COMPLETED:
            completed_tasks = total_tasks
        
        # Create progress dict
        progress = {
            "status": self.article_run.status,
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks,
            "errors": self.article_run.errors,
            "reflection_status": "completed" if self._reflection_phase_complete else 
                               "in_progress" if self._reflection_in_progress else "pending",
        }
        
        # Add bias analysis if available
        if "bias_analysis" in self.article_run.metadata:
            progress["bias_analysis"] = self.article_run.metadata["bias_analysis"]
        
        return progress

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics about the article generation process.

        Returns:
            Dict[str, Any]: Metrics information
        """
        metrics = {
            "generation_time": None,  # Will be calculated
            "agent_count": len(self._selected_agents),
            "reflection_count": 0,  # Will be filled
            "bias_levels": {},  # Will be filled
        }
        
        # Calculate generation time if completed
        if self.article_run.completed_at and self.article_run.created_at:
            generation_time = (self.article_run.completed_at - self.article_run.created_at).total_seconds()
            metrics["generation_time"] = generation_time
        
        # Get reflection counts if available
        if "reflections" in self.article_run.metadata:
            reflections = self.article_run.metadata["reflections"]
            metrics["reflection_count"] = sum(len(memo_reflections) for memo_reflections in reflections.values())
        
        # Get bias levels if available
        if "bias_analysis" in self.article_run.metadata:
            bias_analysis = self.article_run.metadata["bias_analysis"]
            if "levels_by_type" in bias_analysis:
                metrics["bias_levels"] = bias_analysis["levels_by_type"]
        
        return metrics 