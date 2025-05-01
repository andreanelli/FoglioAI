"""Tests for the Politics-Right agent."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents import PoliticsRightAgent
from app.models.agent import AgentRole
from app.models.citation import Citation


@pytest.fixture
def mock_redis_client():
    """Fixture for mocking the Redis client."""
    with patch("app.agents.politics_right.redis_client") as mock_client:
        # Configure mock
        mock_client.client = MagicMock()
        mock_client.client.json.return_value.set = AsyncMock()
        mock_client.client.exists.return_value = False
        yield mock_client


@pytest.fixture
def mock_citation_manager():
    """Fixture for mocking the CitationManager."""
    with patch("app.agents.politics_right.CitationManager") as mock_cm:
        manager_instance = mock_cm.return_value
        yield manager_instance


@pytest.fixture
def politics_right_agent(mock_redis_client, mock_citation_manager):
    """Fixture for creating a Politics-Right agent for testing."""
    article_id = uuid.uuid4()
    agent = PoliticsRightAgent(article_id=article_id)
    
    # Mock the publish methods to avoid actual Redis operations
    agent.publish_progress = MagicMock()
    agent.publish_completion = MagicMock()
    agent.publish_error = MagicMock()
    
    yield agent


@pytest.mark.asyncio
async def test_politics_right_init():
    """Test Politics-Right agent initialization."""
    article_id = uuid.uuid4()
    agent = PoliticsRightAgent(article_id=article_id)
    
    assert agent.config.role == AgentRole.POLITICS_RIGHT
    assert agent.config.name == "Conservative Political Analyst"
    assert agent.article_id == article_id


@pytest.mark.asyncio
async def test_analyze_political_topic(politics_right_agent):
    """Test analyzing a political topic from a conservative perspective."""
    topic = "Government Regulation of Business"
    citations = [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/politics/business-regulation",
            title="Impact of Regulations on Economic Growth",
            author="John Conservative",
            publication_date="1995-01-01",
            access_timestamp="2023-01-01T12:00:00",
            excerpt="An analysis of how government regulations affect economic growth and prosperity...",
        )
    ]
    
    result = await politics_right_agent.analyze_political_topic(topic, citations)
    
    # Verify the result structure
    assert "perspective" in result
    assert "key_points" in result
    assert "policy_recommendations" in result
    assert "bias_markers" in result
    assert "cited_sources" in result
    
    # Verify bias markers are included
    assert "conservative_bias_score" in result["bias_markers"]
    assert "bias_areas" in result["bias_markers"]
    
    # Verify that progress and completion were published
    politics_right_agent.publish_progress.assert_called_once()
    politics_right_agent.publish_completion.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_economic_impact(politics_right_agent):
    """Test evaluating economic impact of a policy from a conservative perspective."""
    policy = "New corporate tax increase proposal"
    citations = [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/economics/taxation",
            title="Effects of Corporate Taxation on Investment",
            author="Economics Institute",
            publication_date="2000-01-01",
            access_timestamp="2023-01-01T12:00:00",
            excerpt="Analysis of how corporate tax rates affect business investment decisions...",
        )
    ]
    
    result = await politics_right_agent.evaluate_economic_impact(policy, citations)
    
    # Verify the result structure
    assert "market_impact" in result
    assert "fiscal_responsibility" in result
    assert "entrepreneurship_impact" in result
    assert "conservative_score" in result
    assert "bias_markers" in result
    
    # Verify that progress was published
    politics_right_agent.publish_progress.assert_called_once()


@pytest.mark.asyncio
async def test_create_conservative_memo(politics_right_agent):
    """Test creating a comprehensive conservative political memo."""
    topic = "Tax Policy Reform"
    citations = [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/politics/tax-reform",
            title="Principles of Sound Tax Policy",
            author="Conservative Think Tank",
            publication_date="2005-01-01",
            access_timestamp="2023-01-01T12:00:00",
            excerpt="Analysis of principles that should guide tax policy reforms...",
        )
    ]
    
    # Mock the analyze_political_topic method to return predetermined data
    politics_right_agent.analyze_political_topic = AsyncMock(
        return_value={
            "perspective": "conservative",
            "key_points": [
                "Lower taxes stimulate economic growth",
                "Simplified tax code reduces compliance costs",
                "Fiscal responsibility requires spending cuts"
            ],
            "core_values_alignment": "Tax policy reform aligns with conservative principles of economic freedom",
            "policy_recommendations": ["Flat tax system", "Eliminate loopholes"],
            "bias_markers": {
                "conservative_bias_score": 0.8,
                "bias_areas": ["low taxation", "fiscal restraint"]
            },
            "cited_sources": [str(citations[0].id)],
        }
    )
    
    result = await politics_right_agent.create_conservative_memo(topic, citations)
    
    # Verify that the memo contains expected sections
    assert "CONSERVATIVE PERSPECTIVE ON TAX POLICY REFORM" in result
    assert "the lens of free markets, limited government, and traditional values" in result
    assert "Lower taxes stimulate economic growth" in result
    assert "Simplified tax code reduces compliance costs" in result
    assert "Fiscal responsibility requires spending cuts" in result
    assert "Flat tax system" in result
    assert "Eliminate loopholes" in result
    
    # Verify that progress and completion were published
    politics_right_agent.publish_progress.assert_called_once()
    politics_right_agent.publish_completion.assert_called_once() 