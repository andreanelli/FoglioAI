"""Tests for agent reflection capabilities."""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents import AgentConfig, BaseAgent
from app.models.agent import AgentRole
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
def base_agent(mock_redis_client, mock_scratchpad):
    """Fixture for creating a basic agent for testing."""
    article_id = uuid.uuid4()
    config = AgentConfig(
        role=AgentRole.EDITOR,
        name="Test Agent",
        goal="Test reflection capabilities",
        backstory="A test agent for reflection capabilities",
        memory_key="test_memory",
        verbose=True,
        allow_delegation=True,
        can_reflect=True,
        reflection_quality=0.9,
    )
    agent = BaseAgent(config, article_id)
    yield agent


@pytest.mark.asyncio
async def test_request_reflection(base_agent, mock_scratchpad):
    """Test requesting a reflection from another agent."""
    memo_id = uuid.uuid4()
    content = "Test content for reflection"
    target_agent_id = "Target Agent"
    prompt = "Please provide reflection on this content"
    
    # Set the return value for the request_reflection method
    expected_reflection_id = uuid.uuid4()
    mock_scratchpad.request_reflection.return_value = expected_reflection_id
    
    # Request reflection
    reflection_id = await base_agent.request_reflection(
        memo_id=memo_id,
        content=content,
        target_agent_id=target_agent_id,
        prompt=prompt,
        priority=ReflectionPriority.HIGH,
    )
    
    # Verify that the request_reflection method was called with correct parameters
    mock_scratchpad.request_reflection.assert_called_once_with(
        article_id=base_agent.article_id,
        memo_id=memo_id,
        source_agent_id=base_agent.config.name,
        target_agent_id=target_agent_id,
        content=content,
        prompt=prompt,
        priority=ReflectionPriority.HIGH,
        deadline=None,
    )
    
    # Verify that the reflection ID is stored in pending requests
    assert reflection_id == expected_reflection_id
    assert reflection_id in base_agent._pending_reflection_requests


@pytest.mark.asyncio
async def test_request_reflections_from_multiple_agents(base_agent, mock_scratchpad):
    """Test requesting reflections from multiple agents."""
    memo_id = uuid.uuid4()
    content = "Test content for multiple reflections"
    target_agent_ids = ["Agent1", "Agent2", "Agent3"]
    prompt = "Please provide reflection on this content"
    
    # Set up return values for each request
    expected_reflection_ids = [uuid.uuid4() for _ in range(len(target_agent_ids))]
    mock_scratchpad.request_reflection.side_effect = expected_reflection_ids
    
    # Request reflections
    reflection_ids = await base_agent.request_reflections_from_multiple_agents(
        memo_id=memo_id,
        content=content,
        target_agent_ids=target_agent_ids,
        prompt=prompt,
    )
    
    # Verify that request_reflection was called for each agent
    assert mock_scratchpad.request_reflection.call_count == len(target_agent_ids)
    
    # Verify that all reflection IDs are returned and stored in pending requests
    assert len(reflection_ids) == len(target_agent_ids)
    for reflection_id in reflection_ids:
        assert reflection_id in base_agent._pending_reflection_requests


@pytest.mark.asyncio
async def test_submit_reflection(base_agent, mock_scratchpad):
    """Test submitting a reflection in response to a request."""
    reflection_id = uuid.uuid4()
    content = "This is my reflection on the provided content"
    metadata = {"quality": 0.8, "bias": 0.2}
    
    # Submit reflection
    await base_agent.submit_reflection(
        reflection_id=reflection_id,
        content=content,
        metadata=metadata,
    )
    
    # Verify that submit_reflection was called with correct parameters
    mock_scratchpad.submit_reflection.assert_called_once_with(
        reflection_id=reflection_id,
        agent_id=base_agent.config.name,
        content=content,
        metadata=metadata,
    )


@pytest.mark.asyncio
async def test_skip_reflection(base_agent, mock_scratchpad):
    """Test skipping a reflection request."""
    reflection_id = uuid.uuid4()
    reason = "Agent is busy with other tasks"
    
    # Skip reflection
    await base_agent.skip_reflection(
        reflection_id=reflection_id,
        reason=reason,
    )
    
    # Verify that mark_reflection_skipped was called with correct parameters
    mock_scratchpad.mark_reflection_skipped.assert_called_once_with(
        reflection_id=reflection_id,
        reason=reason,
    )


@pytest.mark.asyncio
async def test_get_pending_reflections(base_agent, mock_scratchpad):
    """Test getting pending reflection requests."""
    # Set up return value for get_pending_reflections
    expected_reflections = [
        ReflectionRequest(
            article_id=base_agent.article_id,
            memo_id=uuid.uuid4(),
            source_agent_id="Source Agent",
            target_agent_id=base_agent.config.name,
            content="Content for reflection",
            prompt="Please reflect on this",
        )
    ]
    mock_scratchpad.get_pending_reflections.return_value = expected_reflections
    
    # Get pending reflections
    reflections = await base_agent.get_pending_reflections()
    
    # Verify that get_pending_reflections was called with correct parameters
    mock_scratchpad.get_pending_reflections.assert_called_once_with(base_agent.config.name)
    
    # Verify that the expected reflections are returned
    assert reflections == expected_reflections


def test_handle_reflection_request(base_agent, mock_scratchpad):
    """Test handling a reflection request message."""
    reflection_id = uuid.uuid4()
    memo_id = uuid.uuid4()
    source_agent_id = "Source Agent"
    content = "Content for reflection"
    prompt = "Please reflect on this"
    
    # Create a mock reflection callback
    mock_callback = MagicMock()
    base_agent.set_reflection_callback(mock_callback)
    
    # Create a reflection request message
    message = Message(
        type=MessageType.REFLECTION_REQUEST,
        agent_id=source_agent_id,
        article_id=base_agent.article_id,
        reflection_id=reflection_id,
        target_agent_id=base_agent.config.name,
        content={
            "memo_id": str(memo_id),
            "content": content,
            "prompt": prompt,
        },
    )
    
    # Handle the message
    base_agent._handle_message(message)
    
    # Verify that the callback was called with a ReflectionRequest object
    mock_callback.assert_called_once()
    request_arg = mock_callback.call_args[0][0]
    assert isinstance(request_arg, ReflectionRequest)
    assert request_arg.reflection_id == reflection_id
    assert request_arg.memo_id == memo_id
    assert request_arg.source_agent_id == source_agent_id
    assert request_arg.target_agent_id == base_agent.config.name
    assert request_arg.content == content
    assert request_arg.prompt == prompt


def test_handle_reflection_response(base_agent):
    """Test handling a reflection response message."""
    reflection_id = uuid.uuid4()
    memo_id = uuid.uuid4()
    source_agent_id = "Source Agent"
    reflection_content = "This is my reflection on the content"
    
    # Add the reflection ID to pending requests
    base_agent._pending_reflection_requests.add(reflection_id)
    
    # Create a reflection response message
    message = Message(
        type=MessageType.REFLECTION_RESPONSE,
        agent_id=source_agent_id,
        article_id=base_agent.article_id,
        reflection_id=reflection_id,
        target_agent_id=base_agent.config.name,
        content={
            "memo_id": str(memo_id),
            "reflection": reflection_content,
        },
    )
    
    # Handle the message
    base_agent._handle_message(message)
    
    # Verify that the reflection is stored and removed from pending
    assert reflection_id not in base_agent._pending_reflection_requests
    assert reflection_id in base_agent._reflection_responses
    feedback = base_agent._reflection_responses[reflection_id]
    assert feedback.reflection_id == reflection_id
    assert feedback.memo_id == memo_id
    assert feedback.source_agent_id == source_agent_id
    assert feedback.content == reflection_content


def test_handle_reflection_error(base_agent):
    """Test handling a reflection error message."""
    reflection_id = uuid.uuid4()
    error_message = "Failed to generate reflection due to an error"
    
    # Add the reflection ID to pending requests
    base_agent._pending_reflection_requests.add(reflection_id)
    
    # Create a reflection error message
    message = Message(
        type=MessageType.REFLECTION_ERROR,
        agent_id="Source Agent",
        article_id=base_agent.article_id,
        reflection_id=reflection_id,
        target_agent_id=base_agent.config.name,
        content={
            "error": error_message,
        },
    )
    
    # Handle the message
    base_agent._handle_message(message)
    
    # Verify that the reflection is removed from pending
    assert reflection_id not in base_agent._pending_reflection_requests
    assert reflection_id not in base_agent._reflection_responses


def test_get_reflection_feedback(base_agent):
    """Test getting reflection feedback."""
    # Create some test reflection feedback
    memo_id_1 = uuid.uuid4()
    memo_id_2 = uuid.uuid4()
    
    feedback_1 = {
        "reflection_id": uuid.uuid4(),
        "memo_id": memo_id_1,
        "source_agent_id": "Agent1",
        "content": "Reflection 1",
        "metadata": {},
        "timestamp": 123.45,
    }
    
    feedback_2 = {
        "reflection_id": uuid.uuid4(),
        "memo_id": memo_id_1,
        "source_agent_id": "Agent2",
        "content": "Reflection 2",
        "metadata": {},
        "timestamp": 123.46,
    }
    
    feedback_3 = {
        "reflection_id": uuid.uuid4(),
        "memo_id": memo_id_2,
        "source_agent_id": "Agent3",
        "content": "Reflection 3",
        "metadata": {},
        "timestamp": 123.47,
    }
    
    # Add feedback to the agent
    base_agent._reflection_responses[feedback_1["reflection_id"]] = MagicMock(**feedback_1)
    base_agent._reflection_responses[feedback_2["reflection_id"]] = MagicMock(**feedback_2)
    base_agent._reflection_responses[feedback_3["reflection_id"]] = MagicMock(**feedback_3)
    
    # Get all feedback
    all_feedback = base_agent.get_reflection_feedback()
    assert len(all_feedback) == 3
    
    # Get feedback for memo_id_1
    memo_1_feedback = base_agent.get_reflection_feedback(memo_id_1)
    assert len(memo_1_feedback) == 2
    assert all(f.memo_id == memo_id_1 for f in memo_1_feedback)
    
    # Get feedback for memo_id_2
    memo_2_feedback = base_agent.get_reflection_feedback(memo_id_2)
    assert len(memo_2_feedback) == 1
    assert memo_2_feedback[0].memo_id == memo_id_2


def test_has_pending_reflections(base_agent):
    """Test checking if agent has pending reflections."""
    # Initially no pending reflections
    assert not base_agent.has_pending_reflections()
    
    # Add a pending reflection
    base_agent._pending_reflection_requests.add(uuid.uuid4())
    assert base_agent.has_pending_reflections()


def test_get_reflection_status(base_agent):
    """Test getting reflection status."""
    # Add some pending and completed reflections
    base_agent._pending_reflection_requests.add(uuid.uuid4())
    base_agent._pending_reflection_requests.add(uuid.uuid4())
    
    reflection_id_1 = uuid.uuid4()
    reflection_id_2 = uuid.uuid4()
    reflection_id_3 = uuid.uuid4()
    
    base_agent._reflection_responses[reflection_id_1] = MagicMock()
    base_agent._reflection_responses[reflection_id_2] = MagicMock()
    base_agent._reflection_responses[reflection_id_3] = MagicMock()
    
    # Get status
    status = base_agent.get_reflection_status()
    assert status["pending"] == 2
    assert status["completed"] == 3 