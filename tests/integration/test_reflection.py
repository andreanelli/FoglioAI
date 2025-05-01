"""Integration tests for the agent reflection process."""
import asyncio
import uuid
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base import BaseAgent
from app.agents.editor import EditorAgent
from app.agents.orchestrator import ArticleOrchestrator, OrchestratorConfig
from app.models.agent import AgentRole
from app.models.article import Article
from app.models.article_run import ArticleRunStatus
from app.pubsub.scratchpad import (
    AgentScratchpad, 
    Message, 
    MessageType, 
    ReflectionPriority,
    ReflectionRequest,
    ReflectionStatus
)
from app.utils.article_balancer import ArticleBalancer
from app.utils.bias import BiasDetector, BiasLevel, BiasType


@pytest.fixture
def article_id():
    """Generate a test article ID."""
    return uuid.uuid4()


@pytest.fixture
def mock_article_run(article_id):
    """Create a mock article run for testing."""
    article_run = {
        "id": str(article_id),
        "status": ArticleRunStatus.PENDING,
        "user_query": "Analysis of the impact of climate change policies on the economy",
        "agent_outputs": {},
        "citations": [],
        "visuals": [],
        "errors": [],
        "metadata": {},
        "created_at": datetime.now(UTC),
    }
    return article_run


@pytest.fixture
def mock_article(article_id):
    """Create a mock article for testing."""
    return Article(
        id=article_id,
        topic="Analysis of the impact of climate change policies on the economy",
        outline=None,
        style_guide={"tone": "modern"},
        status="planning",
    )


@pytest.fixture
def mock_memos():
    """Create mock memos for testing."""
    return [
        {
            "id": str(uuid.uuid4()),
            "agent_id": "Researcher",
            "content": "Research findings on climate change policies: Studies indicate that transitioning to renewable energy could create 25 million jobs by 2030 while requiring significant investment. Critics argue that rapid implementation could cause economic disruption in fossil fuel-dependent regions.",
            "timestamp": datetime.now(UTC).timestamp(),
        },
        {
            "id": str(uuid.uuid4()),
            "agent_id": "Politics-Left",
            "content": "Progressive analysis: Climate change policy must prioritize environmental justice and worker protections. [BIAS-L] We should implement a Green New Deal with strong regulations on polluters and substantial government investment. The economic benefits of green technology far outweigh short-term costs, especially when considering the catastrophic consequences of inaction.",
            "timestamp": datetime.now(UTC).timestamp(),
        },
        {
            "id": str(uuid.uuid4()),
            "agent_id": "Politics-Right",
            "content": "Conservative analysis: Climate policies should prioritize market-based solutions and innovation rather than regulations. [BIAS-R] Carbon taxes and cap-and-trade systems may be more efficient than government mandates. We must ensure economic growth isn't sacrificed for environmental goals, as prosperity enables better environmental stewardship through technological advancement.",
            "timestamp": datetime.now(UTC).timestamp(),
        },
        {
            "id": str(uuid.uuid4()),
            "agent_id": "Geopolitics",
            "content": "International perspective: Climate policy has significant geopolitical implications. Countries implementing stricter regulations may face competitive disadvantages if others don't follow suit. The Paris Agreement attempts to coordinate global action while respecting varying economic capacities. Developing nations argue for greater responsibility from historically high-emission developed countries.",
            "timestamp": datetime.now(UTC).timestamp(),
        },
    ]


@pytest.fixture
def mock_reflections():
    """Create mock reflection responses."""
    return {
        "left_on_right": {
            "content": "The conservative analysis provides important market-based perspectives but underemphasizes the urgency of climate action and the need for regulatory frameworks to ensure emissions targets are met. The argument for technological advancement through prosperity has merit, but historical evidence suggests market forces alone are insufficient without policy direction.",
            "metadata": {"bias_score": 0.3, "quality": 0.8}
        },
        "right_on_left": {
            "content": "The progressive analysis correctly identifies environmental justice concerns but overstates the feasibility of rapid transition without economic disruption. The memo lacks specific cost-benefit analysis and assumes government investment will automatically yield optimal outcomes without addressing efficiency concerns or potential unintended consequences.",
            "metadata": {"bias_score": -0.4, "quality": 0.8}
        },
        "editor_synthesis": {
            "content": "Both political perspectives offer valid insights. The progressive view correctly emphasizes urgency and justice considerations, while the conservative view highlights economic efficiency and innovation. A balanced approach would combine market incentives with targeted regulations, ensuring both environmental protection and economic adaptation. International coordination remains essential regardless of domestic policy choices."
        }
    }


@pytest.mark.asyncio
async def test_end_to_end_reflection_process(article_id, mock_article_run, mock_article, mock_memos, mock_reflections):
    """Test the complete reflection process from memo generation to synthesis."""
    # Mock dependencies
    with patch("app.agents.orchestrator.get_article_run", return_value=mock_article_run), \
         patch("app.agents.orchestrator.save_article_run"), \
         patch("app.agents.base.agent_scratchpad") as mock_scratchpad, \
         patch("app.agents.base.get_memo_by_id") as mock_get_memo, \
         patch("app.agents.editor.get_memos_by_article") as mock_get_memos, \
         patch("app.utils.article_balancer.get_memos_by_article") as mock_balancer_get_memos, \
         patch("app.agents.base.Mistral") as mock_mistral, \
         patch("app.agents.orchestrator.ArticleOrchestrator._initialize_agents"):
        
        # Configure mocks
        mock_scratchpad.publish_message = AsyncMock()
        mock_scratchpad.request_reflection = AsyncMock(return_value=uuid.uuid4())
        mock_scratchpad.submit_reflection = AsyncMock()
        mock_scratchpad.get_pending_reflections = AsyncMock(return_value=[])
        
        mock_get_memo.side_effect = lambda memo_id: next(
            (memo for memo in mock_memos if memo["id"] == memo_id), None
        )
        
        mock_get_memos.return_value = mock_memos
        mock_balancer_get_memos.return_value = mock_memos
        
        # Mock Mistral responses for reflections
        mock_chat_completion = AsyncMock()
        mock_chat_completion.content = "Reflection content"
        mock_mistral.return_value.chat.completions.create = AsyncMock(return_value=mock_chat_completion)
        
        # Initialize orchestrator
        orchestrator = ArticleOrchestrator(article_id)
        
        # Mock agent initialization
        orchestrator._initialize_agents = MagicMock()
        orchestrator.agent_map = {
            "Chief Editor": MagicMock(spec=EditorAgent),
            "Researcher": MagicMock(spec=BaseAgent),
            "Writer": MagicMock(spec=BaseAgent),
            "Politics-Left": MagicMock(spec=BaseAgent),
            "Politics-Right": MagicMock(spec=BaseAgent),
            "Geopolitics": MagicMock(spec=BaseAgent),
            "Historian": MagicMock(spec=BaseAgent),
        }
        
        # Mock the reflection phase execution
        editor = orchestrator.agent_map["Chief Editor"]
        editor._start_reflection_phase = AsyncMock()
        editor._check_reflection_complete = MagicMock(return_value=True)
        editor._finalize_reflection_phase = AsyncMock()
        editor.synthesize_article_with_reflections = AsyncMock(return_value="Balanced final article content")
        
        # Set up the reflection plan in the editor
        left_memo = next(memo for memo in mock_memos if memo["agent_id"] == "Politics-Left")
        right_memo = next(memo for memo in mock_memos if memo["agent_id"] == "Politics-Right")
        
        editor._reflection_plan = {
            uuid.UUID(left_memo["id"]): ["Politics-Right"],
            uuid.UUID(right_memo["id"]): ["Politics-Left"],
        }
        
        # Create mock reflection requests for testing
        reflection_requests = [
            ReflectionRequest(
                reflection_id=uuid.uuid4(),
                article_id=article_id,
                memo_id=uuid.UUID(left_memo["id"]),
                source_agent_id="Chief Editor",
                target_agent_id="Politics-Right",
                content=left_memo["content"],
                prompt="Analyze this memo for political bias and provide a balanced perspective.",
            ),
            ReflectionRequest(
                reflection_id=uuid.uuid4(),
                article_id=article_id,
                memo_id=uuid.UUID(right_memo["id"]),
                source_agent_id="Chief Editor",
                target_agent_id="Politics-Left",
                content=right_memo["content"],
                prompt="Analyze this memo for political bias and provide a balanced perspective.",
            ),
        ]
        
        # 1. Simulate drafting phase completion
        mock_article_run["agent_outputs"] = {
            "Researcher": {"memo": mock_memos[0]["content"]},
            "Politics-Left": {"memo": mock_memos[1]["content"]},
            "Politics-Right": {"memo": mock_memos[2]["content"]},
            "Geopolitics": {"memo": mock_memos[3]["content"]},
        }
        mock_article_run["status"] = ArticleRunStatus.DRAFTING
        
        # 2. Test transition to reflection phase
        await orchestrator._handle_drafting_complete()
        
        # Verify the reflection phase was started
        editor._start_reflection_phase.assert_called_once()
        
        # 3. Simulate reflection responses
        # Mock the reflection feedback handling in the editor
        def mock_handle_reflection(message_type, message):
            if message_type == MessageType.REFLECTION_RESPONSE:
                if message.content.get("memo_id") == left_memo["id"]:
                    return mock_reflections["right_on_left"]["content"]
                else:
                    return mock_reflections["left_on_right"]["content"]
            return None
        
        editor._handle_reflection_response = MagicMock(side_effect=mock_handle_reflection)
        
        # Simulate the completion of reflections
        for request in reflection_requests:
            response_message = Message(
                type=MessageType.REFLECTION_RESPONSE,
                agent_id=request.target_agent_id,
                article_id=article_id,
                reflection_id=request.reflection_id,
                content={
                    "memo_id": str(request.memo_id),
                    "reflection": mock_reflections["right_on_left"]["content"] if request.target_agent_id == "Politics-Left" else mock_reflections["left_on_right"]["content"],
                },
                metadata=mock_reflections["right_on_left"]["metadata"] if request.target_agent_id == "Politics-Left" else mock_reflections["left_on_right"]["metadata"],
            )
            orchestrator._message_handlers[MessageType.REFLECTION_RESPONSE](response_message)
        
        # 4. Test transition to synthesis phase
        
        # Mock the bias detection and balancing
        with patch("app.utils.article_balancer.BiasDetector") as mock_detector, \
             patch("app.utils.article_balancer.BiasBalancer") as mock_balancer:
            
            # Set up bias detection
            detector_instance = MagicMock()
            detector_instance.detect_bias.return_value = MagicMock(
                bias_level=BiasLevel.MODERATE,
                bias_direction=0.0,  # Balanced
                primary_bias_types=[BiasType.NEUTRAL],
                summary="Balanced content with diverse perspectives."
            )
            mock_detector.return_value = detector_instance
            
            # Set up bias analysis
            mock_balancer.calculate_article_bias.return_value = {
                "overall_bias_direction": 0.0,
                "overall_bias_level": BiasLevel.MODERATE.value,
                "bias_by_type": {},
                "bias_by_memo": {},
                "summary": "The article has a good balance of perspectives."
            }
            
            mock_balancer.generate_balance_recommendations.return_value = {
                "needs_balancing": False,
                "recommendations": ["The content is already well-balanced."],
            }
            
            # Set article status to reflecting
            mock_article_run["status"] = ArticleRunStatus.REFLECTING
            
            # Call the handle_reflection_complete method
            await orchestrator._handle_reflection_complete()
            
            # Verify the reflection phase was finalized
            editor._finalize_reflection_phase.assert_called_once()
            
            # Verify article synthesis was called
            editor.synthesize_article_with_reflections.assert_called_once()
            
            # Verify the final content was added to the article run
            assert "Chief Editor" in mock_article_run["agent_outputs"]
            
            # Verify the article status was updated
            assert mock_article_run["status"] == ArticleRunStatus.COMPLETED


@pytest.mark.asyncio
async def test_bias_detection_in_reflection_process(article_id, mock_article_run, mock_memos):
    """Test that bias detection and balancing is properly applied during the reflection process."""
    # Create a real BiasDetector to test with actual content
    bias_detector = BiasDetector()
    
    # Test the Politics-Left memo for bias
    politics_left_memo = next(memo for memo in mock_memos if memo["agent_id"] == "Politics-Left")
    left_result = bias_detector.detect_bias(politics_left_memo["content"])
    
    # Verify progressive bias is detected
    assert left_result.bias_level in [BiasLevel.MODERATE, BiasLevel.STRONG]
    assert BiasType.POLITICAL_LEFT in left_result.primary_bias_types or BiasType.ECONOMIC_PROGRESSIVE in left_result.primary_bias_types
    assert left_result.bias_direction > 0  # Positive = progressive
    assert left_result.bias_markers[BiasType.POLITICAL_LEFT] == 1  # Should detect the [BIAS-L] marker
    
    # Test the Politics-Right memo for bias
    politics_right_memo = next(memo for memo in mock_memos if memo["agent_id"] == "Politics-Right")
    right_result = bias_detector.detect_bias(politics_right_memo["content"])
    
    # Verify conservative bias is detected
    assert right_result.bias_level in [BiasLevel.MODERATE, BiasLevel.STRONG]
    assert BiasType.POLITICAL_RIGHT in right_result.primary_bias_types or BiasType.ECONOMIC_CONSERVATIVE in right_result.primary_bias_types
    assert right_result.bias_direction < 0  # Negative = conservative
    assert right_result.bias_markers[BiasType.POLITICAL_RIGHT] == 1  # Should detect the [BIAS-R] marker
    
    # Test the ArticleBalancer with the memos
    with patch("app.utils.article_balancer.get_memos_by_article", return_value=mock_memos):
        balancer = ArticleBalancer(article_id)
        bias_analysis = await balancer.analyze_article_bias()
        
        # Verify the analysis contains the expected structure
        assert "overall_bias_direction" in bias_analysis
        assert "overall_bias_level" in bias_analysis
        assert "bias_by_type" in bias_analysis
        assert "bias_by_memo" in bias_analysis
        assert "recommendations" in bias_analysis
        
        # Verify that recommendations are generated
        assert len(bias_analysis["recommendations"]) > 0
        
        # Test balanced content generation
        content = await balancer.generate_balanced_content(mock_memos, bias_analysis)
        
        # Verify that all perspectives are included
        assert "Research findings" in content
        assert "Progressive analysis" in content
        assert "Conservative analysis" in content
        assert "International perspective" in content


@pytest.mark.asyncio
async def test_reflection_quality_impact(article_id, mock_article_run, mock_article, mock_memos, mock_reflections):
    """Test how the quality of reflections impacts the final article."""
    # Mock dependencies
    with patch("app.agents.orchestrator.get_article_run", return_value=mock_article_run), \
         patch("app.agents.orchestrator.save_article_run"), \
         patch("app.agents.base.agent_scratchpad") as mock_scratchpad, \
         patch("app.agents.editor.get_memos_by_article") as mock_get_memos, \
         patch("app.utils.article_balancer.get_memos_by_article") as mock_balancer_get_memos, \
         patch("app.agents.orchestrator.ArticleOrchestrator._initialize_agents"):
        
        # Configure mocks
        mock_scratchpad.publish_message = AsyncMock()
        mock_get_memos.return_value = mock_memos
        mock_balancer_get_memos.return_value = mock_memos
        
        # Initialize orchestrator
        orchestrator = ArticleOrchestrator(article_id)
        
        # Mock agent initialization
        orchestrator._initialize_agents = MagicMock()
        orchestrator.agent_map = {
            "Chief Editor": MagicMock(spec=EditorAgent),
            "Researcher": MagicMock(spec=BaseAgent),
            "Writer": MagicMock(spec=BaseAgent),
            "Politics-Left": MagicMock(spec=BaseAgent),
            "Politics-Right": MagicMock(spec=BaseAgent),
            "Geopolitics": MagicMock(spec=BaseAgent),
            "Historian": MagicMock(spec=BaseAgent),
        }
        
        # Create reflections with different quality scores
        high_quality_reflection = {
            "content": "High quality reflection with specific critiques and balanced analysis...",
            "metadata": {"bias_score": 0.1, "quality": 0.9}
        }
        
        low_quality_reflection = {
            "content": "Poor quality reflection with vague statements...",
            "metadata": {"bias_score": 0.1, "quality": 0.3}
        }
        
        # Get the editor agent
        editor = orchestrator.agent_map["Chief Editor"]
        
        # Mock editor methods to test reflection quality handling
        editor._reflection_quality_threshold = 0.6
        editor._get_reflection_quality = MagicMock()
        editor._incorporate_reflection = MagicMock()
        
        # Test with high quality reflection
        high_quality_message = Message(
            type=MessageType.REFLECTION_RESPONSE,
            agent_id="Politics-Right",
            article_id=article_id,
            reflection_id=uuid.uuid4(),
            content={
                "memo_id": mock_memos[1]["id"],  # Politics-Left memo
                "reflection": high_quality_reflection["content"],
            },
            metadata=high_quality_reflection["metadata"],
        )
        
        editor._get_reflection_quality.return_value = high_quality_reflection["metadata"]["quality"]
        
        # Mock handle reflection response
        if hasattr(editor, "_handle_reflection_response"):
            editor._handle_reflection_response = MagicMock()
            editor._handle_reflection_response(high_quality_message)
            editor._incorporate_reflection.assert_called_once()
        
        # Reset mocks
        editor._incorporate_reflection.reset_mock()
        
        # Test with low quality reflection
        low_quality_message = Message(
            type=MessageType.REFLECTION_RESPONSE,
            agent_id="Politics-Left",
            article_id=article_id,
            reflection_id=uuid.uuid4(),
            content={
                "memo_id": mock_memos[2]["id"],  # Politics-Right memo
                "reflection": low_quality_reflection["content"],
            },
            metadata=low_quality_reflection["metadata"],
        )
        
        editor._get_reflection_quality.return_value = low_quality_reflection["metadata"]["quality"]
        
        # Mock handle reflection response
        if hasattr(editor, "_handle_reflection_response"):
            editor._handle_reflection_response(low_quality_message)
            # Should not incorporate low quality reflection
            editor._incorporate_reflection.assert_not_called() 