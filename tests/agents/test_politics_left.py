"""Tests for the Politics-Left agent."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents import PoliticsLeftAgent
from app.models.agent import AgentRole
from app.models.citation import Citation


@pytest.fixture
def mock_redis_client():
    """Fixture for mocking the Redis client."""
    with patch("app.agents.politics_left.redis_client") as mock_client:
        # Configure mock
        mock_client.client = MagicMock()
        mock_client.client.json.return_value.set = AsyncMock()
        mock_client.client.exists.return_value = False
        yield mock_client


@pytest.fixture
def mock_citation_manager():
    """Fixture for mocking the CitationManager."""
    with patch("app.agents.politics_left.CitationManager") as mock_cm:
        manager_instance = mock_cm.return_value
        yield manager_instance


@pytest.fixture
def politics_left_agent(mock_redis_client, mock_citation_manager):
    """Fixture for creating a Politics-Left agent for testing."""
    article_id = uuid.uuid4()
    agent = PoliticsLeftAgent(article_id=article_id)
    
    # Mock the publish methods to avoid actual Redis operations
    agent.publish_progress = MagicMock()
    agent.publish_completion = MagicMock()
    agent.publish_error = MagicMock()
    
    yield agent


@pytest.mark.asyncio
async def test_politics_left_init():
    """Test Politics-Left agent initialization."""
    article_id = uuid.uuid4()
    agent = PoliticsLeftAgent(article_id=article_id)
    
    assert agent.config.role == AgentRole.POLITICS_LEFT
    assert agent.config.name == "Progressive Political Analyst"
    assert agent.article_id == article_id


@pytest.mark.asyncio
async def test_analyze_political_topic(politics_left_agent):
    """Test analyzing a political topic from a progressive perspective."""
    topic = "Workers' Rights Legislation"
    citations = [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/politics/workers-rights",
            title="The Fight for Workers' Rights",
            author="Jane Progressive",
            publication_date="1995-01-01",
            access_timestamp="2023-01-01T12:00:00",
            excerpt="The struggle for fair labor practices and workers' rights...",
        )
    ]
    
    result = await politics_left_agent.analyze_political_topic(topic, citations)
    
    # Verify the result structure
    assert "perspective" in result
    assert "key_points" in result
    assert "policy_recommendations" in result
    assert "bias_markers" in result
    assert "cited_sources" in result
    
    # Verify bias markers are included
    assert "progressive_bias_score" in result["bias_markers"]
    assert "bias_areas" in result["bias_markers"]
    
    # Verify that progress and completion were published
    politics_left_agent.publish_progress.assert_called_once()
    politics_left_agent.publish_completion.assert_called_once()


@pytest.mark.asyncio
async def test_provide_counterarguments(politics_left_agent):
    """Test providing progressive counterarguments to conservative points."""
    conservative_points = [
        "Government regulations stifle business growth and innovation",
        "Lower taxes for businesses lead to job creation"
    ]
    citations = [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/politics/regulations",
            title="Impact of Regulations on Economy",
            author="Policy Institute",
            publication_date="2000-01-01",
            access_timestamp="2023-01-01T12:00:00",
            excerpt="The relationship between government regulations and economic outcomes...",
        )
    ]
    
    result = await politics_left_agent.provide_counterarguments(conservative_points, citations)
    
    # Verify the result structure
    assert "responses" in result
    assert "progressive_principles" in result
    assert "bias_markers" in result
    
    # Verify responses match the conservative points
    assert len(result["responses"]) == len(conservative_points)
    assert result["responses"][0]["point"] == conservative_points[0]
    
    # Verify bias markers are included
    assert "progressive_bias_score" in result["bias_markers"]
    
    # Verify that progress was published
    politics_left_agent.publish_progress.assert_called_once()


@pytest.mark.asyncio
async def test_create_progressive_memo(politics_left_agent):
    """Test creating a comprehensive progressive political memo."""
    topic = "Economic Inequality"
    citations = [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/politics/inequality",
            title="The Growing Economic Divide",
            author="Economy Watch",
            publication_date="2005-01-01",
            access_timestamp="2023-01-01T12:00:00",
            excerpt="Analysis of growing economic inequality and its societal impacts...",
        )
    ]
    
    # Mock the analyze_political_topic method to return predetermined data
    politics_left_agent.analyze_political_topic = AsyncMock(
        return_value={
            "perspective": "progressive",
            "key_points": [
                "Inequality undermines social cohesion",
                "Progressive taxation is needed",
                "Workers need stronger protections"
            ],
            "core_values_alignment": "Economic inequality fundamentally contradicts progressive values",
            "policy_recommendations": ["Wealth tax", "Stronger labor unions"],
            "bias_markers": {
                "progressive_bias_score": 0.8,
                "bias_areas": ["wealth redistribution", "labor advocacy"]
            },
            "cited_sources": [str(citations[0].id)],
        }
    )
    
    result = await politics_left_agent.create_progressive_memo(topic, citations)
    
    # Verify that the memo contains expected sections
    assert "PROGRESSIVE PERSPECTIVE ON ECONOMIC INEQUALITY" in result
    assert "the lens of social equality and economic justice" in result
    assert "Inequality undermines social cohesion" in result
    assert "Progressive taxation is needed" in result
    assert "Workers need stronger protections" in result
    assert "Wealth tax" in result
    assert "Stronger labor unions" in result
    
    # Verify that progress and completion were published
    politics_left_agent.publish_progress.assert_called_once()
    politics_left_agent.publish_completion.assert_called_once() 