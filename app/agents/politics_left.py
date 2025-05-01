"""Politics-Left agent implementation."""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.agents import AgentConfig, BaseAgent
from app.models.agent import AgentRole
from app.models.citation import Citation
from app.pubsub.scratchpad import Message, MessageType
from app.redis_client import redis_client
from app.web import CitationManager

logger = logging.getLogger(__name__)


class PoliticsLeftAgent(BaseAgent):
    """Politics-Left agent responsible for providing progressive political analysis."""

    def __init__(
        self,
        article_id: UUID,
        tools: Optional[list] = None,
        llm: Optional[Any] = None,
    ) -> None:
        """Initialize the politics-left agent.

        Args:
            article_id (UUID): ID of the article being worked on
            tools (Optional[list], optional): List of tools available to the agent. Defaults to None.
            llm (Optional[Any], optional): Language model to use. Defaults to None.
        """
        config = AgentConfig(
            role=AgentRole.POLITICS_LEFT,
            name="Progressive Political Analyst",
            goal=(
                "Provide insightful analysis of political events from a progressive perspective, focusing on "
                "social equality, workers' rights, and governmental reform in the style of a modern Washington Post analysis."
            ),
            backstory=(
                "As the Progressive Political Analyst for a Washington Post-style publication, you have built "
                "your reputation advocating for social reform, labor rights, and economic justice. "
                "Your analysis draws inspiration from progressive movements and contemporary progressive thought, "
                "championing causes like racial justice, healthcare access, climate action, and economic equity. "
                "You maintain the measured yet compelling tone of modern progressive commentary "
                "in quality journalistic publications, while ensuring factual accuracy and thoughtful analysis."
            ),
            memory_key="politics_left_memory",
            verbose=True,
            allow_delegation=True,
        )
        super().__init__(config, article_id, tools, llm)

        # Initialize citation manager
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
            logger.info("Received editor feedback: %s", feedback)

    async def analyze_political_topic(self, topic: str, citations: List[Citation]) -> Dict[str, Any]:
        """Analyze a political topic from a progressive perspective.

        Args:
            topic (str): The topic to analyze
            citations (List[Citation]): Available citations to reference

        Returns:
            Dict[str, Any]: Progressive political analysis with key points and implications

        Raises:
            Exception: If analysis fails
        """
        try:
            # Report start of political analysis
            self.publish_progress({"status": "started", "topic": topic})

            # TODO: Implement actual progressive political analysis with LLM
            # This is a placeholder for the actual implementation
            analysis = {
                "perspective": "progressive",
                "key_points": [
                    "Social equality implications",
                    "Workers' rights considerations",
                    "Governmental reform needs"
                ],
                "core_values_alignment": "Analysis of how the topic aligns with progressive values",
                "policy_recommendations": ["Progressive policy recommendation 1", "Progressive policy recommendation 2"],
                "bias_markers": {
                    "progressive_bias_score": 0.75,  # Explicitly marking the progressive bias
                    "bias_areas": ["social equality", "economic justice"]
                },
                "cited_sources": [str(citation.id) for citation in citations],
            }

            # Report completion of political analysis
            self.publish_completion({
                "status": "completed",
                "analysis": analysis,
            })

            return analysis
        except Exception as e:
            logger.error("Progressive political analysis failed: %s", e)
            self.publish_error(str(e))
            raise

    async def evaluate_social_impact(self, policy: str, citations: List[Citation]) -> Dict[str, Any]:
        """Evaluate the social impact of a policy from a progressive perspective.

        Args:
            policy (str): The policy to evaluate
            citations (List[Citation]): Citations to reference

        Returns:
            Dict[str, Any]: Social impact assessment
        """
        try:
            # Report start of social impact evaluation
            self.publish_progress({"status": "evaluating_social_impact", "policy": policy})

            # TODO: Implement social impact evaluation with LLM
            assessment = {
                "equity_impact": "How the policy affects social equity",
                "worker_impact": "How the policy affects workers' rights and conditions",
                "marginalized_groups_impact": "How the policy affects marginalized communities",
                "progressive_score": 0.65,  # Rated on alignment with progressive values
                "bias_markers": {
                    "progressive_bias_score": 0.7,
                    "bias_areas": ["worker advocacy", "social equity"]
                }
            }

            return assessment
        except Exception as e:
            logger.error("Social impact evaluation failed: %s", e)
            self.publish_error(str(e))
            raise

    async def provide_counterarguments(self, conservative_points: List[str], citations: List[Citation]) -> Dict[str, Any]:
        """Provide progressive counterarguments to conservative points.

        Args:
            conservative_points (List[str]): Conservative arguments to counter
            citations (List[Citation]): Citations to reference

        Returns:
            Dict[str, Any]: Progressive counterarguments
        """
        try:
            # Report start of counterargument creation
            self.publish_progress({"status": "creating_counterarguments"})

            # TODO: Implement counterargument generation with LLM
            counterarguments = {
                "responses": [{"point": point, "counterargument": f"Progressive response to: {point}"} 
                             for point in conservative_points],
                "progressive_principles": ["Social equity", "Economic justice", "Governmental oversight"],
                "bias_markers": {
                    "progressive_bias_score": 0.8,
                    "bias_areas": ["social programs", "regulation advocacy"]
                }
            }

            return counterarguments
        except Exception as e:
            logger.error("Counterargument creation failed: %s", e)
            self.publish_error(str(e))
            raise

    async def create_progressive_memo(self, topic: str, citations: List[Citation]) -> str:
        """Create a comprehensive progressive political memo on a topic.

        Args:
            topic (str): Topic to analyze
            citations (List[Citation]): Citations to reference

        Returns:
            str: Progressive political memo content
        """
        try:
            # Report start of memo creation
            self.publish_progress({"status": "creating_memo", "topic": topic})

            # First provide political analysis
            analysis = await self.analyze_political_topic(topic, citations)

            # TODO: Use LLM to synthesize this into a cohesive memo
            memo = f"""
            PROGRESSIVE PERSPECTIVE ON {topic.upper()}
            
            From the progressive standpoint, this matter warrants careful consideration
            through the lens of social equality and economic justice.
            
            Key Points:
            - {analysis['key_points'][0]}
            - {analysis['key_points'][1]}
            - {analysis['key_points'][2]}
            
            Policy Recommendations:
            - {analysis['policy_recommendations'][0]}
            - {analysis['policy_recommendations'][1]}
            
            {analysis['core_values_alignment']}
            """

            # Report completion of memo creation
            self.publish_completion({
                "status": "completed",
                "memo": memo,
                "bias_markers": analysis['bias_markers']  # Include explicit bias markers for balancing
            })

            return memo
        except Exception as e:
            logger.error("Progressive memo creation failed: %s", e)
            self.publish_error(str(e))
            raise 