"""Tests for the Geopolitics agent."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents import GeopoliticsAgent
from app.models.agent import AgentRole
from app.models.citation import Citation


@pytest.fixture
def mock_redis_client():
    """Fixture for mocking the Redis client."""
    with patch("app.agents.geopolitics.redis_client") as mock_client:
        # Configure mock
        mock_client.client = MagicMock()
        mock_client.client.json.return_value.set = AsyncMock()
        mock_client.client.exists.return_value = False
        yield mock_client


@pytest.fixture
def mock_citation_manager():
    """Fixture for mocking the CitationManager."""
    with patch("app.agents.geopolitics.CitationManager") as mock_cm:
        manager_instance = mock_cm.return_value
        yield manager_instance


@pytest.fixture
def geopolitics_agent(mock_redis_client, mock_citation_manager):
    """Fixture for creating a Geopolitics agent for testing."""
    article_id = uuid.uuid4()
    agent = GeopoliticsAgent(article_id=article_id)
    
    # Mock the publish methods to avoid actual Redis operations
    agent.publish_progress = MagicMock()
    agent.publish_completion = MagicMock()
    agent.publish_error = MagicMock()
    
    yield agent


@pytest.mark.asyncio
async def test_geopolitics_init():
    """Test Geopolitics agent initialization."""
    article_id = uuid.uuid4()
    agent = GeopoliticsAgent(article_id=article_id)
    
    assert agent.config.role == AgentRole.GEOPOLITICS
    assert agent.config.name == "International Relations Analyst"
    assert agent.article_id == article_id


@pytest.mark.asyncio
async def test_analyze_international_relations(geopolitics_agent):
    """Test analyzing international relations on a topic."""
    topic = "The Treaty of Versailles"
    region = "Europe"
    citations = [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/treaties/versailles",
            title="The Treaty of Versailles and Its Aftermath",
            author="Diplomatic Institute",
            publication_date="1995-01-01",
            access_timestamp="2023-01-01T12:00:00",
            excerpt="An analysis of the Treaty of Versailles and its impact on European politics...",
        )
    ]
    
    result = await geopolitics_agent.analyze_international_relations(topic, region, citations)
    
    # Verify the result structure
    assert "key_players" in result
    assert "power_dynamics" in result
    assert "tensions" in result
    assert "diplomatic_context" in result
    assert "economic_factors" in result
    assert "military_aspects" in result
    assert "regional_focus" in result
    assert "cited_sources" in result
    
    # Verify region is set correctly
    assert result["regional_focus"] == region
    
    # Verify that progress and completion were published
    geopolitics_agent.publish_progress.assert_called_once()
    geopolitics_agent.publish_completion.assert_called_once()


@pytest.mark.asyncio
async def test_assess_regional_stability(geopolitics_agent):
    """Test assessing regional stability."""
    region = "Balkans"
    citations = [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/geopolitics/balkans",
            title="Stability Assessment of the Balkan Region",
            author="Global Affairs Institute",
            publication_date="2000-01-01",
            access_timestamp="2023-01-01T12:00:00",
            excerpt="Analysis of factors affecting stability in the Balkan region...",
        )
    ]
    
    result = await geopolitics_agent.assess_regional_stability(region, citations)
    
    # Verify the result structure
    assert "stability_score" in result
    assert "risk_factors" in result
    assert "protective_factors" in result
    assert "short_term_outlook" in result
    assert "long_term_outlook" in result
    
    # Verify that progress was published
    geopolitics_agent.publish_progress.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_territorial_dispute(geopolitics_agent):
    """Test analyzing a territorial dispute."""
    parties = ["Nation A", "Nation B"]
    territory = "Disputed Islands"
    citations = [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/disputes/islands",
            title="The Disputed Islands Conflict",
            author="Territorial Studies Center",
            publication_date="2005-01-01",
            access_timestamp="2023-01-01T12:00:00",
            excerpt="Analysis of the ongoing territorial dispute over the islands...",
        )
    ]
    
    result = await geopolitics_agent.analyze_territorial_dispute(parties, territory, citations)
    
    # Verify the result structure
    assert "historical_claims" in result
    assert "legal_status" in result
    assert "strategic_importance" in result
    assert "resource_factors" in result
    assert "international_response" in result
    assert "potential_resolutions" in result
    
    # Verify that all parties have historical claims
    for party in parties:
        assert party in result["historical_claims"]
    
    # Verify that progress was published
    geopolitics_agent.publish_progress.assert_called_once()


@pytest.mark.asyncio
async def test_create_geopolitical_memo(geopolitics_agent):
    """Test creating a comprehensive geopolitical memo."""
    topic = "The League of Nations"
    region = "Global"
    citations = [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/league-of-nations",
            title="The League of Nations: Formation and Function",
            author="World Politics Institute",
            publication_date="2005-01-01",
            access_timestamp="2023-01-01T12:00:00",
            excerpt="Analysis of the League of Nations and its role in international affairs...",
        )
    ]
    
    # Mock the analyze_international_relations method to return predetermined data
    geopolitics_agent.analyze_international_relations = AsyncMock(
        return_value={
            "key_players": ["Britain", "France", "United States"],
            "power_dynamics": "Complex balance of power in the post-war period",
            "tensions": ["Territorial settlements", "War reparations", "Colonial mandates"],
            "diplomatic_context": "Diplomatic relations in the aftermath of the Great War",
            "economic_factors": "Economic reconstruction and reparations payments",
            "military_aspects": "Disarmament provisions and enforcement mechanisms",
            "regional_focus": "Global",
            "historical_context": "Created in the aftermath of World War I",
            "cited_sources": [str(citations[0].id)],
        }
    )
    
    result = await geopolitics_agent.create_geopolitical_memo(topic, region, citations)
    
    # Verify that the memo contains expected sections
    assert "INTERNATIONAL PERSPECTIVE ON THE LEAGUE OF NATIONS IN GLOBAL" in result
    assert "diplomatic, economic, and security factors" in result
    assert "Britain" in result
    assert "France" in result
    assert "United States" in result
    assert "Complex balance of power" in result
    assert "Territorial settlements" in result
    assert "War reparations" in result
    assert "Colonial mandates" in result
    assert "Diplomatic Context" in result
    assert "Economic Considerations" in result
    assert "Military & Security Aspects" in result
    assert "Historical Context" in result
    
    # Verify that progress and completion were published
    geopolitics_agent.publish_progress.assert_called_once()
    geopolitics_agent.publish_completion.assert_called_once() 