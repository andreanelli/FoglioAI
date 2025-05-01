"""Editor agent implementation."""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from app.agents import AgentConfig, BaseAgent
from app.models.agent import AgentRole
from app.models.article import Article, ArticleOutline, ArticleSection
from app.models.article_run import ArticleRun, ArticleStatus
from app.pubsub.scratchpad import (
    Message, 
    MessageType, 
    ReflectionPriority,
    ReflectionRequest,
    ReflectionStatus,
)
from app.storage.article_run import get_article_run, save_article_run
from app.storage.memos import get_memo_by_id, get_memos_by_article

logger = logging.getLogger(__name__)


class ReflectionConfig:
    """Configuration for reflection process."""
    
    # Minimum number of reflections to consider per memo
    MIN_REFLECTIONS_PER_MEMO = 2
    
    # Maximum number of reflections to request per memo
    MAX_REFLECTIONS_PER_MEMO = 3
    
    # Threshold quality score to consider reflection "sufficient" (0-1)
    REFLECTION_QUALITY_THRESHOLD = 0.7
    
    # Prioritize reflection combinations (agent pairs)
    REFLECTION_PRIORITIES = {
        # Higher values indicate higher priority pairs
        # Format: (source_role, reviewer_role): priority
        (AgentRole.POLITICS_LEFT, AgentRole.POLITICS_RIGHT): 5,  # Highest priority - opposing views
        (AgentRole.POLITICS_RIGHT, AgentRole.POLITICS_LEFT): 5,
        (AgentRole.HISTORIAN, AgentRole.GEOPOLITICS): 4,
        (AgentRole.GEOPOLITICS, AgentRole.HISTORIAN): 4,
        (AgentRole.WRITER, AgentRole.EDITOR): 3,
        (AgentRole.RESEARCHER, AgentRole.HISTORIAN): 3,
    }


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
                "Washington Post style, ensuring journalistic integrity and balanced coverage."
            ),
            backstory=(
                "As the Chief Editor with decades of experience in journalism at the Washington Post, "
                "you have a keen eye for compelling stories. You uphold the highest standards of "
                "journalistic integrity, ensuring balanced reporting especially on politically sensitive "
                "topics. Your expertise in coordinating reporters, fact-checkers, and writers ensures "
                "that each article meets exacting standards for quality and fairness."
            ),
            memory_key="editor_memory",
            verbose=True,
            allow_delegation=True,
            can_reflect=True,
            reflection_quality=0.95,  # Editors should provide high-quality reflections
        )
        super().__init__(config, article_id, tools, llm)
        self.article_run = get_article_run(article_id)
        
        # Reflection tracking
        self._reflection_phase_complete = False
        self._memo_reflection_counts: Dict[UUID, int] = {}  # Tracks reflections per memo
        self._pending_reflections: Set[UUID] = set()  # Reflection IDs waiting for completion
        self._reflection_plan: Dict[UUID, List[str]] = {}  # Maps memo IDs to reviewer agent IDs
        
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Set up handlers for different message types."""
        self.set_message_callback(self._handle_agent_message)
        # Set reflection callback
        self.set_reflection_callback(self._handle_reflection_request)

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
            MessageType.REFLECTION_COMPLETED: self._handle_reflection_completed,
            MessageType.REFLECTION_ERROR: self._handle_reflection_error,
            MessageType.REFLECTION_SUMMARY: self._handle_reflection_summary,
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

        # If this completes the drafting phase, start the reflection phase
        if self._check_drafting_complete() and not self._reflection_phase_complete:
            asyncio.create_task(self._start_reflection_phase())

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

    def _handle_reflection_request(self, request: ReflectionRequest) -> None:
        """Handle reflection request from other agents.

        Args:
            request (ReflectionRequest): The reflection request
        """
        # Editor doesn't typically receive reflection requests except for
        # coordinating the reflection process, but we'll implement it anyway
        asyncio.create_task(self._process_reflection_request(request))

    async def _process_reflection_request(self, request: ReflectionRequest) -> None:
        """Process a reflection request.

        Args:
            request (ReflectionRequest): The reflection request
        """
        logger.info(
            "Editor processing reflection request from %s for memo %s",
            request.source_agent_id,
            request.memo_id,
        )
        
        # Generate reflection content - Editor gives high-quality feedback
        reflection_content = await self._generate_reflection_for_memo(
            request.memo_id, 
            request.content, 
            request.prompt,
        )
        
        # Submit reflection
        await self.submit_reflection(
            reflection_id=request.reflection_id,
            content=reflection_content,
            metadata={
                "quality_score": 0.95,  # Editor provides high-quality feedback
                "bias_score": 0.1,  # Editor should provide balanced feedback
                "suggestions_count": reflection_content.count("suggestion:"),
            },
        )

    async def _generate_reflection_for_memo(
        self, 
        memo_id: UUID, 
        content: str, 
        prompt: Optional[str] = None,
    ) -> str:
        """Generate reflection content for a memo.

        Args:
            memo_id (UUID): ID of the memo to reflect on
            content (str): Content to reflect on
            prompt (Optional[str], optional): Specific reflection prompt. Defaults to None.

        Returns:
            str: Generated reflection content
        """
        # TODO: Use LLM to generate actual reflection content
        # For now, we'll return a placeholder
        return (
            "Reflection on memo content:\n\n"
            "Overall quality: High\n"
            "Bias assessment: This memo contains some bias in the framing of economic issues "
            "that could be balanced with alternative perspectives.\n\n"
            "Specific suggestions:\n"
            "1. suggestion: Consider including additional context about historical precedents.\n"
            "2. suggestion: The economic analysis could be strengthened with more recent data.\n"
            "3. suggestion: Some statements about political motivations appear speculative "
            "and should be clearly marked as analysis rather than fact.\n\n"
            "The memo otherwise demonstrates solid reporting and clear writing."
        )

    def _handle_reflection_completed(self, message: Message) -> None:
        """Handle reflection completed messages.

        Args:
            message (Message): The reflection completed message
        """
        reflection_id = message.reflection_id
        if reflection_id and reflection_id in self._pending_reflections:
            self._pending_reflections.remove(reflection_id)
            
            # Store the reflection in the article run
            memo_id = UUID(message.content.get("memo_id", ""))
            reflection = {
                "reflection_id": str(reflection_id),
                "source_agent_id": message.agent_id,
                "content": message.content.get("reflection", ""),
                "metadata": message.metadata or {},
                "timestamp": message.timestamp,
            }
            
            if "reflections" not in self.article_run.metadata:
                self.article_run.metadata["reflections"] = {}
            
            memo_reflections = self.article_run.metadata["reflections"].get(str(memo_id), [])
            memo_reflections.append(reflection)
            self.article_run.metadata["reflections"][str(memo_id)] = memo_reflections
            save_article_run(self.article_run)
            
            # Check if reflection phase is complete
            if not self._pending_reflections and self._reflection_plan:
                # All planned reflections are complete
                asyncio.create_task(self._finalize_reflection_phase())

    def _handle_reflection_error(self, message: Message) -> None:
        """Handle reflection error messages.

        Args:
            message (Message): The reflection error message
        """
        reflection_id = message.reflection_id
        if reflection_id and reflection_id in self._pending_reflections:
            self._pending_reflections.remove(reflection_id)
            
            logger.warning(
                "Reflection %s failed: %s",
                reflection_id,
                message.content.get("error", "Unknown error"),
            )
            
            # Check if reflection phase is complete despite this error
            if not self._pending_reflections and self._reflection_plan:
                # All planned reflections are complete
                asyncio.create_task(self._finalize_reflection_phase())

    def _handle_reflection_summary(self, message: Message) -> None:
        """Handle reflection summary messages.

        Args:
            message (Message): The reflection summary message
        """
        # Store the reflection summary in the article run
        memo_id = UUID(message.content.get("memo_id", ""))
        summary = message.content.get("summary", "")
        
        if "reflection_summaries" not in self.article_run.metadata:
            self.article_run.metadata["reflection_summaries"] = {}
        
        self.article_run.metadata["reflection_summaries"][str(memo_id)] = {
            "summary": summary,
            "source_agent_id": message.agent_id,
            "timestamp": message.timestamp,
        }
        save_article_run(self.article_run)

    def _check_drafting_complete(self) -> bool:
        """Check if all agents have completed their drafting work.

        Returns:
            bool: True if drafting phase is complete
        """
        # Check if all required agents have submitted their memos
        required_agents = {
            "Researcher", 
            "Writer", 
            "Historian", 
            "Politics-Left", 
            "Politics-Right", 
            "Geopolitics"
        }
        completed_agents = set(self.article_run.agent_outputs.keys())
        
        return required_agents.issubset(completed_agents)

    async def _start_reflection_phase(self) -> None:
        """Start the reflection phase after drafting is complete."""
        logger.info("Starting reflection phase for article %s", self.article_id)
        
        # Update article status
        self.article_run.status = ArticleStatus.REFLECTING
        save_article_run(self.article_run)
        
        # Get all memos for this article
        memos = await get_memos_by_article(self.article_id)
        
        # Create reflection plan
        self._create_reflection_plan(memos)
        
        # Request reflections according to plan
        await self._request_planned_reflections()

    def _create_reflection_plan(self, memos: List[Dict[str, Any]]) -> None:
        """Create a plan for which agents should reflect on which memos.

        Args:
            memos (List[Dict[str, Any]]): List of memos to plan reflections for
        """
        plan = {}
        
        # Map agent roles for easier access
        agent_roles = {
            "Researcher": AgentRole.RESEARCHER,
            "Writer": AgentRole.WRITER,
            "Historian": AgentRole.HISTORIAN,
            "Politics-Left": AgentRole.POLITICS_LEFT,
            "Politics-Right": AgentRole.POLITICS_RIGHT,
            "Geopolitics": AgentRole.GEOPOLITICS,
            "Chief Editor": AgentRole.EDITOR,
        }
        
        # Calculate review priorities for each memo
        for memo in memos:
            memo_id = UUID(memo["id"])
            source_agent = memo["agent_id"]
            source_role = agent_roles.get(source_agent)
            
            # Skip if no valid role
            if not source_role:
                continue
                
            reviewers = []
            
            # Find suitable reviewers based on priority table
            prioritized_reviewers = []
            for (s_role, r_role), priority in ReflectionConfig.REFLECTION_PRIORITIES.items():
                if s_role == source_role:
                    # Find agent with this role
                    for agent_name, role in agent_roles.items():
                        if role == r_role and agent_name != source_agent:
                            prioritized_reviewers.append((agent_name, priority))
            
            # Sort by priority (highest first)
            prioritized_reviewers.sort(key=lambda x: x[1], reverse=True)
            
            # Take the top N reviewers based on config
            num_reviewers = min(
                len(prioritized_reviewers),
                ReflectionConfig.MAX_REFLECTIONS_PER_MEMO
            )
            
            if num_reviewers >= ReflectionConfig.MIN_REFLECTIONS_PER_MEMO:
                # Use prioritized reviewers
                reviewers = [r[0] for r in prioritized_reviewers[:num_reviewers]]
            else:
                # Not enough prioritized reviewers, add other agents to reach minimum
                reviewers = [r[0] for r in prioritized_reviewers]
                
                # Add other agents (excluding source agent) until we reach minimum
                for agent_name in agent_roles:
                    if agent_name != source_agent and agent_name not in reviewers:
                        reviewers.append(agent_name)
                        if len(reviewers) >= ReflectionConfig.MIN_REFLECTIONS_PER_MEMO:
                            break
            
            # Store the plan for this memo
            plan[memo_id] = reviewers
            self._memo_reflection_counts[memo_id] = len(reviewers)
        
        self._reflection_plan = plan
        
        logger.info(
            "Created reflection plan with %d memos and %d total reflections",
            len(plan),
            sum(len(reviewers) for reviewers in plan.values()),
        )

    async def _request_planned_reflections(self) -> None:
        """Request reflections according to the plan."""
        for memo_id, reviewers in self._reflection_plan.items():
            # Get the memo content
            memo = await get_memo_by_id(memo_id)
            if not memo:
                logger.warning("Memo %s not found, skipping reflection requests", memo_id)
                continue
            
            memo_content = memo.get("content", "")
            source_agent = memo.get("agent_id", "Unknown")
            
            # Create appropriate prompt for each reviewer
            for reviewer in reviewers:
                prompt = (
                    f"Please provide a thorough reflection on this memo from {source_agent}. "
                    f"Assess its factual accuracy, bias, quality, and suggestions for improvement. "
                    f"Consider the article topic and your specialized expertise."
                )
                
                # Customize prompt based on reviewer role
                if reviewer == "Politics-Left" and source_agent == "Politics-Right":
                    prompt += " Pay particular attention to potential conservative bias."
                elif reviewer == "Politics-Right" and source_agent == "Politics-Left":
                    prompt += " Pay particular attention to potential progressive bias."
                elif reviewer == "Historian":
                    prompt += " Focus especially on historical accuracy and context."
                elif reviewer == "Geopolitics":
                    prompt += " Focus on international relations and cross-border implications."
                
                # Request reflection with priority based on reviewer
                priority = ReflectionPriority.MEDIUM
                
                # Set high priority for politically opposing viewpoints
                if (reviewer == "Politics-Left" and source_agent == "Politics-Right") or \
                   (reviewer == "Politics-Right" and source_agent == "Politics-Left"):
                    priority = ReflectionPriority.HIGH
                
                # Request the reflection
                reflection_id = await self.request_reflection(
                    memo_id=memo_id,
                    content=memo_content,
                    target_agent_id=reviewer,
                    prompt=prompt,
                    priority=priority,
                )
                
                self._pending_reflections.add(reflection_id)
                
                logger.info(
                    "Requested reflection from %s on memo %s (reflection_id: %s)",
                    reviewer,
                    memo_id,
                    reflection_id,
                )
    
    async def _finalize_reflection_phase(self) -> None:
        """Finalize the reflection phase and move to synthesis."""
        logger.info("Reflection phase complete for article %s", self.article_id)
        
        # Mark reflection phase as complete
        self._reflection_phase_complete = True
        
        # Update article status
        self.article_run.status = ArticleStatus.SYNTHESIZING
        self.article_run.metadata["reflection_complete"] = True
        save_article_run(self.article_run)
        
        # Process reflection results and synthesize final article
        await self._synthesize_article_with_reflections()

    async def _synthesize_article_with_reflections(self) -> None:
        """Synthesize the final article using reflection feedback."""
        # Gather all reflections
        reflections = self.article_run.metadata.get("reflections", {})
        
        # Process bias detection results
        article_bias = self._detect_overall_bias(reflections)
        
        if article_bias:
            # Log bias detection results
            logger.info(
                "Detected bias in article: %s",
                article_bias,
            )
            
            # Store bias results in article metadata
            self.article_run.metadata["bias_assessment"] = article_bias
            save_article_run(self.article_run)
        
        # TODO: Use LLM to incorporate reflection feedback into final article
        # This would involve:
        # 1. Summarizing key reflection points per memo
        # 2. Identifying improvements to make based on reflections
        # 3. Generating balanced article content
        # 4. Ensuring politically sensitive topics have fair coverage
        
        # For now, update the article status to complete
        self.article_run.status = ArticleStatus.COMPLETED
        save_article_run(self.article_run)
        
        logger.info("Article synthesis complete: %s", self.article_id)

    def _detect_overall_bias(self, reflections: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Detect overall bias in the article based on reflections.

        Args:
            reflections (Dict[str, List[Dict[str, Any]]]): Reflections by memo ID

        Returns:
            Dict[str, Any]: Bias assessment results
        """
        # This is a simplified bias detection implementation
        # A more comprehensive implementation would use NLP/ML techniques
        
        bias_indicators = {
            "left_biased_terms": 0,
            "right_biased_terms": 0,
            "neutral_terms": 0,
            "bias_by_agent": {},
        }
        
        for memo_id, memo_reflections in reflections.items():
            for reflection in memo_reflections:
                content = reflection.get("content", "")
                source_agent = reflection.get("source_agent_id", "")
                
                # Simple keyword analysis (would be more sophisticated in production)
                left_terms = ["progressive", "liberal", "left-leaning", "democrat"]
                right_terms = ["conservative", "republican", "right-leaning", "traditional"]
                neutral_terms = ["balanced", "neutral", "fair", "objective"]
                
                # Count mentions of bias terms
                bias_indicators["left_biased_terms"] += sum(content.lower().count(term) for term in left_terms)
                bias_indicators["right_biased_terms"] += sum(content.lower().count(term) for term in right_terms)
                bias_indicators["neutral_terms"] += sum(content.lower().count(term) for term in neutral_terms)
                
                # Track bias by agent
                if source_agent not in bias_indicators["bias_by_agent"]:
                    bias_indicators["bias_by_agent"][source_agent] = {
                        "reflections_given": 0,
                        "bias_mentions": 0,
                    }
                
                bias_indicators["bias_by_agent"][source_agent]["reflections_given"] += 1
                if "bias" in content.lower():
                    bias_indicators["bias_by_agent"][source_agent]["bias_mentions"] += 1
        
        # Calculate overall bias direction
        total_bias_terms = bias_indicators["left_biased_terms"] + bias_indicators["right_biased_terms"]
        if total_bias_terms > 0:
            bias_indicators["bias_ratio"] = bias_indicators["left_biased_terms"] / total_bias_terms
        else:
            bias_indicators["bias_ratio"] = 0.5  # Neutral
        
        # Produce human-readable assessment
        if bias_indicators["bias_ratio"] > 0.65:
            bias_indicators["assessment"] = "Left-leaning bias detected"
        elif bias_indicators["bias_ratio"] < 0.35:
            bias_indicators["assessment"] = "Right-leaning bias detected"
        else:
            bias_indicators["assessment"] = "Relatively balanced coverage"
        
        return bias_indicators

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
                    style_notes="Opening paragraph in Washington Post style",
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