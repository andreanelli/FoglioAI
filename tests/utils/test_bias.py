"""Tests for bias detection and analysis utilities."""
import uuid
from unittest.mock import patch

import pytest

from app.utils.bias import (
    BiasBalancer,
    BiasConfig,
    BiasDetectionResult,
    BiasDetector,
    BiasLevel,
    BiasType,
)


class TestBiasDetector:
    """Tests for the BiasDetector class."""

    @pytest.fixture
    def bias_detector(self):
        """Create a BiasDetector instance for testing."""
        return BiasDetector()

    def test_detect_politically_neutral_text(self, bias_detector):
        """Test detection of politically neutral text."""
        text = """
        Today's weather forecast indicates a high of 75 degrees with partly cloudy skies.
        Expect light winds from the northwest and a 20% chance of precipitation in the evening.
        Tomorrow will bring similar conditions with slightly cooler temperatures.
        """
        
        result = bias_detector.detect_bias(text)
        
        # Check structure of result
        assert isinstance(result, BiasDetectionResult)
        assert hasattr(result, "bias_scores")
        assert hasattr(result, "bias_markers")
        assert hasattr(result, "sentiment_score")
        
        # Check content
        assert result.bias_level == BiasLevel.NONE
        assert BiasType.NEUTRAL in result.primary_bias_types
        assert -0.2 <= result.bias_direction <= 0.2  # Near zero
        
        # Check summary
        assert "no significant bias" in result.summary.lower()

    def test_detect_left_leaning_political_text(self, bias_detector):
        """Test detection of progressive/left-leaning political text."""
        text = """
        The new progressive tax policy aims to reduce income inequality and provide universal healthcare
        to all citizens. We must support the unions and workers' rights while implementing stronger 
        regulations on big corporations. The wealth tax proposal is a step towards economic justice
        and a more equitable society where social justice prevails.
        """
        
        result = bias_detector.detect_bias(text)
        
        # Verify progressive bias is detected
        assert result.bias_level in [BiasLevel.MODERATE, BiasLevel.STRONG, BiasLevel.EXTREME]
        assert BiasType.POLITICAL_LEFT in result.primary_bias_types or BiasType.ECONOMIC_PROGRESSIVE in result.primary_bias_types
        assert result.bias_direction > 0.3  # Positive = progressive
        
        # Check scores
        assert result.bias_scores[BiasType.POLITICAL_LEFT] > 0.4
        assert result.bias_scores[BiasType.ECONOMIC_PROGRESSIVE] > 0.3
        
        # Check summary
        assert "progressive" in result.summary.lower()

    def test_detect_right_leaning_political_text(self, bias_detector):
        """Test detection of conservative/right-leaning political text."""
        text = """
        Small government and free market principles are essential for economic growth and prosperity.
        We must protect traditional values and religious freedom while reducing regulations that
        hurt American businesses. The proposed tax cuts will help job creators and the 
        private sector drive innovation while respecting our constitutional rights.
        """
        
        result = bias_detector.detect_bias(text)
        
        # Verify conservative bias is detected
        assert result.bias_level in [BiasLevel.MODERATE, BiasLevel.STRONG, BiasLevel.EXTREME]
        assert BiasType.POLITICAL_RIGHT in result.primary_bias_types or BiasType.ECONOMIC_CONSERVATIVE in result.primary_bias_types
        assert result.bias_direction < -0.3  # Negative = conservative
        
        # Check scores
        assert result.bias_scores[BiasType.POLITICAL_RIGHT] > 0.4
        assert result.bias_scores[BiasType.ECONOMIC_CONSERVATIVE] > 0.3
        
        # Check summary
        assert "conservative" in result.summary.lower()

    def test_detect_environmental_bias(self, bias_detector):
        """Test detection of environmental bias."""
        text = """
        Climate change presents an urgent crisis requiring immediate action.
        We must transition to renewable energy and reduce carbon emissions 
        to protect our planet. Environmental protection should be a top priority,
        and fossil fuel companies must be held accountable for pollution.
        """
        
        result = bias_detector.detect_bias(text)
        
        # Verify environmental progressive bias is detected
        assert BiasType.ENVIRONMENTAL_PROGRESSIVE in result.primary_bias_types
        assert result.bias_scores[BiasType.ENVIRONMENTAL_PROGRESSIVE] > 0.5
        
        # Check summary
        assert any(b.value == "environmental_progressive" for b in result.primary_bias_types)

    def test_detect_sensationalist_language(self, bias_detector):
        """Test detection of sensationalist language."""
        text = """
        BREAKING: Shocking new scandal rocks administration in unprecedented crisis!
        The explosive revelations have caused chaos and could lead to a devastating
        collapse of public trust. This alarming emergency threatens to create
        a catastrophic disaster for the political establishment.
        """
        
        result = bias_detector.detect_bias(text)
        
        # Verify sensationalism is detected
        assert BiasType.SENSATIONALIST in result.primary_bias_types
        assert result.bias_scores[BiasType.SENSATIONALIST] > 0.6
        
        # Check summary 
        assert any(b.value == "sensationalist" for b in result.primary_bias_types)

    def test_detect_explicit_bias_markers(self, bias_detector):
        """Test detection of explicit bias markers in text."""
        text = """
        The economic data [BIAS-L] suggests that increased regulation
        may benefit consumer protection. However, other analysts [BIAS-R] 
        argue that market freedom produces better outcomes. Environmental 
        concerns [ENV-L] must be balanced with business interests [ECON-R].
        """
        
        result = bias_detector.detect_bias(text)
        
        # Verify markers are detected
        assert sum(result.bias_markers.values()) == 4
        assert result.bias_markers[BiasType.POLITICAL_LEFT] == 1
        assert result.bias_markers[BiasType.POLITICAL_RIGHT] == 1
        assert result.bias_markers[BiasType.ENVIRONMENTAL_PROGRESSIVE] == 1
        assert result.bias_markers[BiasType.ECONOMIC_CONSERVATIVE] == 1
        
        # Check that markers are mentioned in summary
        assert "bias markers" in result.summary.lower()


class TestBiasBalancer:
    """Tests for the BiasBalancer class."""

    def test_calculate_article_bias_empty(self):
        """Test calculation of article bias with empty memo set."""
        memo_results = {}
        
        result = BiasBalancer.calculate_article_bias(memo_results)
        
        # Check structure of result
        assert isinstance(result, dict)
        assert "overall_bias_direction" in result
        assert "overall_bias_level" in result
        assert "bias_by_type" in result
        assert "bias_by_memo" in result
        assert "summary" in result
        
        # Check default values for empty set
        assert result["overall_bias_direction"] == 0.0
        assert result["overall_bias_level"] == BiasLevel.NONE.value
        assert result["bias_by_type"] == {}
        assert result["bias_by_memo"] == {}
        assert "No memos" in result["summary"]

    def test_calculate_article_bias_mixed(self):
        """Test calculation of article bias with mixed memo biases."""
        # Create mock BiasDetectionResults
        memo_id1 = str(uuid.uuid4())
        memo_id2 = str(uuid.uuid4())
        memo_id3 = str(uuid.uuid4())
        
        # Left-leaning memo
        left_memo = BiasDetectionResult(
            text="Progressive memo text",
            bias_scores={
                BiasType.POLITICAL_LEFT: 0.7,
                BiasType.ECONOMIC_PROGRESSIVE: 0.6,
                BiasType.SOCIAL_PROGRESSIVE: 0.5,
                BiasType.POLITICAL_RIGHT: 0.1,
            },
            bias_markers={
                BiasType.POLITICAL_LEFT: 1,
                BiasType.ECONOMIC_PROGRESSIVE: 0,
                BiasType.SOCIAL_PROGRESSIVE: 0,
                BiasType.POLITICAL_RIGHT: 0,
                BiasType.ECONOMIC_CONSERVATIVE: 0,
                BiasType.SOCIAL_CONSERVATIVE: 0,
                BiasType.ENVIRONMENTAL_PROGRESSIVE: 0,
                BiasType.ENVIRONMENTAL_CONSERVATIVE: 0,
                BiasType.SENSATIONALIST: 0,
            },
            sentiment_score=0.2,
            tokens_count=50,
        )
        
        # Right-leaning memo
        right_memo = BiasDetectionResult(
            text="Conservative memo text",
            bias_scores={
                BiasType.POLITICAL_RIGHT: 0.8,
                BiasType.ECONOMIC_CONSERVATIVE: 0.7,
                BiasType.SOCIAL_CONSERVATIVE: 0.4,
                BiasType.POLITICAL_LEFT: 0.1,
            },
            bias_markers={
                BiasType.POLITICAL_LEFT: 0,
                BiasType.ECONOMIC_PROGRESSIVE: 0,
                BiasType.SOCIAL_PROGRESSIVE: 0,
                BiasType.POLITICAL_RIGHT: 1,
                BiasType.ECONOMIC_CONSERVATIVE: 1,
                BiasType.SOCIAL_CONSERVATIVE: 0,
                BiasType.ENVIRONMENTAL_PROGRESSIVE: 0,
                BiasType.ENVIRONMENTAL_CONSERVATIVE: 0,
                BiasType.SENSATIONALIST: 0,
            },
            sentiment_score=-0.1,
            tokens_count=60,
        )
        
        # Neutral memo
        neutral_memo = BiasDetectionResult(
            text="Neutral memo text",
            bias_scores={
                BiasType.POLITICAL_LEFT: 0.1,
                BiasType.ECONOMIC_PROGRESSIVE: 0.15,
                BiasType.POLITICAL_RIGHT: 0.1,
                BiasType.ECONOMIC_CONSERVATIVE: 0.15,
            },
            bias_markers={
                BiasType.POLITICAL_LEFT: 0,
                BiasType.ECONOMIC_PROGRESSIVE: 0,
                BiasType.SOCIAL_PROGRESSIVE: 0,
                BiasType.POLITICAL_RIGHT: 0,
                BiasType.ECONOMIC_CONSERVATIVE: 0,
                BiasType.SOCIAL_CONSERVATIVE: 0,
                BiasType.ENVIRONMENTAL_PROGRESSIVE: 0,
                BiasType.ENVIRONMENTAL_CONSERVATIVE: 0,
                BiasType.SENSATIONALIST: 0,
            },
            sentiment_score=0.0,
            tokens_count=40,
        )
        
        memo_results = {
            memo_id1: left_memo,
            memo_id2: right_memo,
            memo_id3: neutral_memo,
        }
        
        result = BiasBalancer.calculate_article_bias(memo_results)
        
        # Check overall bias (should be relatively balanced with slight conservative lean)
        # (0.7 + -0.8 + 0.0) / 3 ≈ -0.03
        assert -0.2 <= result["overall_bias_direction"] <= 0.2
        
        # The overall bias level should be Strong or Extreme
        # (because one memo has strong/extreme bias)
        assert result["overall_bias_level"] in [BiasLevel.STRONG.value, BiasLevel.EXTREME.value]
        
        # Check that memo-specific results are included
        assert len(result["bias_by_memo"]) == 3
        assert memo_id1 in result["bias_by_memo"]
        assert memo_id2 in result["bias_by_memo"]
        assert memo_id3 in result["bias_by_memo"]
        
        # Check that bias types are aggregated
        assert "political_left" in result["bias_by_type"]
        assert "political_right" in result["bias_by_type"]
        
        # Check summary includes some recommendations
        assert "balanced" in result["summary"].lower() or "bias" in result["summary"].lower()

    def test_generate_balance_recommendations_mild_bias(self):
        """Test balance recommendations for mild bias."""
        bias_assessment = {
            "overall_bias_direction": 0.1,
            "overall_bias_level": BiasLevel.MILD.value,
            "bias_by_type": {
                "political_left": 0.3,
                "political_right": 0.2,
            },
            "bias_by_memo": {},
            "summary": "The article shows mild bias with a politically balanced orientation."
        }
        
        result = BiasBalancer.generate_balance_recommendations(bias_assessment)
        
        # Should not need balancing for mild bias
        assert result["needs_balancing"] is False
        assert "sufficiently balanced" in result["recommendations"][0]
        assert result["memo_specific_recommendations"] == {}

    def test_generate_balance_recommendations_strong_left_bias(self):
        """Test balance recommendations for strong progressive bias."""
        bias_assessment = {
            "overall_bias_direction": 0.7,
            "overall_bias_level": BiasLevel.STRONG.value,
            "bias_by_type": {
                "political_left": 0.8,
                "economic_progressive": 0.7,
                "social_progressive": 0.6,
            },
            "bias_by_memo": {
                "memo1": {
                    "bias_direction": 0.8,
                    "bias_level": BiasLevel.EXTREME.value,
                    "primary_bias_types": ["political_left", "economic_progressive"],
                },
            },
            "summary": "The article shows strong bias with a strongly progressive orientation."
        }
        
        result = BiasBalancer.generate_balance_recommendations(bias_assessment)
        
        # Should need balancing
        assert result["needs_balancing"] is True
        
        # Should recommend conservative perspectives
        assert any("conservative perspectives" in r.lower() for r in result["recommendations"])
        
        # Should have memo-specific recommendations for the biased memo
        assert "memo1" in result["memo_specific_recommendations"]
        assert "Politics-Right" in result["memo_specific_recommendations"]["memo1"][1]

    def test_generate_balance_recommendations_strong_right_bias(self):
        """Test balance recommendations for strong conservative bias."""
        bias_assessment = {
            "overall_bias_direction": -0.7,
            "overall_bias_level": BiasLevel.STRONG.value,
            "bias_by_type": {
                "political_right": 0.8,
                "economic_conservative": 0.7,
                "social_conservative": 0.6,
            },
            "bias_by_memo": {
                "memo1": {
                    "bias_direction": -0.8,
                    "bias_level": BiasLevel.EXTREME.value,
                    "primary_bias_types": ["political_right", "economic_conservative"],
                },
            },
            "summary": "The article shows strong bias with a strongly conservative orientation."
        }
        
        result = BiasBalancer.generate_balance_recommendations(bias_assessment)
        
        # Should need balancing
        assert result["needs_balancing"] is True
        
        # Should recommend progressive perspectives
        assert any("progressive perspectives" in r.lower() for r in result["recommendations"])
        
        # Should have memo-specific recommendations for the biased memo
        assert "memo1" in result["memo_specific_recommendations"]
        assert "Politics-Left" in result["memo_specific_recommendations"]["memo1"][1] 