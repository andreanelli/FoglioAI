"""Tests for the Historian agent."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents import HistorianAgent
from app.models.agent import AgentRole
from app.models.citation import Citation


@pytest.fixture
def mock_redis_client():
    """Fixture for mocking the Redis client."""
    with patch("app.agents.historian.redis_client") as mock_client:
        # Configure mock
        mock_client.client = MagicMock()
        mock_client.client.json.return_value.set = AsyncMock()
        mock_client.client.exists.return_value = False
        yield mock_client


@pytest.fixture
def mock_citation_manager():
    """Fixture for mocking the CitationManager."""
    with patch("app.agents.historian.CitationManager") as mock_cm:
        manager_instance = mock_cm.return_value
        yield manager_instance


@pytest.fixture
def historian_agent(mock_redis_client, mock_citation_manager):
    """Fixture for creating a Historian agent for testing."""
    article_id = uuid.uuid4()
    agent = HistorianAgent(article_id=article_id)
    
    # Mock the publish methods to avoid actual Redis operations
    agent.publish_progress = MagicMock()
    agent.publish_completion = MagicMock()
    agent.publish_error = MagicMock()
    
    yield agent


@pytest.mark.asyncio
async def test_historian_init():
    """Test Historian agent initialization."""
    article_id = uuid.uuid4()
    agent = HistorianAgent(article_id=article_id)
    
    assert agent.config.role == AgentRole.HISTORIAN
    assert agent.config.name == "Chief Historian"
    assert agent.article_id == article_id


@pytest.mark.asyncio
async def test_provide_historical_context(historian_agent):
    """Test providing historical context."""
    topic = "The Great Depression"
    citations = [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/history/great-depression",
            title="The Great Depression: Causes and Impact",
            author="John Historian",
            publication_date="1990-01-01",
            access_timestamp="2023-01-01T12:00:00",
            excerpt="The Great Depression was a severe worldwide economic depression...",
        )
    ]
    
    result = await historian_agent.provide_historical_context(topic, citations)
    
    # Verify the result structure
    assert "context" in result
    assert "parallels" in result
    assert "implications" in result
    assert "cited_sources" in result
    
    # Verify that progress and completion were published
    historian_agent.publish_progress.assert_called_once()
    historian_agent.publish_completion.assert_called_once()


@pytest.mark.asyncio
async def test_create_historical_memo(historian_agent):
    """Test creating a historical memo."""
    topic = "World War I Aftermath"
    citations = [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/history/wwi-aftermath",
            title="The Aftermath of the Great War",
            author="Emma Historian",
            publication_date="1995-01-01",
            access_timestamp="2023-01-01T12:00:00",
            excerpt="The aftermath of World War I saw dramatic political, cultural, and social change...",
        )
    ]
    
    # Mock the provide_historical_context method to return predetermined data
    historian_agent.provide_historical_context = AsyncMock(
        return_value={
            "context": "Historical context for World War I Aftermath",
            "parallels": ["Historical parallel 1", "Historical parallel 2"],
            "implications": "Implications based on historical patterns",
            "cited_sources": [str(citations[0].id)],
        }
    )
    
    result = await historian_agent.create_historical_memo(topic, citations)
    
    # Verify that the memo contains expected sections
    assert "HISTORICAL PERSPECTIVE ON WORLD WAR I AFTERMATH" in result
    assert "Historical context for World War I Aftermath" in result
    assert "Historical Parallels:" in result
    assert "Historical parallel 1" in result
    assert "Historical parallel 2" in result
    assert "Implications:" in result
    
    # Verify that progress and completion were published
    historian_agent.publish_progress.assert_called_once()
    historian_agent.publish_completion.assert_called_once() 