"""Tests for article balancer utilities."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utils.article_balancer import ArticleBalancer
from app.utils.bias import BiasDetectionResult, BiasLevel, BiasType


@pytest.fixture
def bias_detector_mock():
    """Mock the BiasDetector class."""
    with patch("app.utils.article_balancer.BiasDetector") as mock:
        detector_instance = MagicMock()
        mock.return_value = detector_instance
        yield detector_instance


@pytest.fixture
def bias_balancer_mock():
    """Mock the BiasBalancer class."""
    with patch("app.utils.article_balancer.BiasBalancer") as mock:
        mock.calculate_article_bias = MagicMock()
        mock.generate_balance_recommendations = MagicMock()
        yield mock


@pytest.fixture
def get_memos_mock():
    """Mock the get_memos_by_article function."""
    with patch("app.utils.article_balancer.get_memos_by_article") as mock:
        # Default to return empty list
        mock.return_value = []
        yield mock


@pytest.fixture
def article_balancer(bias_detector_mock, get_memos_mock):
    """Create an ArticleBalancer instance for testing."""
    article_id = uuid.uuid4()
    return ArticleBalancer(article_id)


@pytest.mark.asyncio
async def test_analyze_article_bias_no_memos(article_balancer, get_memos_mock):
    """Test analyzing article bias when no memos are found."""
    get_memos_mock.return_value = []
    
    result = await article_balancer.analyze_article_bias()
    
    # Check structure of result
    assert "overall_bias_direction" in result
    assert "overall_bias_level" in result
    assert "bias_by_type" in result
    assert "bias_by_memo" in result
    assert "summary" in result
    assert "recommendations" in result
    
    # Check default values for empty set
    assert result["overall_bias_direction"] == 0.0
    assert result["overall_bias_level"] == "none"
    assert result["bias_by_type"] == {}
    assert result["bias_by_memo"] == {}
    assert "No memos" in result["summary"]
    assert "No memos" in result["recommendations"][0]


@pytest.mark.asyncio
async def test_analyze_article_bias_with_memos(article_balancer, get_memos_mock, bias_detector_mock, bias_balancer_mock):
    """Test analyzing article bias with memos."""
    # Set up mock memos
    memo1 = {"id": str(uuid.uuid4()), "content": "Test memo 1", "agent_id": "Politics-Left"}
    memo2 = {"id": str(uuid.uuid4()), "content": "Test memo 2", "agent_id": "Politics-Right"}
    get_memos_mock.return_value = [memo1, memo2]
    
    # Set up mock bias detection results
    result1 = MagicMock(spec=BiasDetectionResult)
    result1.bias_level = BiasLevel.MODERATE
    result1.bias_direction = 0.7
    result1.to_dict.return_value = {"bias_level": "moderate", "bias_direction": 0.7}
    
    result2 = MagicMock(spec=BiasDetectionResult)
    result2.bias_level = BiasLevel.MODERATE
    result2.bias_direction = -0.7
    result2.to_dict.return_value = {"bias_level": "moderate", "bias_direction": -0.7}
    
    bias_detector_mock.detect_bias.side_effect = [result1, result2]
    
    # Set up mock article bias and recommendations
    article_bias = {
        "overall_bias_direction": 0.0,  # Balanced
        "overall_bias_level": "moderate",
        "bias_by_type": {
            "political_left": 0.7,
            "political_right": 0.7,
        },
        "bias_by_memo": {
            memo1["id"]: {"bias_direction": 0.7, "bias_level": "moderate"},
            memo2["id"]: {"bias_direction": -0.7, "bias_level": "moderate"},
        },
        "summary": "The article shows moderate bias with a balanced orientation."
    }
    
    recommendations = {
        "needs_balancing": True,
        "recommendations": ["Ensure fair representation of perspectives."],
        "memo_specific_recommendations": {
            memo1["id"]: ["Consider adding conservative viewpoints."],
            memo2["id"]: ["Consider adding progressive viewpoints."],
        },
    }
    
    bias_balancer_mock.calculate_article_bias.return_value = article_bias
    bias_balancer_mock.generate_balance_recommendations.return_value = recommendations
    
    # Call the function
    result = await article_balancer.analyze_article_bias()
    
    # Verify correct function calls
    get_memos_mock.assert_called_once()
    bias_detector_mock.detect_bias.assert_called()
    assert bias_detector_mock.detect_bias.call_count == 2
    bias_balancer_mock.calculate_article_bias.assert_called_once()
    bias_balancer_mock.generate_balance_recommendations.assert_called_once()
    
    # Check result is a combination of article_bias and recommendations
    assert result["overall_bias_direction"] == 0.0
    assert result["overall_bias_level"] == "moderate"
    assert "political_left" in result["bias_by_type"]
    assert "political_right" in result["bias_by_type"]
    assert memo1["id"] in result["bias_by_memo"]
    assert memo2["id"] in result["bias_by_memo"]
    assert "The article shows moderate bias" in result["summary"]
    assert result["needs_balancing"] is True
    assert "Ensure fair representation" in result["recommendations"][0]
    assert memo1["id"] in result["memo_specific_recommendations"]
    assert memo2["id"] in result["memo_specific_recommendations"]


@pytest.mark.asyncio
async def test_generate_balanced_content_no_memos(article_balancer):
    """Test generating balanced content with no memos."""
    memos = []
    bias_analysis = {
        "overall_bias_direction": 0.0,
        "overall_bias_level": "none",
        "needs_balancing": False,
    }
    
    result = await article_balancer.generate_balanced_content(memos, bias_analysis)
    
    assert "No content available" in result


@pytest.mark.asyncio
async def test_generate_balanced_content_with_memos(article_balancer):
    """Test generating balanced content with memos."""
    # Create mock memos
    writer_intro = {
        "agent_id": "Writer",
        "content": "Introduction to the article\n\nThis is the introduction paragraph that sets the stage."
    }
    
    politics_left = {
        "agent_id": "Politics-Left",
        "content": "Progressive perspective\n\nFrom a progressive standpoint, this issue represents..."
    }
    
    politics_right = {
        "agent_id": "Politics-Right",
        "content": "Conservative perspective\n\nFrom a conservative viewpoint, we must consider..."
    }
    
    researcher = {
        "agent_id": "Researcher",
        "content": "Research findings\n\nThe data indicates several key trends..."
    }
    
    writer_conclusion = {
        "agent_id": "Writer",
        "content": "Conclusion\n\nIn conclusion, the evidence suggests..."
    }
    
    memos = [writer_intro, politics_left, politics_right, researcher, writer_conclusion]
    
    # Test with balanced content (no bias)
    balanced_bias = {
        "overall_bias_direction": 0.0,
        "overall_bias_level": "none",
        "needs_balancing": False,
    }
    
    result = await article_balancer.generate_balanced_content(memos, balanced_bias)
    
    # Should include content from all memos
    assert "Introduction to the article" in result
    assert "Progressive perspective" in result
    assert "Conservative perspective" in result
    assert "Research findings" in result
    assert "In conclusion" in result
    
    # Test with progressive bias
    progressive_bias = {
        "overall_bias_direction": 0.7,
        "overall_bias_level": "strong",
        "needs_balancing": True,
    }
    
    # Set up a mock for _calculate_agent_weights
    with patch.object(article_balancer, '_calculate_agent_weights') as mock_weights:
        # Prioritize conservative sources
        mock_weights.return_value = {
            "Writer": 1.0,
            "Researcher": 0.9,
            "Politics-Right": 0.9,  # Higher weight for conservative
            "Politics-Left": 0.4,   # Lower weight for progressive
        }
        
        result = await article_balancer.generate_balanced_content(memos, progressive_bias)
        
        # Conservative content should come before progressive
        conservative_pos = result.find("Conservative perspective")
        progressive_pos = result.find("Progressive perspective")
        
        if progressive_pos != -1 and conservative_pos != -1:
            assert conservative_pos < progressive_pos
    
    # Test with conservative bias
    conservative_bias = {
        "overall_bias_direction": -0.7,
        "overall_bias_level": "strong",
        "needs_balancing": True,
    }
    
    # Set up a mock for _calculate_agent_weights
    with patch.object(article_balancer, '_calculate_agent_weights') as mock_weights:
        # Prioritize progressive sources
        mock_weights.return_value = {
            "Writer": 1.0,
            "Researcher": 0.9,
            "Politics-Left": 0.9,   # Higher weight for progressive
            "Politics-Right": 0.4,  # Lower weight for conservative
        }
        
        result = await article_balancer.generate_balanced_content(memos, conservative_bias)
        
        # Progressive content should come before conservative
        conservative_pos = result.find("Conservative perspective")
        progressive_pos = result.find("Progressive perspective")
        
        if progressive_pos != -1 and conservative_pos != -1:
            assert progressive_pos < conservative_pos


def test_calculate_agent_weights(article_balancer):
    """Test calculating agent weights based on bias direction and level."""
    # Test with no bias
    weights = article_balancer._calculate_agent_weights(0.0, "none")
    assert "Writer" in weights
    assert "Researcher" in weights
    assert "Politics-Left" in weights
    assert "Politics-Right" in weights
    assert weights["Politics-Left"] == weights["Politics-Right"]  # Equal weight
    
    # Test with progressive bias
    weights = article_balancer._calculate_agent_weights(0.7, "strong")
    assert weights["Politics-Left"] < weights["Politics-Right"]  # Conservative weighted higher
    assert weights["Researcher"] >= 0.9  # Factual sources boosted
    
    # Test with conservative bias
    weights = article_balancer._calculate_agent_weights(-0.7, "strong")
    assert weights["Politics-Right"] < weights["Politics-Left"]  # Progressive weighted higher
    assert weights["Researcher"] >= 0.9  # Factual sources boosted


@pytest.mark.asyncio
async def test_generate_reflection_prompts_no_balancing():
    """Test generating reflection prompts when no balancing is needed."""
    bias_analysis = {
        "needs_balancing": False,
        "bias_by_memo": {},
        "memo_specific_recommendations": {},
    }
    
    result = await ArticleBalancer.generate_reflection_prompts(bias_analysis)
    
    assert result == {}  # No prompts when no balancing needed


@pytest.mark.asyncio
async def test_generate_reflection_prompts_with_bias():
    """Test generating reflection prompts when balancing is needed."""
    memo1_id = str(uuid.uuid4())
    memo2_id = str(uuid.uuid4())
    
    bias_analysis = {
        "needs_balancing": True,
        "bias_by_memo": {
            memo1_id: {
                "bias_direction": 0.8,  # Progressive bias
                "bias_level": "strong",
                "primary_bias_types": ["political_left", "economic_progressive"],
            },
            memo2_id: {
                "bias_direction": -0.8,  # Conservative bias
                "bias_level": "strong",
                "primary_bias_types": ["political_right", "economic_conservative"],
            },
        },
        "memo_specific_recommendations": {
            memo1_id: ["This memo has strong progressive bias."],
            memo2_id: ["This memo has strong conservative bias."],
        },
    }
    
    result = await ArticleBalancer.generate_reflection_prompts(bias_analysis)
    
    # Should have prompts for both memos
    assert len(result) == 2
    assert UUID(memo1_id) in result
    assert UUID(memo2_id) in result
    
    # Progressive memo should have Politics-Right reviewer
    memo1_prompts = result[UUID(memo1_id)]
    assert any(p["target_agent_id"] == "Politics-Right" for p in memo1_prompts)
    
    # Conservative memo should have Politics-Left reviewer
    memo2_prompts = result[UUID(memo2_id)]
    assert any(p["target_agent_id"] == "Politics-Left" for p in memo2_prompts)
    
    # All memos should have Researcher and Editor reviewers
    assert any(p["target_agent_id"] == "Researcher" for p in memo1_prompts)
    assert any(p["target_agent_id"] == "Researcher" for p in memo2_prompts)
    assert any(p["target_agent_id"] == "Chief Editor" for p in memo1_prompts)
    assert any(p["target_agent_id"] == "Chief Editor" for p in memo2_prompts) 