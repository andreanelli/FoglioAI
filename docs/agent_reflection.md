# Agent Reflection and Bias Balancing in FoglioAI

This document details the implementation of the expanded agent roster and reflection loop in FoglioAI, which enables agents to critique each other's work and allows for bias detection and balancing.

## Expanded Agent Roster

FoglioAI now includes specialized agents beyond the core Researcher, Writer, and Editor:

### Historian Agent

The Historian agent provides historical context and analysis for articles. It specializes in:
- Analyzing historical trends and precedents
- Providing chronological context
- Identifying historical parallels
- Explaining the evolution of situations over time
- Adding depth to contemporary topics by connecting them to historical events

### Politics Agents

Two complementary political analysis agents bring different perspectives:

#### Politics-Left Agent
- Provides progressive and left-leaning political analysis
- Emphasizes social justice, equality, environmental concerns, and collective welfare
- Marks its own bias with [BIAS-L] indicators for transparency
- Specializes in issues like social programs, income inequality, and regulatory approaches

#### Politics-Right Agent
- Provides conservative and right-leaning political analysis
- Emphasizes free markets, individual liberty, tradition, and limited government
- Marks its own bias with [BIAS-R] indicators for transparency
- Specializes in issues like economic growth, deregulation, and private sector innovation

### Geopolitics Agent

The Geopolitics agent analyzes international relations and global dynamics:
- Examines cross-border issues and regional tensions
- Analyzes power dynamics between nations
- Provides context on treaties, trade agreements, and international organizations
- Evaluates global implications of local events
- Offers insights on different regional perspectives

## Reflection Loop Architecture

The reflection loop allows agents to critique each other's work and improve the overall article quality through multiple perspectives.

### Key Components

1. **Enhanced Redis Scratchpad**
   - New message types: `REFLECTION_REQUEST`, `REFLECTION_RESPONSE`, `REFLECTION_ERROR`
   - ReflectionRequest model for tracking request metadata and status
   - ReflectionTracker for managing the reflection queue
   - Priority-based reflection scheduling (`HIGH`, `MEDIUM`, `LOW`)
   - Status tracking (`PENDING`, `IN_PROGRESS`, `COMPLETED`, `SKIPPED`, `FAILED`)

2. **BaseAgent Reflection Capabilities**
   - Methods for requesting reflections on memos
   - Callbacks for handling reflection requests
   - Reflection request and response handling
   - Quality assessment of reflections
   - Prioritization of feedback

3. **Editor Agent Enhanced Role**
   - ReflectionConfig class for customization
   - Reflection coordination logic
   - Agent selection for reflection based on expertise and opposing viewpoints
   - Reflection scheduling mechanism
   - Feedback integration into final synthesis
   - Phase management (drafting → reflecting → synthesizing)

4. **Orchestrator Integration**
   - Flow management through the entire reflection process
   - Agent selection based on topic relevance
   - Reflection phase scheduling
   - Progress tracking and status reporting

## Reflection Process Flow

1. **Drafting Phase**
   - Agents create initial memos based on their expertise
   - Memos are stored with agent attribution and metadata

2. **Reflection Planning**
   - Editor analyzes memos to identify which need reflection
   - Creates a reflection plan with opposing viewpoints prioritized
   - Example: Left-leaning political memos are reviewed by the Right-leaning agent and vice versa

3. **Reflection Requests**
   - Editor issues reflection requests with priorities
   - Requests include memo content, prompts for reflection, and metadata
   - Agents receive requests in their queue

4. **Reflection Generation**
   - Agents analyze assigned memos
   - Identify bias, factual issues, or perspective limitations
   - Generate constructive critique with suggested improvements
   - Submit reflections with quality and bias metadata

5. **Feedback Integration**
   - Editor evaluates reflection quality
   - Incorporates high-quality reflections into synthesis
   - Low-quality reflections may be discarded or de-prioritized

6. **Article Synthesis**
   - Editor creates final article incorporating reflection feedback
   - Balances perspectives based on bias analysis
   - Ensures fair representation of different viewpoints

## Bias Detection and Balancing

FoglioAI implements a sophisticated bias detection and balancing system to ensure fair coverage of topics.

### Bias Types

The system can detect multiple types of bias:
- `POLITICAL_LEFT` / `POLITICAL_RIGHT`: Political orientation
- `ECONOMIC_PROGRESSIVE` / `ECONOMIC_CONSERVATIVE`: Economic policy perspectives
- `SOCIAL_PROGRESSIVE` / `SOCIAL_CONSERVATIVE`: Social policy perspectives
- `ENVIRONMENTAL_PROGRESSIVE` / `ENVIRONMENTAL_CONSERVATIVE`: Environmental policy perspectives
- `SENSATIONALIST`: Exaggerated or emotionally charged content
- `NEUTRAL`: Balanced or unbiased content

### Bias Detection Process

1. **Content Analysis**
   - BiasDetector class analyzes text for keywords and patterns
   - Checks for explicit bias markers (e.g., [BIAS-L], [BIAS-R])
   - Evaluates linguistic patterns indicating bias
   - Measures sentiment and intensity

2. **Scoring System**
   - BiasLevel enum: `NONE`, `MILD`, `MODERATE`, `STRONG`, `EXTREME`
   - Bias direction: -1.0 (far right) to +1.0 (far left)
   - BiasDetectionResult containing scores, markers, and summary

### Balancing Mechanisms

1. **Article-Level Analysis**
   - ArticleBalancer examines all memos for overall bias
   - Calculates weighted bias scores across agent contributions
   - Generates balance recommendations

2. **Content Rebalancing**
   - Adjusts agent contribution weights based on bias
   - Prioritizes underrepresented perspectives
   - Reorganizes content presentation order
   - Adds editorial notes highlighting different perspectives

3. **Memo-Specific Recommendations**
   - Identifies specific memos that need balancing
   - Suggests specific improvements for each memo
   - Provides customized reflection prompts

4. **Quality Control**
   - Measures final article for bias reduction
   - Ensures multiple perspectives are represented
   - Provides transparency about potential remaining bias

## Extending the Agent Roster

The system is designed for easy extension with new specialized agents:

1. Create a new agent class extending BaseAgent
2. Define appropriate prompts, goals, and backstory
3. Implement specialized methods for the agent's domain
4. Update agent_map in the ArticleOrchestrator
5. Add detection patterns to the topic keyword system

## Best Practices for Agent Reflection

1. **Cross-Perspective Reflection**
   - Always have agents with different perspectives review each other
   - Ensure factual accuracy is prioritized over opinion

2. **Quality Assessment**
   - Set appropriate reflection quality thresholds
   - Monitor reflection quality metrics over time
   - Adjust agent prompts based on reflection performance

3. **Bias Transparency**
   - Ensure bias markers are used consistently
   - Provide clear documentation about potential biases
   - Include bias metadata with article output

4. **Balanced Coverage**
   - Ensure all relevant perspectives are included
   - Verify that no single viewpoint dominates
   - Use ArticleBalancer to measure final balance

## Examples

### Example 1: Reflection Request for Left-Leaning Political Content

```json
{
  "reflection_id": "550e8400-e29b-41d4-a716-446655440000",
  "article_id": "123e4567-e89b-12d3-a456-426614174000",
  "memo_id": "abcdef12-3456-7890-abcd-1234567890ab",
  "source_agent_id": "Chief Editor",
  "target_agent_id": "Politics-Right",
  "content": "Progressive memo content with [BIAS-L] markers...",
  "prompt": "Please analyze this memo for political bias and provide balanced perspective on economic implications.",
  "priority": "HIGH"
}
```

### Example 2: Reflection Response

```json
{
  "reflection_id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "The memo presents important environmental justice concerns but underemphasizes economic transition costs. It would benefit from acknowledging the challenges of rapid implementation in fossil fuel-dependent communities and considering market-based mechanisms alongside regulation.",
  "metadata": {
    "bias_score": -0.2,
    "quality": 0.85,
    "word_count": 427,
    "focus_areas": ["economic policy", "environmental policy"]
  }
}
```

### Example 3: Bias Analysis Output

```json
{
  "overall_bias_direction": 0.1,
  "overall_bias_level": "mild",
  "bias_by_type": {
    "political_left": 0.4,
    "political_right": 0.3,
    "economic_progressive": 0.5,
    "economic_conservative": 0.4
  },
  "bias_by_memo": {
    "memo1_id": {"bias_direction": 0.7, "bias_level": "strong"},
    "memo2_id": {"bias_direction": -0.6, "bias_level": "moderate"}
  },
  "summary": "Article shows slight progressive economic bias but generally balanced political perspective.",
  "recommendations": [
    "Consider adding more market-based solution analysis",
    "Ensure equal space for both regulatory and innovation approaches"
  ]
}
``` 