"""Integration tests for the enhanced orchestrator with reflection capabilities."""
import asyncio
import uuid
from datetime import datetime, timezone, UTC
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.orchestrator import ArticleOrchestrator, OrchestratorConfig
from app.models.agent import AgentRole
from app.models.article import Article
from app.models.article_run import ArticleRunStatus
from app.models.citation import Citation
from app.pubsub.scratchpad import Message, MessageType


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
        "user_query": "Test topic",
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
        topic="Test topic",
        outline=None,
        style_guide={"tone": "modern"},
        status="planning",
    )


@pytest.fixture
def mock_citations():
    """Create mock citations for testing."""
    return [
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/1",
            title="Test Citation 1",
            content="Test content 1",
            publication_date=datetime.now(UTC),
        ),
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/2",
            title="Test Citation 2",
            content="Test content 2",
            publication_date=datetime.now(UTC),
        ),
    ]


@pytest.fixture
def mock_memos():
    """Create mock memos for testing."""
    return [
        {
            "id": str(uuid.uuid4()),
            "agent_id": "Researcher",
            "content": "Research memo content",
            "timestamp": datetime.now(UTC).timestamp(),
        },
        {
            "id": str(uuid.uuid4()),
            "agent_id": "Historian",
            "content": "Historical context memo",
            "timestamp": datetime.now(UTC).timestamp(),
        },
        {
            "id": str(uuid.uuid4()),
            "agent_id": "Politics-Left",
            "content": "Progressive analysis memo",
            "timestamp": datetime.now(UTC).timestamp(),
        },
        {
            "id": str(uuid.uuid4()),
            "agent_id": "Politics-Right",
            "content": "Conservative analysis memo",
            "timestamp": datetime.now(UTC).timestamp(),
        },
    ]


@pytest.mark.asyncio
async def test_agent_selection_for_political_topic(article_id, mock_article_run):
    """Test agent selection for political topics."""
    with patch("app.agents.orchestrator.get_article_run", return_value=mock_article_run), \
         patch("app.agents.orchestrator.save_article_run"), \
         patch("app.agents.base.agent_scratchpad"), \
         patch("app.agents.orchestrator.ArticleOrchestrator._initialize_agents"):
        
        # Initialize orchestrator
        orchestrator = ArticleOrchestrator(article_id)
        
        # Mock agent initialization
        orchestrator._initialize_agents = MagicMock()
        orchestrator.agent_map = {
            "Chief Editor": MagicMock(),
            "Researcher": MagicMock(),
            "Writer": MagicMock(),
            "Historian": MagicMock(),
            "Politics-Left": MagicMock(),
            "Politics-Right": MagicMock(),
            "Geopolitics": MagicMock(),
        }
        
        # Test with political topic
        political_topic = "Analysis of upcoming election and policy implications"
        selected_agents = orchestrator._select_agents_for_topic(political_topic)
        
        # Verify political agents are selected
        assert "Chief Editor" in selected_agents
        assert "Researcher" in selected_agents
        assert "Writer" in selected_agents
        assert "Politics-Left" in selected_agents
        assert "Politics-Right" in selected_agents


@pytest.mark.asyncio
async def test_agent_selection_for_historical_topic(article_id, mock_article_run):
    """Test agent selection for historical topics."""
    with patch("app.agents.orchestrator.get_article_run", return_value=mock_article_run), \
         patch("app.agents.orchestrator.save_article_run"), \
         patch("app.agents.base.agent_scratchpad"), \
         patch("app.agents.orchestrator.ArticleOrchestrator._initialize_agents"):
        
        # Initialize orchestrator
        orchestrator = ArticleOrchestrator(article_id)
        
        # Mock agent initialization
        orchestrator._initialize_agents = MagicMock()
        orchestrator.agent_map = {
            "Chief Editor": MagicMock(),
            "Researcher": MagicMock(),
            "Writer": MagicMock(),
            "Historian": MagicMock(),
            "Politics-Left": MagicMock(),
            "Politics-Right": MagicMock(),
            "Geopolitics": MagicMock(),
        }
        
        # Test with historical topic
        historical_topic = "The medieval history of Europe and its dynasties"
        selected_agents = orchestrator._select_agents_for_topic(historical_topic)
        
        # Verify historian agent is selected
        assert "Chief Editor" in selected_agents
        assert "Researcher" in selected_agents
        assert "Writer" in selected_agents
        assert "Historian" in selected_agents


@pytest.mark.asyncio
async def test_agent_selection_for_international_topic(article_id, mock_article_run):
    """Test agent selection for international topics."""
    with patch("app.agents.orchestrator.get_article_run", return_value=mock_article_run), \
         patch("app.agents.orchestrator.save_article_run"), \
         patch("app.agents.base.agent_scratchpad"), \
         patch("app.agents.orchestrator.ArticleOrchestrator._initialize_agents"):
        
        # Initialize orchestrator
        orchestrator = ArticleOrchestrator(article_id)
        
        # Mock agent initialization
        orchestrator._initialize_agents = MagicMock()
        orchestrator.agent_map = {
            "Chief Editor": MagicMock(),
            "Researcher": MagicMock(),
            "Writer": MagicMock(),
            "Historian": MagicMock(),
            "Politics-Left": MagicMock(),
            "Politics-Right": MagicMock(),
            "Geopolitics": MagicMock(),
        }
        
        # Test with international topic
        international_topic = "Diplomatic relations between nations in the South China Sea"
        selected_agents = orchestrator._select_agents_for_topic(international_topic)
        
        # Verify geopolitics agent is selected
        assert "Chief Editor" in selected_agents
        assert "Researcher" in selected_agents
        assert "Writer" in selected_agents
        assert "Geopolitics" in selected_agents


@pytest.mark.asyncio
async def test_create_drafting_tasks(article_id, mock_article_run, mock_article):
    """Test creation of drafting tasks for various agent combinations."""
    with patch("app.agents.orchestrator.get_article_run", return_value=mock_article_run), \
         patch("app.agents.orchestrator.save_article_run"), \
         patch("app.agents.base.agent_scratchpad"), \
         patch("app.agents.orchestrator.ArticleOrchestrator._initialize_agents"):
        
        # Initialize orchestrator
        orchestrator = ArticleOrchestrator(article_id)
        
        # Mock agent initialization
        orchestrator._initialize_agents = MagicMock()
        orchestrator.agent_map = {
            "Chief Editor": MagicMock(),
            "Researcher": MagicMock(),
            "Writer": MagicMock(),
            "Historian": MagicMock(),
            "Politics-Left": MagicMock(),
            "Politics-Right": MagicMock(),
            "Geopolitics": MagicMock(),
        }
        
        # Test with all agents selected
        orchestrator._selected_agents = {
            "Chief Editor", "Researcher", "Writer", 
            "Historian", "Politics-Left", "Politics-Right", "Geopolitics"
        }
        tasks = orchestrator._create_drafting_tasks(mock_article)
        
        # Verify correct number of tasks
        # 1 research + 4 specialized agents + 1 writer = 6 tasks
        assert len(tasks) == 6
        
        # Verify task descriptions and agents
        task_types = {}
        for task in tasks:
            agent_name = None
            for name, agent in orchestrator.agent_map.items():
                if task.agent == agent:
                    agent_name = name
                    break
            
            task_types[agent_name] = task.description
        
        assert "Researcher" in task_types
        assert "Historian" in task_types
        assert "Politics-Left" in task_types
        assert "Politics-Right" in task_types
        assert "Geopolitics" in task_types
        assert "Writer" in task_types


@pytest.mark.asyncio
async def test_reflection_phase(article_id, mock_article_run):
    """Test reflection phase scheduling and completion."""
    with patch("app.agents.orchestrator.get_article_run") as mock_get_run, \
         patch("app.agents.orchestrator.save_article_run"), \
         patch("app.agents.base.agent_scratchpad"), \
         patch("app.agents.orchestrator.asyncio.sleep", return_value=None), \
         patch("app.agents.orchestrator.ArticleOrchestrator._initialize_agents"):
        
        # Configure mock_get_run to return updated article_run with reflection_complete
        def get_article_run_with_reflection():
            mock_article_run["metadata"]["reflection_complete"] = True
            return mock_article_run
        
        mock_get_run.side_effect = [mock_article_run, get_article_run_with_reflection()]
        
        # Initialize orchestrator
        orchestrator = ArticleOrchestrator(article_id)
        orchestrator._initialize_agents = MagicMock()
        
        # Run reflection phase
        await orchestrator._run_reflection_phase()
        
        # Verify reflection phase is marked as complete
        assert orchestrator._reflection_phase_complete == True
        assert orchestrator._reflection_in_progress == False


@pytest.mark.asyncio
async def test_synthesis_phase(article_id, mock_article_run, mock_article, mock_memos):
    """Test synthesis phase with bias analysis and content balancing."""
    with patch("app.agents.orchestrator.get_article_run", return_value=mock_article_run), \
         patch("app.agents.orchestrator.save_article_run"), \
         patch("app.agents.orchestrator.get_memos_by_article", return_value=mock_memos), \
         patch("app.agents.base.agent_scratchpad"), \
         patch("app.agents.orchestrator.ArticleOrchestrator._initialize_agents"):
        
        # Mock bias analysis result
        bias_analysis = {
            "direction": 0.3,  # Slightly left-leaning
            "level": "mild",
            "assessment": "The content shows a mild left-leaning bias",
            "levels_by_type": {
                "political_left": "mild",
                "political_right": "none",
                "economic_progressive": "moderate",
                "economic_conservative": "none",
            }
        }
        
        # Mock balanced content
        balanced_content = "This is the balanced article content that incorporates all perspectives fairly."
        
        # Initialize orchestrator
        orchestrator = ArticleOrchestrator(article_id)
        orchestrator._initialize_agents = MagicMock()
        
        # Mock article balancer
        orchestrator.article_balancer = MagicMock()
        orchestrator.article_balancer.analyze_article_bias = AsyncMock(return_value=bias_analysis)
        orchestrator.article_balancer.generate_balanced_content = AsyncMock(return_value=balanced_content)
        
        # Run synthesis phase
        await orchestrator._run_synthesis_phase(mock_article)
        
        # Verify article balancer methods were called
        orchestrator.article_balancer.analyze_article_bias.assert_called_once()
        orchestrator.article_balancer.generate_balanced_content.assert_called_once_with(mock_memos, bias_analysis)
        
        # Verify article content was updated
        assert mock_article.content == balanced_content
        
        # Verify article run was updated with bias analysis
        assert mock_article_run["metadata"]["bias_analysis"] == bias_analysis
        assert "bias_analysis" in mock_article_run["final_output"]


@pytest.mark.asyncio
async def test_get_progress_with_reflection(article_id, mock_article_run):
    """Test progress reporting with reflection status."""
    with patch("app.agents.orchestrator.get_article_run", return_value=mock_article_run), \
         patch("app.agents.orchestrator.save_article_run"), \
         patch("app.agents.base.agent_scratchpad"), \
         patch("app.agents.orchestrator.ArticleOrchestrator._initialize_agents"):
        
        # Initialize orchestrator
        orchestrator = ArticleOrchestrator(article_id)
        orchestrator._initialize_agents = MagicMock()
        
        # Set up test state
        orchestrator._selected_agents = {"Chief Editor", "Researcher", "Writer", "Historian"}
        orchestrator._completed_agents = {"Researcher", "Historian"}
        orchestrator._reflection_phase_complete = True
        
        # Get progress
        progress = orchestrator.get_progress()
        
        # Verify progress includes reflection status
        assert progress["reflection_status"] == "completed"
        assert progress["completed_tasks"] == 3  # 2 agents + reflection phase
        assert progress["total_tasks"] == 6  # 4 agents + reflection + synthesis
        
        # Test with reflection in progress
        orchestrator._reflection_phase_complete = False
        orchestrator._reflection_in_progress = True
        
        progress = orchestrator.get_progress()
        assert progress["reflection_status"] == "in_progress"


@pytest.mark.asyncio
async def test_get_metrics(article_id, mock_article_run):
    """Test metrics reporting for the article generation process."""
    with patch("app.agents.orchestrator.get_article_run", return_value=mock_article_run), \
         patch("app.agents.orchestrator.save_article_run"), \
         patch("app.agents.base.agent_scratchpad"), \
         patch("app.agents.orchestrator.ArticleOrchestrator._initialize_agents"):
        
        # Initialize orchestrator
        orchestrator = ArticleOrchestrator(article_id)
        orchestrator._initialize_agents = MagicMock()
        
        # Add test data
        orchestrator._selected_agents = {"Chief Editor", "Researcher", "Writer", "Historian", "Politics-Left", "Politics-Right"}
        
        # Add reflection data to article_run
        mock_article_run["metadata"]["reflections"] = {
            "memo1": [{"reflection": "r1"}, {"reflection": "r2"}],
            "memo2": [{"reflection": "r3"}],
        }
        
        # Add bias analysis
        mock_article_run["metadata"]["bias_analysis"] = {
            "levels_by_type": {
                "political_left": "mild",
                "political_right": "none",
            }
        }
        
        # Add timestamps
        mock_article_run["created_at"] = datetime.now(UTC).replace(hour=10, minute=0, second=0)
        mock_article_run["completed_at"] = datetime.now(UTC).replace(hour=10, minute=5, second=0)
        
        # Get metrics
        metrics = orchestrator.get_metrics()
        
        # Verify metrics include expected data
        assert metrics["agent_count"] == 6
        assert metrics["reflection_count"] == 3
        assert "political_left" in metrics["bias_levels"]
        assert metrics["generation_time"] == 300  # 5 minutes = 300 seconds


@pytest.mark.asyncio
async def test_complete_article_generation_workflow(article_id, mock_article_run, mock_article):
    """Test the complete article generation workflow with reflection."""
    with patch("app.agents.orchestrator.get_article_run", return_value=mock_article_run), \
         patch("app.agents.orchestrator.save_article_run"), \
         patch("app.agents.base.agent_scratchpad"), \
         patch("app.agents.orchestrator.ArticleOrchestrator._initialize_agents"), \
         patch("app.agents.orchestrator.ArticleOrchestrator._select_agents_for_topic") as mock_select, \
         patch("app.agents.orchestrator.ArticleOrchestrator._create_drafting_tasks") as mock_create_tasks, \
         patch("app.agents.orchestrator.ArticleOrchestrator._run_reflection_phase") as mock_reflection, \
         patch("app.agents.orchestrator.ArticleOrchestrator._run_synthesis_phase") as mock_synthesis, \
         patch("crewai.Crew") as mock_crew_cls:
        
        # Initialize orchestrator
        orchestrator = ArticleOrchestrator(article_id)
        orchestrator._initialize_agents = MagicMock()
        orchestrator.editor = MagicMock()
        orchestrator.editor.create_article_outline = MagicMock(return_value=mock_article)
        
        # Configure mocks
        mock_select.return_value = {"Chief Editor", "Researcher", "Writer", "Historian"}
        mock_create_tasks.return_value = [MagicMock(), MagicMock()]
        mock_reflection.return_value = None
        mock_synthesis.return_value = None
        
        # Mock Crew run
        mock_crew = MagicMock()
        mock_crew.run = AsyncMock()
        mock_crew_cls.return_value = mock_crew
        
        # Run the article generation
        topic = "The impact of climate change on global politics"
        style_guide = {"tone": "analytical"}
        article = await orchestrator.generate_article(topic, style_guide)
        
        # Verify all phases were called in order
        mock_select.assert_called_once_with(topic)
        mock_create_tasks.assert_called_once()
        mock_crew.run.assert_called_once()
        mock_reflection.assert_called_once()
        mock_synthesis.assert_called_once_with(mock_article)
        
        # Verify article status updates
        assert mock_article_run["status"] == ArticleStatus.COMPLETED 