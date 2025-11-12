"""Data models for agent orchestration state."""

from typing import Any, Literal, TypedDict

from src.rag.models import QueryResult, SourceCitation


class AgentState(TypedDict, total=False):
    """State passed between agents in the LangGraph workflow.

    This state object is incrementally built as it flows through the agent workflow.
    Each agent reads from and writes to specific fields.

    Workflow:
        original_question → router → decomposer → executor → synthesizer → final_answer
    """

    # ========== Input ==========
    original_question: str
    """The user's original question"""

    session_id: str | None
    """Browser session ID for query isolation"""

    # ========== Analysis (Router Agent) ==========
    query_type: Literal["simple", "complex"]
    """Classification of query complexity"""

    complexity_reasoning: str
    """Explanation of why query was classified as simple or complex"""

    # ========== Decomposition (Decomposer Agent) ==========
    sub_queries: list[str]
    """List of sub-queries for complex questions (2-5 queries)"""

    execution_order: Literal["parallel", "sequential"]
    """Whether sub-queries should be executed in parallel or sequentially"""

    decomposition_reasoning: str
    """Explanation of decomposition strategy"""

    # ========== Execution (Executor Agent) ==========
    sub_results: list[QueryResult]
    """Results from executing each sub-query through RAG system"""

    # ========== Synthesis (Synthesis Agent) ==========
    final_answer: str
    """The synthesized final answer addressing the original question"""

    all_sources: list[SourceCitation]
    """Aggregated source citations from all sub-queries"""

    synthesis_reasoning: str
    """Explanation of how sub-answers were combined"""

    # ========== Metadata & Observability ==========
    reasoning_steps: list[dict[str, Any]]
    """Log of all agent actions for transparency/debugging"""

    processing_time_ms: int
    """Total processing time in milliseconds"""

    agent_calls: list[str]
    """List of agents that processed this query (e.g., ['router', 'decomposer'])"""

    error: str | None
    """Error message if workflow failed"""


class ReasoningStep(TypedDict):
    """A single step in the reasoning process for transparency."""

    agent: str
    """Name of the agent that performed this step"""

    action: str
    """What action was performed (e.g., 'query_decomposition')"""

    input: dict[str, Any]
    """Input to this step"""

    output: dict[str, Any]
    """Output from this step"""

    duration_ms: int
    """How long this step took"""
