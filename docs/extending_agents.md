# Extending the FoglioAI Agent Roster

This guide provides instructions for developers who want to create new specialized agents for the FoglioAI system.

## Overview

FoglioAI is built on a flexible agent architecture that allows for easy extension with new specialized agents. Each agent fulfills a unique role in the article generation process, and you can create custom agents for specific domains, perspectives, or functions.

## Agent Types in FoglioAI

The system includes several core agent types:

- **Editor**: Coordinates the article creation process and synthesizes the final output
- **Researcher**: Gathers and analyzes source material
- **Writer**: Crafts narrative content based on research and outlines

And specialized domain agents:

- **Historian**: Provides historical context and analysis
- **Politics-Left**: Delivers progressive political analysis
- **Politics-Right**: Offers conservative political analysis
- **Geopolitics**: Analyzes international relations and global dynamics

## Creating a New Agent

### Step 1: Define Agent Purpose and Capabilities

Before coding, clearly define:

- The agent's specific domain expertise
- Its unique value in the article generation process
- How it will interact with other agents
- What biases it might have (and how to handle them transparently)

### Step 2: Create the Agent Class

1. Create a new file in `app/agents/` named after your agent (e.g., `technology.py` for a Technology agent)

2. Import the necessary dependencies:

```python
from app.agents.base import BaseAgent, AgentConfig
from app.models.agent import AgentRole
```

3. Define your agent class:

```python
class TechnologyAgent(BaseAgent):
    """Technology specialist agent that analyzes tech trends and innovations."""
    
    def __init__(self, article_id):
        """Initialize the Technology agent."""
        config = AgentConfig(
            role=AgentRole.SPECIALIST,
            name="Technology",
            goal="Provide expert analysis on technology trends, innovations, and impacts",
            backstory=(
                "You are a technology analyst with expertise in emerging technologies, "
                "digital transformation, and tech industry dynamics. You have a deep "
                "understanding of how technology affects businesses, society, and everyday life."
            ),
            memory_key=f"technology_agent:{article_id}",
            verbose=True,
            allow_delegation=True,
            can_reflect=True,
            reflection_quality=0.9,
        )
        super().__init__(config, article_id)
    
    async def analyze_tech_trends(self, topic, context=None):
        """Analyze technology trends relevant to the topic."""
        prompt = self._create_tech_trends_prompt(topic, context)
        response = await self._get_llm_response(prompt)
        return response
    
    def _create_tech_trends_prompt(self, topic, context=None):
        """Create a prompt for tech trend analysis."""
        prompt = f"""
        As a technology analyst, provide an insightful analysis of the technological aspects 
        of the following topic: {topic}.
        
        Focus on:
        - Current technological trends relevant to this topic
        - How technology is changing this field
        - Potential future developments
        - Impact of these technologies on businesses and society
        - Ethical considerations and challenges
        
        Base your analysis on factual information and clear reasoning.
        """
        
        if context:
            prompt += f"\n\nAdditional context:\n{context}"
            
        return prompt
    
    async def handle_reflection_request(self, reflection_request):
        """Handle a reflection request from another agent."""
        # Customize reflection handling for technology-specific insights
        prompt = f"""
        As a technology expert, review this content and provide a reflection focusing on:
        - Accuracy of technology claims and predictions
        - Missing technological context or considerations
        - Technical feasibility of described solutions
        - Additional tech trends that should be considered
        
        The content to review:
        {reflection_request.content}
        
        Specific reflection request:
        {reflection_request.prompt}
        """
        
        reflection = await self._get_llm_response(prompt)
        
        await self.submit_reflection(
            reflection_id=reflection_request.reflection_id,
            content=reflection,
            metadata={"domain": "technology", "bias_level": "low"}
        )
```

### Step 3: Add Technology-Specific Methods

Enhance your agent with domain-specific capabilities:

```python
async def evaluate_technical_feasibility(self, solution_description):
    """Evaluate the technical feasibility of a proposed solution."""
    prompt = f"""
    As a technology expert, evaluate the technical feasibility of the following solution:
    
    {solution_description}
    
    Provide an analysis covering:
    1. Technical viability with current technology
    2. Major technical challenges or barriers
    3. Timeline estimation for implementation
    4. Alternative approaches that might be more feasible
    5. Required technology stack or infrastructure
    
    Be specific and provide reasoning for your assessment.
    """
    
    response = await self._get_llm_response(prompt)
    return response

async def predict_tech_evolution(self, technology, timeframe="5 years"):
    """Predict how a specific technology will evolve in the given timeframe."""
    prompt = f"""
    As a technology forecaster, predict how {technology} will likely evolve over the next {timeframe}.
    
    Include:
    - Key improvement areas
    - Potential breakthroughs
    - Adoption patterns
    - Market impacts
    - Societal implications
    
    Base your predictions on current trends, research directions, and historical patterns of technology evolution.
    """
    
    response = await self._get_llm_response(prompt)
    return response
```

### Step 4: Register the Agent

1. Add your agent to `app/agents/__init__.py`:

```python
from .technology import TechnologyAgent

__all__ = [
    # Existing agents
    "BaseAgent",
    "EditorAgent",
    "ResearcherAgent",
    "WriterAgent",
    "HistorianAgent",
    "PoliticsLeftAgent",
    "PoliticsRightAgent",
    "GeopoliticsAgent",
    # New agent
    "TechnologyAgent",
]
```

2. Update the `ArticleOrchestrator` to include your agent:

```python
# In app/agents/orchestrator.py

from .technology import TechnologyAgent

# In the ArticleOrchestrator._initialize_agents method
def _initialize_agents(self):
    """Initialize all agents for the orchestration."""
    self.agent_map = {
        # Existing agents
        "Chief Editor": EditorAgent(self.article_id),
        "Researcher": ResearcherAgent(self.article_id),
        "Writer": WriterAgent(self.article_id),
        "Historian": HistorianAgent(self.article_id),
        "Politics-Left": PoliticsLeftAgent(self.article_id),
        "Politics-Right": PoliticsRightAgent(self.article_id),
        "Geopolitics": GeopoliticsAgent(self.article_id),
        # New agent
        "Technology": TechnologyAgent(self.article_id),
    }
```

3. Add topic detection for your agent:

```python
# In app/agents/orchestrator.py, _select_agents_for_topic method

def _select_agents_for_topic(self, topic):
    """Select appropriate agents based on the article topic."""
    # Always include these core agents
    selected_agents = {"Chief Editor", "Researcher", "Writer"}
    
    # Add specialized agents based on topic keywords
    if any(keyword in topic.lower() for keyword in [
        "history", "historical", "ancient", "medieval", "century", "dynasty",
        "era", "period", "civilization", "empire"
    ]):
        selected_agents.add("Historian")
    
    # Add technology agent for tech-related topics
    if any(keyword in topic.lower() for keyword in [
        "technology", "tech", "digital", "software", "hardware", "ai", 
        "artificial intelligence", "blockchain", "crypto", "computer",
        "innovation", "startup", "app", "automation", "robot"
    ]):
        selected_agents.add("Technology")
    
    # Existing topic detection logic...
    
    return selected_agents
```

## Handling Agent Interactions and Bias

When creating specialized agents, consider how they will interact with other agents, especially during the reflection phase.

### Bias Management

If your agent represents a specific perspective that may have inherent biases:

1. Add explicit bias markers in the agent's responses:
   - Use `[BIAS-TECH]` or similar markers to indicate technology-centric bias
   - Include balanced considerations when possible

2. Implement specific reflection handling:

```python
async def handle_reflection_request(self, reflection_request):
    """Handle reflection requests with awareness of potential techno-optimism bias."""
    prompt = f"""
    Review the following content as a technology expert. Be aware of potential techno-optimism bias 
    (the tendency to overestimate the positive impacts of technology and underestimate challenges).
    
    Content: {reflection_request.content}
    
    Provide a balanced reflection that:
    1. Acknowledges both opportunities and challenges
    2. Considers societal impacts beyond technical feasibility
    3. Addresses potential implementation barriers
    4. Notes where technological solutions may not be sufficient alone
    
    Mark any statements that might reflect techno-optimism bias with [BIAS-TECH].
    """
    
    reflection = await self._get_llm_response(prompt)
    await self.submit_reflection(reflection_request.reflection_id, reflection)
```

### Inter-agent Communication

For effective collaboration with other agents:

1. Implement specialized memo types for technical analysis
2. Add methods to request technical evaluation from other agents
3. Create specific response formats for technical questions

Example:

```python
async def request_technical_evaluation(self, content, question):
    """Request technical evaluation from the Technology agent."""
    memo_id = uuid.uuid4()
    reflection_id = await self.request_reflection(
        memo_id=memo_id,
        content=content,
        target_agent_id="Technology",
        prompt=f"Technical Question: {question}",
        priority=ReflectionPriority.HIGH,
    )
    return reflection_id
```

## Testing Your New Agent

Create comprehensive tests for your agent:

1. Create a test file in `tests/agents/test_technology.py`:

```python
"""Tests for the Technology agent."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.technology import TechnologyAgent


@pytest.fixture
def technology_agent():
    """Create a Technology agent for testing."""
    article_id = uuid.uuid4()
    return TechnologyAgent(article_id)


@pytest.mark.asyncio
async def test_analyze_tech_trends(technology_agent):
    """Test tech trend analysis."""
    with patch.object(technology_agent, "_get_llm_response", AsyncMock(return_value="Analysis content")):
        result = await technology_agent.analyze_tech_trends("AI in healthcare")
        assert result == "Analysis content"
        technology_agent._get_llm_response.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_technical_feasibility(technology_agent):
    """Test technical feasibility evaluation."""
    with patch.object(technology_agent, "_get_llm_response", AsyncMock(return_value="Feasibility analysis")):
        result = await technology_agent.evaluate_technical_feasibility("Quantum computing for drug discovery")
        assert result == "Feasibility analysis"
        technology_agent._get_llm_response.assert_called_once()
```

2. Add integration tests in `tests/integration/test_technology_agent.py`:

```python
"""Integration tests for the Technology agent with other agents."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.technology import TechnologyAgent
from app.agents.editor import EditorAgent
from app.models.article import Article
from app.pubsub.scratchpad import Message, MessageType, ReflectionRequest


@pytest.mark.asyncio
async def test_technology_agent_reflection():
    """Test the Technology agent can provide reflections on content."""
    article_id = uuid.uuid4()
    technology_agent = TechnologyAgent(article_id)
    
    # Mock the LLM and scratchpad
    with patch.object(technology_agent, "_get_llm_response", AsyncMock(return_value="Technical reflection content")), \
         patch.object(technology_agent, "submit_reflection", AsyncMock()):
        
        # Create a reflection request
        reflection_request = ReflectionRequest(
            reflection_id=uuid.uuid4(),
            article_id=article_id,
            memo_id=uuid.uuid4(),
            source_agent_id="Chief Editor",
            target_agent_id="Technology",
            content="Content about AI replacing jobs",
            prompt="Evaluate the technical accuracy and balance of this content",
        )
        
        # Handle the reflection request
        await technology_agent.handle_reflection_request(reflection_request)
        
        # Verify the reflection was submitted
        technology_agent.submit_reflection.assert_called_once()
        technology_agent._get_llm_response.assert_called_once()
```

## Best Practices

### Agent Prompting

1. **Be specific about domain**: Clearly define the agent's expertise area
2. **Ensure factual grounding**: Encourage citation of sources and factual reasoning
3. **Handle uncertainty**: Teach the agent to express confidence levels appropriately
4. **Maintain voice consistency**: Keep a consistent tone and style across responses

### Agent Integration

1. **Keep role definitions focused**: Each agent should have a clear, unique purpose
2. **Ensure complementary capabilities**: New agents should add value without redundancy
3. **Define reflection priorities**: Consider which agents should reflect on your agent's content
4. **Document bias handling**: Make explicit how potential biases are marked and addressed

### Performance Considerations

1. **Monitor token usage**: Specialized agents can increase overall token consumption
2. **Consider selective activation**: Only activate domain-specific agents when relevant
3. **Optimize prompts**: Keep prompts concise and focused to reduce token usage
4. **Cache domain knowledge**: Use agent memory for frequently accessed domain information

## Example: Complete TechnologyAgent Implementation

```python
"""Technology specialist agent implementation."""
import uuid
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent, AgentConfig
from app.models.agent import AgentRole
from app.pubsub.scratchpad import ReflectionPriority, ReflectionRequest


class TechnologyAgent(BaseAgent):
    """Technology specialist agent that analyzes tech trends and innovations."""
    
    def __init__(self, article_id):
        """Initialize the Technology agent."""
        config = AgentConfig(
            role=AgentRole.SPECIALIST,
            name="Technology",
            goal="Provide expert analysis on technology trends, innovations, and impacts",
            backstory=(
                "You are a technology analyst with expertise in emerging technologies, "
                "digital transformation, and tech industry dynamics. You have a deep "
                "understanding of how technology affects businesses, society, and everyday life."
            ),
            memory_key=f"technology_agent:{article_id}",
            verbose=True,
            allow_delegation=True,
            can_reflect=True,
            reflection_quality=0.9,
        )
        super().__init__(config, article_id)
    
    async def analyze_tech_trends(self, topic, context=None):
        """Analyze technology trends relevant to the topic."""
        prompt = self._create_tech_trends_prompt(topic, context)
        response = await self._get_llm_response(prompt)
        return response
    
    def _create_tech_trends_prompt(self, topic, context=None):
        """Create a prompt for tech trend analysis."""
        prompt = f"""
        As a technology analyst, provide an insightful analysis of the technological aspects 
        of the following topic: {topic}.
        
        Focus on:
        - Current technological trends relevant to this topic
        - How technology is changing this field
        - Potential future developments
        - Impact of these technologies on businesses and society
        - Ethical considerations and challenges
        
        Base your analysis on factual information and clear reasoning.
        Mark any statements that might reflect techno-optimism bias with [BIAS-TECH].
        """
        
        if context:
            prompt += f"\n\nAdditional context:\n{context}"
            
        return prompt
    
    async def evaluate_technical_feasibility(self, solution_description):
        """Evaluate the technical feasibility of a proposed solution."""
        prompt = f"""
        As a technology expert, evaluate the technical feasibility of the following solution:
        
        {solution_description}
        
        Provide an analysis covering:
        1. Technical viability with current technology
        2. Major technical challenges or barriers
        3. Timeline estimation for implementation
        4. Alternative approaches that might be more feasible
        5. Required technology stack or infrastructure
        
        Be specific and provide reasoning for your assessment.
        Mark any statements that might reflect techno-optimism bias with [BIAS-TECH].
        """
        
        response = await self._get_llm_response(prompt)
        return response
    
    async def predict_tech_evolution(self, technology, timeframe="5 years"):
        """Predict how a specific technology will evolve in the given timeframe."""
        prompt = f"""
        As a technology forecaster, predict how {technology} will likely evolve over the next {timeframe}.
        
        Include:
        - Key improvement areas
        - Potential breakthroughs
        - Adoption patterns
        - Market impacts
        - Societal implications
        
        Base your predictions on current trends, research directions, and historical patterns of technology evolution.
        Mark any statements that might reflect techno-optimism bias with [BIAS-TECH].
        """
        
        response = await self._get_llm_response(prompt)
        return response
    
    async def handle_reflection_request(self, reflection_request):
        """Handle a reflection request from another agent."""
        prompt = f"""
        As a technology expert, review this content and provide a reflection focusing on:
        - Accuracy of technology claims and predictions
        - Missing technological context or considerations
        - Technical feasibility of described solutions
        - Additional tech trends that should be considered
        
        The content to review:
        {reflection_request.content}
        
        Specific reflection request:
        {reflection_request.prompt}
        
        Be balanced in your assessment. Consider both opportunities and challenges.
        Note where technological solutions may not be sufficient alone.
        Mark any statements that might reflect techno-optimism bias with [BIAS-TECH].
        """
        
        reflection = await self._get_llm_response(prompt)
        
        # Extract bias metrics
        bias_level = 0.1  # Default low bias assumption
        if "[BIAS-TECH]" in reflection:
            # If bias markers are present, increase the bias score
            bias_level = 0.4  # Moderate bias
            
        await self.submit_reflection(
            reflection_id=reflection_request.reflection_id,
            content=reflection,
            metadata={
                "domain": "technology",
                "bias_score": bias_level,
                "bias_type": "techno-optimism" if bias_level > 0.2 else "balanced",
                "quality": 0.85,
            }
        )
    
    async def generate_memo(self, article_topic, research_context=None):
        """Generate a technology analysis memo for the article topic."""
        if research_context:
            prompt = f"""
            As a technology expert, analyze the following topic from a technological perspective:
            
            Topic: {article_topic}
            
            Research context:
            {research_context}
            
            Provide a comprehensive technology analysis that covers:
            1. Current state of technology in this area
            2. Key technological trends and innovations
            3. Future technological developments
            4. Societal and ethical implications
            5. Technical challenges and limitations
            
            Maintain a balanced perspective, acknowledging both benefits and challenges.
            Mark any statements that might reflect techno-optimism bias with [BIAS-TECH].
            
            Format your response as a cohesive memo that could be integrated into a newspaper article.
            """
        else:
            prompt = f"""
            As a technology expert, analyze the following topic from a technological perspective:
            
            Topic: {article_topic}
            
            Provide a comprehensive technology analysis that covers:
            1. Current state of technology in this area
            2. Key technological trends and innovations
            3. Future technological developments
            4. Societal and ethical implications
            5. Technical challenges and limitations
            
            Maintain a balanced perspective, acknowledging both benefits and challenges.
            Mark any statements that might reflect techno-optimism bias with [BIAS-TECH].
            
            Format your response as a cohesive memo that could be integrated into a newspaper article.
            """
        
        memo_content = await self._get_llm_response(prompt)
        
        # Track the memo in the agent's memory
        memo_id = await self._store_memo(memo_content)
        
        return {
            "memo": memo_content,
            "memo_id": str(memo_id),
            "agent_id": self.config.name,
        }
```

## Conclusion

Creating new specialized agents allows you to extend FoglioAI's capabilities for specific domains and use cases. By following this guide, you can implement agents that seamlessly integrate with the existing architecture while adding unique value to the article generation process. 