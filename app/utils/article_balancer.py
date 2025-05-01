"""Utilities for balancing article bias during generation."""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from app.models.agent import AgentRole
from app.models.article import Article
from app.models.article_run import ArticleRun
from app.pubsub.scratchpad import Message, MessageType
from app.storage.memos import get_memo_by_id, get_memos_by_article
from app.utils.bias import BiasBalancer, BiasDetector

logger = logging.getLogger(__name__)


class ArticleBalancer:
    """Utility for balancing bias in article content during generation."""

    def __init__(self, article_id: UUID):
        """Initialize the article balancer.

        Args:
            article_id (UUID): ID of the article being balanced
        """
        self.article_id = article_id
        self.bias_detector = BiasDetector()

    async def analyze_article_bias(self) -> Dict[str, Any]:
        """Analyze the bias in all memos for this article.

        Returns:
            Dict[str, Any]: Bias analysis results
        """
        # Get all memos for this article
        memos = await get_memos_by_article(self.article_id)
        
        if not memos:
            logger.warning(f"No memos found for article {self.article_id}")
            return {
                "overall_bias_direction": 0.0,
                "overall_bias_level": "none",
                "bias_by_type": {},
                "bias_by_memo": {},
                "summary": "No memos to analyze for bias.",
                "recommendations": ["No memos available for bias analysis."],
            }
        
        # Analyze bias in each memo
        memo_bias_results = {}
        for memo in memos:
            memo_id = UUID(memo["id"])
            memo_text = memo["content"]
            agent_id = memo["agent_id"]
            
            # Detect bias in the memo
            bias_result = self.bias_detector.detect_bias(memo_text)
            
            # Store results
            memo_bias_results[str(memo_id)] = bias_result
            
            logger.info(
                f"Bias analysis for memo {memo_id} (agent: {agent_id}): "
                f"level={bias_result.bias_level.value}, "
                f"direction={bias_result.bias_direction:.2f}"
            )
        
        # Calculate overall article bias
        article_bias = BiasBalancer.calculate_article_bias(memo_bias_results)
        
        # Generate balance recommendations
        recommendations = BiasBalancer.generate_balance_recommendations(article_bias)
        
        # Combine all results
        result = {
            **article_bias,
            **recommendations,
        }
        
        return result

    async def generate_balanced_content(
        self, memos: List[Dict[str, Any]], bias_analysis: Dict[str, Any]
    ) -> str:
        """Generate balanced content for the article based on bias analysis.

        Args:
            memos (List[Dict[str, Any]]): Memos to use for content generation
            bias_analysis (Dict[str, Any]): Bias analysis results

        Returns:
            str: Balanced article content
        """
        if not memos:
            return "No content available to generate the article."
        
        # Extract key information
        bias_direction = bias_analysis.get("overall_bias_direction", 0.0)
        bias_level = bias_analysis.get("overall_bias_level", "none")
        needs_balancing = bias_analysis.get("needs_balancing", False)
        
        # Basic balancing strategy - sort memos by agent role with priority
        # given to whichever agents would balance the bias
        memos_by_agent = {}
        for memo in memos:
            agent_id = memo["agent_id"]
            if agent_id not in memos_by_agent:
                memos_by_agent[agent_id] = []
            memos_by_agent[agent_id].append(memo)
        
        # Define agent weights based on bias direction
        agent_weights = self._calculate_agent_weights(bias_direction, bias_level)
        
        # Sort memos by agent weight (higher weight first)
        sorted_memos = []
        for agent_id, weight in sorted(agent_weights.items(), key=lambda x: x[1], reverse=True):
            if agent_id in memos_by_agent:
                sorted_memos.extend(memos_by_agent[agent_id])
        
        # Add any remaining memos
        for agent_id, agent_memos in memos_by_agent.items():
            if agent_id not in agent_weights:
                sorted_memos.extend(agent_memos)
        
        # Extract content and assemble article
        article_parts = []
        
        # Introduction (if available from Writer)
        intro_memo = next((m for m in memos if m["agent_id"] == "Writer" and "introduction" in m["content"].lower()), None)
        if intro_memo:
            article_parts.append(intro_memo["content"])
        
        # Main content from all relevant memos
        for memo in sorted_memos:
            # Skip intro memo which we already included
            if memo is intro_memo:
                continue
                
            # Skip very low-weight agents if we have enough content
            agent_id = memo["agent_id"]
            if needs_balancing and agent_id in agent_weights and agent_weights[agent_id] < 0.3:
                if len(article_parts) >= 3:  # Already have enough content
                    continue
            
            # Extract most relevant parts from the memo
            memo_content = memo["content"]
            
            # Simple heuristic: extract paragraphs that don't appear to be planning or notes
            paragraphs = [p.strip() for p in memo_content.split("\n\n") if p.strip()]
            content_paragraphs = [p for p in paragraphs 
                                 if not p.startswith("Note:") 
                                 and not p.startswith("#") 
                                 and not p.startswith("*")
                                 and len(p) > 50]
            
            if content_paragraphs:
                article_parts.append("\n\n".join(content_paragraphs[:3]))  # Limit to first 3 paragraphs
        
        # Conclusion (if available from Writer)
        conclusion_memo = next((m for m in memos if m["agent_id"] == "Writer" and "conclusion" in m["content"].lower()), None)
        if conclusion_memo:
            article_parts.append(conclusion_memo["content"])
        
        # Combine all parts
        article_content = "\n\n".join(article_parts)
        
        return article_content

    def _calculate_agent_weights(self, bias_direction: float, bias_level: str) -> Dict[str, float]:
        """Calculate weights for each agent based on bias analysis.

        Args:
            bias_direction (float): Overall bias direction (-1.0 to 1.0)
            bias_level (str): Overall bias level

        Returns:
            Dict[str, float]: Agent weights (0.0 to 1.0)
        """
        # Default weights (unbiased)
        weights = {
            "Writer": 1.0,
            "Researcher": 0.9,
            "Historian": 0.8,
            "Politics-Left": 0.7,
            "Politics-Right": 0.7,
            "Geopolitics": 0.6,
            "Chief Editor": 0.8,
        }
        
        # Adjust weights based on bias level and direction
        if bias_level in ["moderate", "strong", "extreme"]:
            # For progressive bias (positive direction)
            if bias_direction > 0.2:
                # Reduce progressive sources, boost conservative ones
                weights["Politics-Left"] = max(0.3, 1.0 - abs(bias_direction))
                weights["Politics-Right"] = min(1.0, 0.7 + abs(bias_direction))
                
                # Adjust economic and social agents based on more specific bias types
                # (would need more detailed bias analysis to do this properly)
                
            # For conservative bias (negative direction)
            elif bias_direction < -0.2:
                # Reduce conservative sources, boost progressive ones
                weights["Politics-Right"] = max(0.3, 1.0 - abs(bias_direction))
                weights["Politics-Left"] = min(1.0, 0.7 + abs(bias_direction))
            
            # Always boost factual sources for any bias
            weights["Researcher"] = min(1.0, weights["Researcher"] + 0.1)
            weights["Historian"] = min(1.0, weights["Historian"] + 0.1)
            
        return weights

    @staticmethod
    async def generate_reflection_prompts(
        bias_analysis: Dict[str, Any]
    ) -> Dict[UUID, List[Dict[str, Any]]]:
        """Generate reflection prompts based on bias analysis.

        Args:
            bias_analysis (Dict[str, Any]): Bias analysis results

        Returns:
            Dict[UUID, List[Dict[str, Any]]]: Reflection prompts by memo ID
        """
        if not bias_analysis.get("needs_balancing", False):
            return {}  # No reflections needed
            
        reflection_prompts = {}
        memo_specific = bias_analysis.get("memo_specific_recommendations", {})
        bias_by_memo = bias_analysis.get("bias_by_memo", {})
        
        # For each memo with bias concerns
        for memo_id_str, recommendations in memo_specific.items():
            memo_id = UUID(memo_id_str)
            memo_bias = bias_by_memo.get(memo_id_str, {})
            
            # Create prompts for that memo
            prompts = []
            
            # Get primary bias types
            bias_types = memo_bias.get("primary_bias_types", [])
            
            # Create a tailored reflection prompt
            if "progressive" in str(bias_types) or memo_bias.get("bias_direction", 0) > 0.5:
                # Progressive bias - ask Politics-Right for reflection
                prompts.append({
                    "target_agent_id": "Politics-Right",
                    "prompt": (
                        "Please provide a thorough critique of this memo from a conservative perspective. "
                        "Identify instances of progressive bias, and suggest ways to balance the content "
                        "with more conservative viewpoints. Focus on factual accuracy and balance."
                    ),
                })
            elif "conservative" in str(bias_types) or memo_bias.get("bias_direction", 0) < -0.5:
                # Conservative bias - ask Politics-Left for reflection
                prompts.append({
                    "target_agent_id": "Politics-Left",
                    "prompt": (
                        "Please provide a thorough critique of this memo from a progressive perspective. "
                        "Identify instances of conservative bias, and suggest ways to balance the content "
                        "with more progressive viewpoints. Focus on factual accuracy and balance."
                    ),
                })
            
            # Add Researcher for fact-checking
            prompts.append({
                "target_agent_id": "Researcher",
                "prompt": (
                    "Please fact-check the claims in this memo and identify any instances of bias. "
                    "Flag any statements that need additional sources or appear to present opinion as fact. "
                    "Suggest improvements to make the content more balanced and accurate."
                ),
            })
            
            # Add Editor for general feedback
            prompts.append({
                "target_agent_id": "Chief Editor",
                "prompt": (
                    "Please review this memo for journalistic quality and bias. "
                    "Evaluate whether it meets the standards of a balanced Washington Post article. "
                    "Suggest specific edits to improve balance, clarity, and adherence to "
                    "journalistic best practices."
                ),
            })
            
            reflection_prompts[memo_id] = prompts
            
        return reflection_prompts 