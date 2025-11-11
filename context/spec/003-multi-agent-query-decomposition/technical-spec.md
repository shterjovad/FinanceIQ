# Technical Specification: Multi-Agent Query Decomposition

**Feature ID**: 003
**Related Functional Spec**: `functional-spec.md`
**Status**: Planning
**Last Updated**: 2025-11-10

---

## Architecture Overview

This feature introduces a multi-agent orchestration layer using **LangGraph** that sits between the chat interface and the existing RAG query engine. The architecture uses a state machine approach where agents analyze, decompose, execute, and synthesize queries.

```
User Query
    ↓
[Query Router Agent] ← Simple? → [Existing RAG Query Engine] → Answer
    ↓ Complex?
[Query Decomposer Agent]
    ↓
[Sub-Query Executor] (parallel/sequential)
    ↓
[Answer Synthesis Agent]
    ↓
Final Answer + Reasoning Steps
```

---

## LangGraph State Machine Design

### State Schema

```python
from typing import TypedDict, List, Literal

class AgentState(TypedDict):
    """State passed between agents in the LangGraph workflow."""

    # Input
    original_question: str

    # Analysis
    query_type: Literal["simple", "complex"]
    complexity_reasoning: str

    # Decomposition
    sub_queries: List[str]
    execution_order: Literal["parallel", "sequential"]

    # Execution
    sub_results: List[QueryResult]  # From existing RAG

    # Synthesis
    final_answer: str
    all_sources: List[SourceCitation]
    reasoning_steps: List[Dict[str, Any]]

    # Metadata
    processing_time_ms: int
    agent_calls: List[str]
```

### LangGraph Workflow

```python
from langgraph.graph import StateGraph, END

def create_agent_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)

    # Add nodes (agents)
    workflow.add_node("router", query_router_agent)
    workflow.add_node("decomposer", query_decomposer_agent)
    workflow.add_node("executor", sub_query_executor)
    workflow.add_node("synthesizer", answer_synthesis_agent)

    # Add edges (transitions)
    workflow.add_edge("router", "route_decision")
    workflow.add_conditional_edges(
        "route_decision",
        route_query,
        {
            "simple": END,  # Skip to existing RAG
            "complex": "decomposer"
        }
    )
    workflow.add_edge("decomposer", "executor")
    workflow.add_edge("executor", "synthesizer")
    workflow.add_edge("synthesizer", END)

    workflow.set_entry_point("router")

    return workflow.compile()
```

---

## Agent Implementations

### 1. Query Router Agent

**Purpose**: Analyze query and determine if decomposition is needed

**Input**: `original_question: str`
**Output**: Updates `query_type` and `complexity_reasoning` in state

**Implementation**:
```python
def query_router_agent(state: AgentState) -> AgentState:
    """
    Uses GPT-3.5-turbo (cheaper, faster) to classify query complexity.

    Prompt engineering:
    - Few-shot examples of simple vs complex queries
    - Structured output (JSON)
    - Fast classification (<500ms)
    """

    system_prompt = """
    You are a query classifier. Determine if a question is SIMPLE or COMPLEX.

    SIMPLE: Single fact, single metric, one document section
    Examples:
    - "What was total revenue?"
    - "Who is the CEO?"

    COMPLEX: Multiple parts, comparisons, multi-step reasoning
    Examples:
    - "How did revenue change from Q1 to Q2 and why?"
    - "Compare iPhone and Mac sales"

    Return JSON: {"type": "simple|complex", "reasoning": "..."}
    """

    # Call LLM (use cheaper model)
    response = litellm.completion(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["original_question"]}
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    state["query_type"] = result["type"]
    state["complexity_reasoning"] = result["reasoning"]
    state["agent_calls"].append("router")

    return state
```

---

### 2. Query Decomposer Agent

**Purpose**: Break complex query into sub-queries

**Input**: `original_question: str`, `query_type: "complex"`
**Output**: Updates `sub_queries` and `execution_order` in state

**Implementation**:
```python
def query_decomposer_agent(state: AgentState) -> AgentState:
    """
    Uses GPT-4 to decompose complex queries into sub-queries.

    Key techniques:
    - Chain-of-thought prompting
    - Structured output (JSON list)
    - Maximum 5 sub-queries to control costs
    """

    system_prompt = """
    You are a query decomposition expert. Break complex questions into 2-5 simple sub-queries.

    Guidelines:
    1. Each sub-query must be independently answerable
    2. Sub-queries should cover all parts of original question
    3. Use clear, specific language
    4. Return JSON: {
        "sub_queries": ["query1", "query2", ...],
        "execution_order": "parallel|sequential",
        "reasoning": "..."
    }

    Example:
    Input: "How did iPhone sales compare Q3 vs Q4 and what drove the change?"
    Output: {
        "sub_queries": [
            "What were iPhone sales in Q3?",
            "What were iPhone sales in Q4?",
            "What factors affected iPhone sales in Q3 and Q4?"
        ],
        "execution_order": "sequential",
        "reasoning": "Need Q3 and Q4 data first, then analyze factors"
    }
    """

    response = litellm.completion(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["original_question"]}
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    state["sub_queries"] = result["sub_queries"]
    state["execution_order"] = result["execution_order"]
    state["reasoning_steps"].append({
        "agent": "decomposer",
        "action": "query_decomposition",
        "output": result
    })
    state["agent_calls"].append("decomposer")

    return state
```

---

### 3. Sub-Query Executor

**Purpose**: Execute each sub-query using existing RAG system

**Input**: `sub_queries: List[str]`
**Output**: Updates `sub_results: List[QueryResult]` in state

**Implementation**:
```python
def sub_query_executor(state: AgentState) -> AgentState:
    """
    Executes each sub-query using the existing RAGQueryEngine.

    No new implementation needed - reuses Phase 1 components!
    Execution order determined by decomposer (parallel/sequential).
    """

    sub_results = []

    # Get existing RAG query engine from service
    query_engine = get_rag_query_engine()  # Dependency injection

    if state["execution_order"] == "parallel":
        # Execute all sub-queries in parallel (asyncio or ThreadPoolExecutor)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(query_engine.query, sub_q)
                for sub_q in state["sub_queries"]
            ]
            sub_results = [future.result() for future in futures]
    else:
        # Execute sequentially
        for sub_q in state["sub_queries"]:
            result = query_engine.query(sub_q)
            sub_results.append(result)

    state["sub_results"] = sub_results
    state["reasoning_steps"].append({
        "agent": "executor",
        "action": "sub_query_execution",
        "sub_queries": state["sub_queries"],
        "results_count": len(sub_results)
    })
    state["agent_calls"].append("executor")

    return state
```

---

### 4. Answer Synthesis Agent

**Purpose**: Combine sub-answers into coherent final response

**Input**: `sub_results: List[QueryResult]`, `original_question: str`
**Output**: Updates `final_answer` and `all_sources` in state

**Implementation**:
```python
def answer_synthesis_agent(state: AgentState) -> AgentState:
    """
    Uses GPT-4 to synthesize sub-answers into coherent final answer.

    Key requirements:
    - Must address original question
    - Must cite all relevant sources
    - Must be coherent and well-structured
    """

    # Build context from sub-results
    context_parts = []
    for i, (sub_q, result) in enumerate(zip(state["sub_queries"], state["sub_results"]), 1):
        context_parts.append(f"""
        Sub-Question {i}: {sub_q}
        Answer: {result.answer}
        Sources: {', '.join(f'Page {s.page_numbers}' for s in result.sources)}
        """)

    synthesis_context = "\n\n".join(context_parts)

    system_prompt = """
    You are an expert at synthesizing information. Combine the sub-answers below
    into a comprehensive response to the original question.

    Requirements:
    1. Directly address the original question
    2. Integrate information from all sub-answers
    3. Maintain citation integrity
    4. Be clear and well-structured
    5. Use markdown formatting
    """

    user_prompt = f"""
    Original Question: {state["original_question"]}

    Sub-Answers:
    {synthesis_context}

    Provide a comprehensive final answer:
    """

    response = litellm.completion(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    state["final_answer"] = response.choices[0].message.content

    # Aggregate all sources
    all_sources = []
    for result in state["sub_results"]:
        all_sources.extend(result.sources)
    state["all_sources"] = all_sources

    state["reasoning_steps"].append({
        "agent": "synthesizer",
        "action": "answer_synthesis",
        "final_answer_length": len(state["final_answer"])
    })
    state["agent_calls"].append("synthesizer")

    return state
```

---

## Module Structure

```
src/agents/
├── __init__.py
├── models.py              # AgentState TypedDict
├── router.py              # Query router agent
├── decomposer.py          # Query decomposer agent
├── executor.py            # Sub-query executor
├── synthesizer.py         # Answer synthesis agent
├── workflow.py            # LangGraph workflow definition
└── service.py             # AgentOrchestrationService (main interface)
```

---

## Integration with Existing Code

### Minimal Changes Required

**1. Update RAGService** (add agent orchestration option):
```python
class RAGService:
    def __init__(
        self,
        ...,
        use_agents: bool = False  # NEW PARAMETER
    ):
        self.use_agents = use_agents
        if use_agents:
            from src.agents.service import AgentOrchestrationService
            self.agent_service = AgentOrchestrationService(
                rag_query_engine=self.query_engine
            )

    def query(self, question: str) -> QueryResult:
        if self.use_agents:
            # Route through agent workflow
            return self.agent_service.process_query(question)
        else:
            # Direct to existing query engine (Phase 1 behavior)
            return self.query_engine.query(question)
```

**2. Update UI** (add reasoning toggle):
```python
# In chat component
show_reasoning = st.checkbox("🧠 Show reasoning steps", value=False)
st.session_state.show_reasoning = show_reasoning

# When displaying answers from agents
if hasattr(result, 'reasoning_steps') and st.session_state.get('show_reasoning'):
    with st.expander("🧠 Reasoning Steps"):
        display_reasoning_steps(result.reasoning_steps)
```

---

## Dependencies to Add

```toml
# pyproject.toml
[project]
dependencies = [
    # Existing...
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
]
```

---

## Testing Strategy

### Unit Tests
- Test each agent independently with mocked state
- Test state transitions
- Test LLM prompt/response handling

### Integration Tests
- Test full workflow end-to-end with real LLMs
- Test simple vs complex query routing
- Test sub-query execution

### E2E Tests
- Test with real financial documents
- Validate decomposition quality
- Measure performance

---

## Performance Considerations

1. **Query Router**: Use GPT-3.5-turbo (faster, cheaper) - target <500ms
2. **Decomposer**: Use GPT-4 (better reasoning) - target <2s
3. **Executor**: Reuse existing RAG (proven performance) - 3-4s per sub-query
4. **Synthesizer**: Use GPT-4 (quality matters) - target <2s
5. **Total for 3 sub-queries**: ~12-15 seconds (acceptable for complex queries)

---

## Configuration

```python
# src/config/settings.py

# Agent settings
USE_AGENTS: bool = True  # Feature flag
AGENT_ROUTER_MODEL: str = "gpt-3.5-turbo"
AGENT_DECOMPOSER_MODEL: str = "gpt-4-turbo-preview"
AGENT_SYNTHESIZER_MODEL: str = "gpt-4-turbo-preview"
MAX_SUB_QUERIES: int = 5
AGENT_TIMEOUT_SECONDS: int = 30
```

---

## Error Handling

1. **Router Failure**: Fall back to treating query as simple
2. **Decomposer Failure**: Fall back to direct RAG query
3. **Executor Failure**: Attempt retry, return partial results if some succeed
4. **Synthesizer Failure**: Return concatenated sub-answers with warning

All failures logged with full context for debugging.

---

## Monitoring & Observability

```python
# Log all agent interactions
logger.info(f"Agent workflow: {state['agent_calls']}")
logger.info(f"Processing time: {state['processing_time_ms']}ms")
logger.info(f"Query type: {state['query_type']}")
logger.info(f"Sub-queries: {len(state.get('sub_queries', []))}")
```

---

## Next Steps

1. Review this technical spec
2. Create tasks.md with vertical slices
3. Start implementation
