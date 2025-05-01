"""Bias detection and analysis utilities for FoglioAI."""
import json
import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import nltk
from nltk.tokenize import word_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer

# Ensure necessary NLTK resources are available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

logger = logging.getLogger(__name__)


class BiasType(str, Enum):
    """Types of bias that can be detected."""

    POLITICAL_LEFT = "political_left"
    POLITICAL_RIGHT = "political_right"
    ECONOMIC_PROGRESSIVE = "economic_progressive"
    ECONOMIC_CONSERVATIVE = "economic_conservative"
    SOCIAL_PROGRESSIVE = "social_progressive"
    SOCIAL_CONSERVATIVE = "social_conservative"
    ENVIRONMENTAL_PROGRESSIVE = "environmental_progressive"
    ENVIRONMENTAL_CONSERVATIVE = "environmental_conservative"
    SENSATIONALIST = "sensationalist"  # Overly dramatic/emotionally charged
    NEUTRAL = "neutral"


class BiasLevel(str, Enum):
    """Levels of bias that can be detected."""

    NONE = "none"  # 0.0-0.2 (20%)
    MILD = "mild"  # 0.2-0.4 (40%)
    MODERATE = "moderate"  # 0.4-0.6 (60%)
    STRONG = "strong"  # 0.6-0.8 (80%)
    EXTREME = "extreme"  # 0.8-1.0 (100%)


class BiasConfig:
    """Configuration for bias detection."""

    # Thresholds for determining bias levels
    BIAS_THRESHOLDS = {
        BiasLevel.NONE: 0.2,
        BiasLevel.MILD: 0.4,
        BiasLevel.MODERATE: 0.6,
        BiasLevel.STRONG: 0.8,
        BiasLevel.EXTREME: 1.0,
    }

    # Keywords associated with different biases
    # These are simplified, a real implementation would use a more sophisticated approach
    BIAS_KEYWORDS = {
        BiasType.POLITICAL_LEFT: {
            "progressive", "liberal", "left-wing", "democrat", "socialism", 
            "social justice", "equality", "universal healthcare", "welfare state",
            "regulation", "big government", "workers rights", "unions",
            "green new deal", "wealth tax", "income inequality"
        },
        BiasType.POLITICAL_RIGHT: {
            "conservative", "republican", "right-wing", "traditional values",
            "free market", "small government", "deregulation", "tax cuts",
            "family values", "religious freedom", "individual liberty",
            "second amendment", "constitutional rights", "patriot"
        },
        BiasType.ECONOMIC_PROGRESSIVE: {
            "wealth tax", "income inequality", "financial regulation", "corporate tax",
            "living wage", "minimum wage", "universal basic income", "economic justice",
            "wall street", "billionaire tax", "labor unions", "progressive taxation"
        },
        BiasType.ECONOMIC_CONSERVATIVE: {
            "tax cuts", "free market", "deregulation", "fiscal responsibility",
            "small business", "job creators", "economic growth", "supply side",
            "trickle down", "market freedom", "private sector", "free enterprise"
        },
        BiasType.SOCIAL_PROGRESSIVE: {
            "reproductive rights", "women's rights", "LGBTQ+", "transgender rights",
            "racial justice", "black lives matter", "social justice", "criminal justice reform",
            "police reform", "immigration reform", "civil liberties"
        },
        BiasType.SOCIAL_CONSERVATIVE: {
            "traditional values", "family values", "religious freedom", "pro-life",
            "border security", "law and order", "tough on crime", "marriage",
            "school choice", "western values", "moral", "heritage"
        },
        BiasType.ENVIRONMENTAL_PROGRESSIVE: {
            "climate change", "global warming", "renewable energy", "environmental justice",
            "sustainability", "carbon emissions", "fossil fuel", "clean energy",
            "environmental protection", "endangered species", "pollution"
        },
        BiasType.ENVIRONMENTAL_CONSERVATIVE: {
            "energy independence", "oil", "natural gas", "coal", "nuclear power",
            "regulatory burden", "economic impact", "job-killing regulations",
            "EPA overreach", "climate alarmism", "energy jobs"
        },
        BiasType.SENSATIONALIST: {
            "catastrophic", "devastating", "unprecedented", "crisis", "shocking",
            "alarming", "outrageous", "scandalous", "bombshell", "breaking",
            "explosive", "disaster", "chaos", "collapse", "emergency", "tragedy"
        },
    }

    # Explicit bias markers (often added by agents themselves)
    BIAS_MARKERS = {
        "BIAS-L": BiasType.POLITICAL_LEFT,
        "BIAS-R": BiasType.POLITICAL_RIGHT,
        "ECON-L": BiasType.ECONOMIC_PROGRESSIVE,
        "ECON-R": BiasType.ECONOMIC_CONSERVATIVE,
        "SOCIAL-L": BiasType.SOCIAL_PROGRESSIVE,
        "SOCIAL-R": BiasType.SOCIAL_CONSERVATIVE,
        "ENV-L": BiasType.ENVIRONMENTAL_PROGRESSIVE,
        "ENV-R": BiasType.ENVIRONMENTAL_CONSERVATIVE,
    }


class BiasDetectionResult:
    """Result of bias detection analysis."""

    def __init__(
        self,
        text: str,
        bias_scores: Dict[BiasType, float],
        bias_markers: Dict[BiasType, int],
        sentiment_score: float,
        tokens_count: int,
    ):
        """Initialize the bias detection result.

        Args:
            text (str): The analyzed text
            bias_scores (Dict[BiasType, float]): Bias scores for each bias type
            bias_markers (Dict[BiasType, int]): Count of explicit bias markers
            sentiment_score (float): Overall sentiment score (-1.0 to 1.0)
            tokens_count (int): Number of tokens processed
        """
        self.text = text
        self.bias_scores = bias_scores
        self.bias_markers = bias_markers
        self.sentiment_score = sentiment_score
        self.tokens_count = tokens_count
        
        # Determine the primary bias types (highest scores)
        self.primary_bias_types = self._get_primary_bias_types()
        
        # Determine the overall bias level
        self.bias_level = self._calculate_bias_level()
        
        # Calculate the overall bias direction (liberal vs. conservative)
        self.bias_direction = self._calculate_bias_direction()
        
        # Human-readable summary
        self.summary = self._generate_summary()

    def _get_primary_bias_types(self) -> List[BiasType]:
        """Get the primary bias types (highest scoring).

        Returns:
            List[BiasType]: List of primary bias types
        """
        if not self.bias_scores:
            return [BiasType.NEUTRAL]
            
        # Find the highest scoring bias type(s)
        max_score = max(self.bias_scores.values())
        
        # If the max score is low, consider neutral
        if max_score < BiasConfig.BIAS_THRESHOLDS[BiasLevel.MILD]:
            return [BiasType.NEUTRAL]
            
        # Return all bias types with the highest score (or very close to it)
        threshold = max_score - 0.05  # Allow for scores very close to max
        return [bias_type for bias_type, score in self.bias_scores.items() 
                if score >= threshold]

    def _calculate_bias_level(self) -> BiasLevel:
        """Calculate the overall bias level.

        Returns:
            BiasLevel: The overall bias level
        """
        if not self.bias_scores:
            return BiasLevel.NONE
            
        # Use the highest bias score to determine level
        max_score = max(self.bias_scores.values())
        
        # Determine level based on thresholds
        for level, threshold in sorted(
            BiasConfig.BIAS_THRESHOLDS.items(), 
            key=lambda x: x[1]
        ):
            if max_score <= threshold:
                return level
                
        return BiasLevel.EXTREME  # Fallback

    def _calculate_bias_direction(self) -> float:
        """Calculate the overall bias direction from -1.0 (conservative) to 1.0 (progressive).

        Returns:
            float: The bias direction score
        """
        # Group bias types into progressive vs. conservative
        progressive_types = {
            BiasType.POLITICAL_LEFT, 
            BiasType.ECONOMIC_PROGRESSIVE,
            BiasType.SOCIAL_PROGRESSIVE, 
            BiasType.ENVIRONMENTAL_PROGRESSIVE
        }
        
        conservative_types = {
            BiasType.POLITICAL_RIGHT, 
            BiasType.ECONOMIC_CONSERVATIVE,
            BiasType.SOCIAL_CONSERVATIVE, 
            BiasType.ENVIRONMENTAL_CONSERVATIVE
        }
        
        # Calculate total progressive and conservative bias
        progressive_score = sum(self.bias_scores.get(bias_type, 0) 
                               for bias_type in progressive_types)
        
        conservative_score = sum(self.bias_scores.get(bias_type, 0) 
                                for bias_type in conservative_types)
        
        # If both scores are very low, return neutral (0)
        if progressive_score < 0.1 and conservative_score < 0.1:
            return 0.0
        
        # Calculate direction between -1 (conservative) and 1 (progressive)
        total = progressive_score + conservative_score
        if total == 0:
            return 0.0
            
        return (progressive_score - conservative_score) / total

    def _generate_summary(self) -> str:
        """Generate a human-readable summary of the bias detection result.

        Returns:
            str: Human-readable summary
        """
        # Define helper function to describe bias level
        def describe_bias_level(level: BiasLevel) -> str:
            return {
                BiasLevel.NONE: "no significant",
                BiasLevel.MILD: "mild",
                BiasLevel.MODERATE: "moderate",
                BiasLevel.STRONG: "strong",
                BiasLevel.EXTREME: "extreme"
            }.get(level, "unknown")
        
        # Define helper function to describe bias direction
        def describe_bias_direction(direction: float) -> str:
            if -0.2 <= direction <= 0.2:
                return "neutral"
            elif direction < -0.6:
                return "strongly conservative"
            elif direction < -0.2:
                return "moderately conservative"
            elif direction > 0.6:
                return "strongly progressive"
            else:
                return "moderately progressive"
                
        # Generate basic summary
        summary = f"Analysis detected {describe_bias_level(self.bias_level)} bias "
        summary += f"with a {describe_bias_direction(self.bias_direction)} orientation. "
        
        # Add information about primary bias types if not neutral
        if BiasType.NEUTRAL not in self.primary_bias_types:
            bias_types_str = ", ".join(b.value for b in self.primary_bias_types)
            summary += f"Primary bias types: {bias_types_str}. "
        
        # Add information about explicit bias markers if any
        if sum(self.bias_markers.values()) > 0:
            summary += f"Detected {sum(self.bias_markers.values())} explicit bias markers. "
        
        # Add sentiment information
        if self.sentiment_score > 0.3:
            summary += "The text has a positive emotional tone. "
        elif self.sentiment_score < -0.3:
            summary += "The text has a negative emotional tone. "
        else:
            summary += "The text has a neutral emotional tone. "
            
        return summary

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the result
        """
        return {
            "bias_scores": {k.value: v for k, v in self.bias_scores.items()},
            "bias_markers": {k.value: v for k, v in self.bias_markers.items()},
            "sentiment_score": self.sentiment_score,
            "tokens_count": self.tokens_count,
            "primary_bias_types": [b.value for b in self.primary_bias_types],
            "bias_level": self.bias_level.value,
            "bias_direction": self.bias_direction,
            "summary": self.summary,
        }


class BiasDetector:
    """Detector for political and ideological bias in text."""

    def __init__(self):
        """Initialize the bias detector."""
        self.sentiment_analyzer = SentimentIntensityAnalyzer()

    def detect_bias(self, text: str) -> BiasDetectionResult:
        """Detect bias in text.

        Args:
            text (str): Text to analyze

        Returns:
            BiasDetectionResult: Result of bias detection
        """
        # Tokenize the text
        tokens = word_tokenize(text.lower())
        
        # Calculate bias scores
        bias_scores = self._calculate_bias_scores(text, tokens)
        
        # Extract explicit bias markers
        bias_markers = self._extract_bias_markers(text)
        
        # Calculate sentiment score
        sentiment_score = self._calculate_sentiment(text)
        
        # Create and return result
        return BiasDetectionResult(
            text=text,
            bias_scores=bias_scores,
            bias_markers=bias_markers,
            sentiment_score=sentiment_score,
            tokens_count=len(tokens),
        )

    def _calculate_bias_scores(
        self, text: str, tokens: List[str]
    ) -> Dict[BiasType, float]:
        """Calculate bias scores for different bias types.

        Args:
            text (str): Original text
            tokens (List[str]): Tokenized text

        Returns:
            Dict[BiasType, float]: Bias scores by type
        """
        bias_scores = {bias_type: 0.0 for bias_type in BiasType 
                       if bias_type != BiasType.NEUTRAL}
        
        # Count matches with bias keywords
        token_set = set(tokens)
        
        # Count bigrams and trigrams too for better matching
        bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens)-1)]
        trigrams = [f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}" 
                    for i in range(len(tokens)-2)]
        
        # Combine all n-grams
        all_grams = token_set.union(set(bigrams), set(trigrams))
        
        # Calculate raw counts of keyword matches
        keyword_counts = {}
        for bias_type, keywords in BiasConfig.BIAS_KEYWORDS.items():
            # Count direct matches
            direct_matches = sum(1 for gram in all_grams 
                                for keyword in keywords 
                                if keyword in gram)
            
            # Count partial matches in longer phrases
            partial_matches = sum(1 for gram in all_grams 
                                 for keyword in keywords 
                                 if keyword in gram and keyword != gram)
            
            # Combine with more weight for direct matches
            keyword_counts[bias_type] = direct_matches + (partial_matches * 0.5)
        
        # Normalize to get scores (0.0 to 1.0)
        max_count = max(keyword_counts.values()) if keyword_counts else 0
        
        if max_count > 0:
            for bias_type, count in keyword_counts.items():
                # Apply a softmax-like normalization to emphasize differences
                normalized_score = count / max_count
                
                # Apply a curve to emphasize stronger biases
                bias_scores[bias_type] = min(1.0, normalized_score ** 0.75)
        
        return bias_scores

    def _extract_bias_markers(self, text: str) -> Dict[BiasType, int]:
        """Extract explicit bias markers from text.

        Args:
            text (str): Text to analyze

        Returns:
            Dict[BiasType, int]: Count of bias markers by type
        """
        bias_markers = {bias_type: 0 for bias_type in BiasType 
                       if bias_type != BiasType.NEUTRAL}
        
        # Look for explicit markers in the text
        for marker, bias_type in BiasConfig.BIAS_MARKERS.items():
            # Match markers like [BIAS-L] or {BIAS-L} or (BIAS-L) or <BIAS-L>
            pattern = rf'[\[\{{\(\<]{marker}[\]\}}\)\>]'
            matches = re.findall(pattern, text)
            bias_markers[bias_type] += len(matches)
        
        return bias_markers

    def _calculate_sentiment(self, text: str) -> float:
        """Calculate sentiment score for text.

        Args:
            text (str): Text to analyze

        Returns:
            float: Sentiment score between -1.0 (negative) and 1.0 (positive)
        """
        try:
            sentiment_scores = self.sentiment_analyzer.polarity_scores(text)
            return sentiment_scores['compound']  # -1.0 to 1.0
        except Exception as e:
            logger.warning(f"Error calculating sentiment: {str(e)}")
            return 0.0


class BiasBalancer:
    """Utility for balancing bias in article content."""

    @staticmethod
    def calculate_article_bias(
        memo_results: Dict[str, BiasDetectionResult]
    ) -> Dict[str, Any]:
        """Calculate overall article bias based on individual memo results.

        Args:
            memo_results (Dict[str, BiasDetectionResult]): 
                Mapping of memo IDs to their bias detection results

        Returns:
            Dict[str, Any]: Overall article bias assessment
        """
        if not memo_results:
            return {
                "overall_bias_direction": 0.0,
                "overall_bias_level": BiasLevel.NONE.value,
                "bias_by_type": {},
                "bias_by_memo": {},
                "summary": "No memos to analyze for bias."
            }
        
        # Calculate average bias direction and level
        bias_directions = [result.bias_direction for result in memo_results.values()]
        overall_direction = sum(bias_directions) / len(bias_directions)
        
        # Calculate highest bias level
        bias_levels = [result.bias_level for result in memo_results.values()]
        bias_level_values = {
            BiasLevel.NONE: 0,
            BiasLevel.MILD: 1,
            BiasLevel.MODERATE: 2,
            BiasLevel.STRONG: 3,
            BiasLevel.EXTREME: 4,
        }
        max_level_value = max(bias_level_values[level] for level in bias_levels)
        overall_level = next(level for level, value in bias_level_values.items() 
                            if value == max_level_value)
        
        # Aggregate bias by type
        bias_by_type = {}
        for result in memo_results.values():
            for bias_type, score in result.bias_scores.items():
                if score > 0:
                    if bias_type.value not in bias_by_type:
                        bias_by_type[bias_type.value] = []
                    bias_by_type[bias_type.value].append(score)
        
        # Calculate average for each bias type
        avg_bias_by_type = {
            bias_type: sum(scores) / len(scores)
            for bias_type, scores in bias_by_type.items()
        }
        
        # Create bias by memo summary
        bias_by_memo = {
            memo_id: {
                "bias_direction": result.bias_direction,
                "bias_level": result.bias_level.value,
                "primary_bias_types": [b.value for b in result.primary_bias_types],
            }
            for memo_id, result in memo_results.items()
        }
        
        # Generate a summary
        summary = BiasBalancer._generate_bias_summary(
            overall_direction, overall_level, avg_bias_by_type
        )
        
        return {
            "overall_bias_direction": overall_direction,
            "overall_bias_level": overall_level.value,
            "bias_by_type": avg_bias_by_type,
            "bias_by_memo": bias_by_memo,
            "summary": summary,
        }

    @staticmethod
    def _generate_bias_summary(
        direction: float, level: BiasLevel, bias_by_type: Dict[str, float]
    ) -> str:
        """Generate a human-readable summary of article bias.

        Args:
            direction (float): Overall bias direction
            level (BiasLevel): Overall bias level
            bias_by_type (Dict[str, float]): Average bias by type

        Returns:
            str: Human-readable summary
        """
        # Describe overall bias
        if level == BiasLevel.NONE:
            summary = "The article shows no significant political or ideological bias. "
        else:
            # Direction description
            if direction < -0.6:
                direction_desc = "strongly conservative"
            elif direction < -0.2:
                direction_desc = "moderately conservative"
            elif direction < 0.2:
                direction_desc = "politically balanced"
            elif direction < 0.6:
                direction_desc = "moderately progressive"
            else:
                direction_desc = "strongly progressive"
            
            # Level description
            level_desc = {
                BiasLevel.MILD: "mild",
                BiasLevel.MODERATE: "moderate",
                BiasLevel.STRONG: "strong",
                BiasLevel.EXTREME: "extreme",
            }[level]
            
            summary = f"The article shows {level_desc} bias with a {direction_desc} orientation. "
        
        # Add information about specific bias types
        if bias_by_type:
            # Find the top bias types
            sorted_biases = sorted(
                bias_by_type.items(), key=lambda x: x[1], reverse=True
            )
            top_biases = [bias_type for bias_type, score in sorted_biases 
                          if score > 0.3]
            
            if top_biases:
                top_biases_str = ", ".join(top_biases)
                summary += f"The most prominent bias types are: {top_biases_str}. "
        
        # Add balancing recommendation if needed
        if level in [BiasLevel.STRONG, BiasLevel.EXTREME]:
            summary += "It is recommended to balance the content by incorporating "
            if direction > 0.2:
                summary += "more conservative perspectives."
            elif direction < -0.2:
                summary += "more progressive perspectives."
            else:
                summary += "more neutral, fact-based reporting."
        
        return summary

    @staticmethod
    def generate_balance_recommendations(
        bias_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate recommendations for balancing article bias.

        Args:
            bias_assessment (Dict[str, Any]): Overall article bias assessment

        Returns:
            Dict[str, Any]: Balance recommendations
        """
        direction = bias_assessment.get("overall_bias_direction", 0.0)
        level_str = bias_assessment.get("overall_bias_level", BiasLevel.NONE.value)
        level = BiasLevel(level_str)
        
        # Only provide recommendations for moderate to extreme bias
        if level in [BiasLevel.NONE, BiasLevel.MILD]:
            return {
                "needs_balancing": False,
                "recommendations": ["The article appears to be sufficiently balanced."],
                "memo_specific_recommendations": {},
            }
        
        # General recommendations
        recommendations = []
        
        if direction > 0.2:  # Progressive bias
            recommendations.extend([
                "Include more conservative perspectives on the topic.",
                "Ensure economic considerations and business impacts are addressed.",
                "Add traditional or religious viewpoints where relevant.",
                "Consider national security and law enforcement perspectives.",
            ])
        elif direction < -0.2:  # Conservative bias
            recommendations.extend([
                "Include more progressive perspectives on the topic.",
                "Ensure social justice and equality aspects are addressed.",
                "Consider environmental and sustainability impacts.",
                "Add perspectives from minority or marginalized groups.",
            ])
        else:  # Neutral but still biased in other ways
            recommendations.extend([
                "Reduce emotionally charged language and rhetoric.",
                "Ensure fact-based reporting with proper citations.",
                "Include diverse perspectives from multiple sides of the issue.",
                "Separate facts from opinions and analysis more clearly.",
            ])
        
        # Add specific recommendations based on bias types
        bias_by_type = bias_assessment.get("bias_by_type", {})
        for bias_type, score in bias_by_type.items():
            if score > 0.5:
                if "political_left" in bias_type:
                    recommendations.append(
                        "Reduce progressive political framing and include more conservative viewpoints."
                    )
                elif "political_right" in bias_type:
                    recommendations.append(
                        "Reduce conservative political framing and include more progressive viewpoints."
                    )
                elif "economic_progressive" in bias_type:
                    recommendations.append(
                        "Balance economic analysis with more market-oriented perspectives."
                    )
                elif "economic_conservative" in bias_type:
                    recommendations.append(
                        "Balance economic analysis with more social welfare considerations."
                    )
                elif "social_progressive" in bias_type:
                    recommendations.append(
                        "Include more traditional perspectives on social issues."
                    )
                elif "social_conservative" in bias_type:
                    recommendations.append(
                        "Include more progressive perspectives on social issues."
                    )
                elif "environmental_progressive" in bias_type:
                    recommendations.append(
                        "Balance environmental concerns with economic considerations."
                    )
                elif "environmental_conservative" in bias_type:
                    recommendations.append(
                        "Address environmental concerns more prominently."
                    )
                elif "sensationalist" in bias_type:
                    recommendations.append(
                        "Reduce emotionally charged language and focus on factual reporting."
                    )
        
        # Generate memo-specific recommendations
        memo_specific = {}
        bias_by_memo = bias_assessment.get("bias_by_memo", {})
        
        for memo_id, memo_bias in bias_by_memo.items():
            memo_direction = memo_bias.get("bias_direction", 0.0)
            memo_level = BiasLevel(memo_bias.get("bias_level", BiasLevel.NONE.value))
            
            if memo_level in [BiasLevel.STRONG, BiasLevel.EXTREME]:
                if memo_direction > 0.5:
                    memo_specific[memo_id] = [
                        "This memo has strong progressive bias and should be balanced with conservative perspectives.",
                        "Consider requesting additional research from Politics-Right agent.",
                    ]
                elif memo_direction < -0.5:
                    memo_specific[memo_id] = [
                        "This memo has strong conservative bias and should be balanced with progressive perspectives.",
                        "Consider requesting additional research from Politics-Left agent.",
                    ]
                else:
                    memo_specific[memo_id] = [
                        "This memo has strong bias in non-political dimensions and should be fact-checked.",
                        "Consider requesting additional research from Researcher agent.",
                    ]
        
        return {
            "needs_balancing": True,
            "recommendations": recommendations,
            "memo_specific_recommendations": memo_specific,
        } 