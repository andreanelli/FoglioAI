"""Tests for Editor agent reflection capabilities."""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.editor import EditorAgent, ReflectionConfig
from app.models.agent import AgentRole
from app.models.article_run import ArticleStatus
from app.pubsub.scratchpad import (
    Message, 
    MessageType, 
    ReflectionPriority, 
    ReflectionRequest,
    ReflectionStatus,
)


@pytest.fixture
def mock_redis_client():
    """Fixture for mocking the Redis client."""
    with patch("app.agents.base.redis_client") as mock_client:
        # Configure mock
        mock_client.client = MagicMock()
        mock_client.client.json.return_value.set = MagicMock()
        mock_client.client.exists.return_value = False
        yield mock_client


@pytest.fixture
def mock_scratchpad():
    """Fixture for mocking the agent scratchpad."""
    with patch("app.agents.base.agent_scratchpad") as mock_pad:
        # Configure mock methods
        mock_pad.publish_message = AsyncMock()
        mock_pad.request_reflection = AsyncMock(return_value=uuid.uuid4())
        mock_pad.submit_reflection = AsyncMock()
        mock_pad.mark_reflection_skipped = AsyncMock()
        mock_pad.mark_reflection_in_progress = AsyncMock()
        mock_pad.get_pending_reflections = AsyncMock(return_value=[])
        yield mock_pad


@pytest.fixture
def mock_article_run():
    """Fixture for mocking article run functions."""
    article_id = uuid.uuid4()
    article_run = {
        "id": str(article_id),
        "status": "drafting",
        "user_query": "Test article query",
        "agent_outputs": {},
        "citations": [],
        "visuals": [],
        "errors": [],
        "metadata": {},
    }
    
    with patch("app.agents.editor.get_article_run") as mock_get, \
         patch("app.agents.editor.save_article_run") as mock_save:
        mock_get.return_value = article_run
        yield article_run, mock_get, mock_save


@pytest.fixture
def mock_memo_functions():
    """Fixture for mocking memo retrieval functions."""
    with patch("app.agents.editor.get_memo_by_id") as mock_get_by_id, \
         patch("app.agents.editor.get_memos_by_article") as mock_get_by_article:
        
        # Configure mock returns
        mock_memo_id_1 = uuid.uuid4()
        mock_memo_id_2 = uuid.uuid4()
        
        # Sample memos
        memos = [
            {
                "id": str(mock_memo_id_1),
                "article_id": "test_article_id",
                "agent_id": "Politics-Left",
                "content": "This is a test memo from Politics-Left agent.",
                "timestamp": 123456789.0,
            },
            {
                "id": str(mock_memo_id_2),
                "article_id": "test_article_id",
                "agent_id": "Politics-Right",
                "content": "This is a test memo from Politics-Right agent.",
                "timestamp": 123456790.0,
            },
        ]
        
        # Set up returns
        mock_get_by_article.return_value = memos
        
        mock_get_by_id.side_effect = lambda memo_id: next(
            (memo for memo in memos if memo["id"] == str(memo_id)), None
        )
        
        yield mock_get_by_id, mock_get_by_article, memos


@pytest.fixture
def editor_agent(mock_redis_client, mock_scratchpad, mock_article_run):
    """Fixture for creating an Editor agent for testing."""
    article_id = uuid.uuid4()
    agent = EditorAgent(article_id)
    yield agent


@pytest.mark.asyncio
async def test_check_drafting_complete(editor_agent, mock_article_run):
    """Test checking if the drafting phase is complete."""
    article_run, _, _ = mock_article_run
    
    # Initially, no agents have completed
    assert not editor_agent._check_drafting_complete()
    
    # Add some agent outputs but not all required ones
    article_run["agent_outputs"] = {
        "Researcher": {"memo": "Test memo"},
        "Writer": {"memo": "Test memo"},
    }
    assert not editor_agent._check_drafting_complete()
    
    # Add all required agent outputs
    article_run["agent_outputs"] = {
        "Researcher": {"memo": "Test memo"},
        "Writer": {"memo": "Test memo"},
        "Historian": {"memo": "Test memo"},
        "Politics-Left": {"memo": "Test memo"},
        "Politics-Right": {"memo": "Test memo"},
        "Geopolitics": {"memo": "Test memo"},
    }
    assert editor_agent._check_drafting_complete()


@pytest.mark.asyncio
async def test_start_reflection_phase(editor_agent, mock_article_run, mock_scratchpad, mock_memo_functions):
    """Test starting the reflection phase."""
    article_run, _, mock_save = mock_article_run
    _, _, memos = mock_memo_functions
    
    # Mock the reflection methods
    editor_agent._create_reflection_plan = MagicMock()
    editor_agent._request_planned_reflections = AsyncMock()
    
    # Start reflection phase
    await editor_agent._start_reflection_phase()
    
    # Verify article status was updated
    assert article_run["status"] == ArticleStatus.REFLECTING
    mock_save.assert_called()
    
    # Verify reflection plan was created
    editor_agent._create_reflection_plan.assert_called_once()
    
    # Verify reflection requests were sent
    editor_agent._request_planned_reflections.assert_called_once()


@pytest.mark.asyncio
async def test_create_reflection_plan(editor_agent, mock_memo_functions):
    """Test creating a reflection plan."""
    _, _, memos = mock_memo_functions
    
    # Create reflection plan
    editor_agent._create_reflection_plan(memos)
    
    # Verify plan structure
    assert isinstance(editor_agent._reflection_plan, dict)
    
    # Check that both memos have reviewers assigned
    assert len(editor_agent._reflection_plan) == 2
    
    # Both memo IDs should be keys in the plan
    memo_ids = [uuid.UUID(memo["id"]) for memo in memos]
    for memo_id in memo_ids:
        assert memo_id in editor_agent._reflection_plan
    
    # Politics-Left memo should have Politics-Right as a reviewer (highest priority)
    politics_left_memo_id = next(
        uuid.UUID(memo["id"]) for memo in memos if memo["agent_id"] == "Politics-Left"
    )
    assert "Politics-Right" in editor_agent._reflection_plan[politics_left_memo_id]
    
    # Politics-Right memo should have Politics-Left as a reviewer (highest priority)
    politics_right_memo_id = next(
        uuid.UUID(memo["id"]) for memo in memos if memo["agent_id"] == "Politics-Right"
    )
    assert "Politics-Left" in editor_agent._reflection_plan[politics_right_memo_id]


@pytest.mark.asyncio
async def test_request_planned_reflections(editor_agent, mock_scratchpad, mock_memo_functions):
    """Test requesting reflections according to the plan."""
    mock_get_by_id, _, memos = mock_memo_functions
    
    # Set up reflection plan
    memo_id_1 = uuid.UUID(memos[0]["id"])
    memo_id_2 = uuid.UUID(memos[1]["id"])
    
    editor_agent._reflection_plan = {
        memo_id_1: ["Politics-Right", "Historian"],
        memo_id_2: ["Politics-Left", "Geopolitics"],
    }
    
    # Request reflections
    await editor_agent._request_planned_reflections()
    
    # Verify reflection requests
    assert mock_scratchpad.request_reflection.call_count == 4  # 2 reviewers for each of 2 memos
    
    # Verify pending reflections
    assert len(editor_agent._pending_reflections) == 4


@pytest.mark.asyncio
async def test_handle_reflection_request(editor_agent, mock_scratchpad):
    """Test handling a reflection request."""
    # Create a reflection request
    memo_id = uuid.uuid4()
    reflection_id = uuid.uuid4()
    source_agent_id = "Researcher"
    content = "Test memo content"
    
    request = ReflectionRequest(
        reflection_id=reflection_id,
        article_id=editor_agent.article_id,
        memo_id=memo_id,
        source_agent_id=source_agent_id,
        target_agent_id="Chief Editor",
        content=content,
    )
    
    # Mock the process function
    editor_agent._process_reflection_request = AsyncMock()
    
    # Handle the request
    editor_agent._handle_reflection_request(request)
    
    # Verify the process function was called
    editor_agent._process_reflection_request.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_process_reflection_request(editor_agent, mock_scratchpad):
    """Test processing a reflection request."""
    # Create a reflection request
    memo_id = uuid.uuid4()
    reflection_id = uuid.uuid4()
    source_agent_id = "Researcher"
    content = "Test memo content"
    
    request = ReflectionRequest(
        reflection_id=reflection_id,
        article_id=editor_agent.article_id,
        memo_id=memo_id,
        source_agent_id=source_agent_id,
        target_agent_id="Chief Editor",
        content=content,
    )
    
    # Mock reflection generation
    expected_reflection = "This is a test reflection"
    editor_agent._generate_reflection_for_memo = AsyncMock(return_value=expected_reflection)
    
    # Process the request
    await editor_agent._process_reflection_request(request)
    
    # Verify reflection was generated
    editor_agent._generate_reflection_for_memo.assert_called_once_with(
        memo_id,
        content,
        None,  # No prompt
    )
    
    # Verify reflection was submitted
    mock_scratchpad.submit_reflection.assert_called_once()
    call_args = mock_scratchpad.submit_reflection.call_args[1]
    assert call_args["reflection_id"] == reflection_id
    assert call_args["agent_id"] == "Chief Editor"
    assert call_args["content"] == expected_reflection


@pytest.mark.asyncio
async def test_handle_reflection_completed(editor_agent, mock_article_run):
    """Test handling a reflection completed message."""
    article_run, _, mock_save = mock_article_run
    
    # Create reflection ID and add to pending
    reflection_id = uuid.uuid4()
    memo_id = uuid.uuid4()
    editor_agent._pending_reflections.add(reflection_id)
    
    # Create a reflection completed message
    message = Message(
        type=MessageType.REFLECTION_COMPLETED,
        agent_id="Politics-Right",
        article_id=editor_agent.article_id,
        reflection_id=reflection_id,
        target_agent_id="Chief Editor",
        content={
            "memo_id": str(memo_id),
            "reflection": "This is a completed reflection",
        },
    )
    
    # Mock finalize function
    editor_agent._finalize_reflection_phase = AsyncMock()
    
    # Handle the message
    editor_agent._handle_reflection_completed(message)
    
    # Verify reflection was removed from pending
    assert reflection_id not in editor_agent._pending_reflections
    
    # Verify reflection was stored in article run
    assert "reflections" in article_run["metadata"]
    assert str(memo_id) in article_run["metadata"]["reflections"]
    assert len(article_run["metadata"]["reflections"][str(memo_id)]) == 1
    
    # Verify article run was saved
    mock_save.assert_called()
    
    # Verify reflection content
    reflection = article_run["metadata"]["reflections"][str(memo_id)][0]
    assert reflection["reflection_id"] == str(reflection_id)
    assert reflection["source_agent_id"] == "Politics-Right"
    assert reflection["content"] == "This is a completed reflection"


@pytest.mark.asyncio
async def test_detect_overall_bias(editor_agent):
    """Test detecting overall bias in reflections."""
    # Create sample reflections
    reflections = {
        "memo1": [
            {
                "content": "This memo shows a left-leaning bias in its analysis of economic policy.",
                "source_agent_id": "Politics-Right",
            },
            {
                "content": "The analysis is balanced and fair in its treatment of the subject.",
                "source_agent_id": "Historian",
            },
        ],
        "memo2": [
            {
                "content": "There is a conservative bias in how this memo frames social issues.",
                "source_agent_id": "Politics-Left",
            },
        ],
    }
    
    # Detect bias
    bias_results = editor_agent._detect_overall_bias(reflections)
    
    # Verify results
    assert "bias_ratio" in bias_results
    assert "assessment" in bias_results
    assert "bias_by_agent" in bias_results
    
    # Check that agents are tracked correctly
    assert "Politics-Right" in bias_results["bias_by_agent"]
    assert "Politics-Left" in bias_results["bias_by_agent"]
    assert "Historian" in bias_results["bias_by_agent"]


@pytest.mark.asyncio
async def test_finalize_reflection_phase(editor_agent, mock_article_run):
    """Test finalizing the reflection phase."""
    article_run, _, mock_save = mock_article_run
    
    # Mock synthesize function
    editor_agent._synthesize_article_with_reflections = AsyncMock()
    
    # Finalize reflection phase
    await editor_agent._finalize_reflection_phase()
    
    # Verify reflection phase marked as complete
    assert editor_agent._reflection_phase_complete
    
    # Verify article status updated
    assert article_run["status"] == ArticleStatus.SYNTHESIZING
    assert article_run["metadata"].get("reflection_complete") is True
    
    # Verify article run was saved
    mock_save.assert_called()
    
    # Verify synthesis was called
    editor_agent._synthesize_article_with_reflections.assert_called_once()


@pytest.mark.asyncio
async def test_synthesize_article_with_reflections(editor_agent, mock_article_run):
    """Test article synthesis with reflections."""
    article_run, _, mock_save = mock_article_run
    
    # Mock bias detection
    bias_results = {
        "bias_ratio": 0.6,
        "assessment": "Relatively balanced coverage",
        "bias_by_agent": {"Politics-Left": {"reflections_given": 1, "bias_mentions": 0}},
    }
    editor_agent._detect_overall_bias = MagicMock(return_value=bias_results)
    
    # Set up reflections in article run
    memo_id = uuid.uuid4()
    article_run["metadata"]["reflections"] = {
        str(memo_id): [
            {
                "reflection_id": str(uuid.uuid4()),
                "source_agent_id": "Politics-Right",
                "content": "This is a reflection",
                "metadata": {},
                "timestamp": 123456789.0,
            }
        ]
    }
    
    # Synthesize article
    await editor_agent._synthesize_article_with_reflections()
    
    # Verify bias detection was called
    editor_agent._detect_overall_bias.assert_called_once()
    
    # Verify bias results stored in article metadata
    assert "bias_assessment" in article_run["metadata"]
    assert article_run["metadata"]["bias_assessment"] == bias_results
    
    # Verify article status updated to completed
    assert article_run["status"] == ArticleStatus.COMPLETED
    
    # Verify article run was saved
    mock_save.assert_called()


@pytest.mark.asyncio
async def test_agent_completion_triggers_reflection(editor_agent, mock_article_run, mock_scratchpad):
    """Test that completing the drafting phase triggers the reflection phase."""
    article_run, _, _ = mock_article_run
    
    # Mock reflection methods
    editor_agent._check_drafting_complete = MagicMock(return_value=True)
    editor_agent._start_reflection_phase = AsyncMock()
    
    # Create completion message
    message = Message(
        type=MessageType.AGENT_COMPLETED,
        agent_id="Geopolitics",
        article_id=editor_agent.article_id,
        content={"memo": "Test memo"},
    )
    
    # Handle message
    editor_agent._handle_agent_completion(message)
    
    # Verify reflection phase was started
    editor_agent._start_reflection_phase.assert_called_once() 