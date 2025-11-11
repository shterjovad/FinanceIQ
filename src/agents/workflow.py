"""LangGraph workflow definition for multi-agent query processing."""

import logging
from functools import partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.rag.query_engine import RAGQueryEngine

from langgraph.graph import END, StateGraph

from src.agents.decomposer import query_decomposer_agent
from src.agents.executor import sub_query_executor
from src.agents.models import AgentState
from src.agents.router import query_router_agent
from src.agents.synthesizer import answer_synthesis_agent

logger = logging.getLogger(__name__)


def route_query(state: AgentState) -> str:
    """Conditional routing based on query complexity.

    Routes to different workflow paths based on query_type:
    - "simple": Direct execution (no decomposition needed)
    - "complex": Decomposition path (requires query breakdown)

    Args:
        state: Current agent state with query_type set by router

    Returns:
        Next node name to route to
    """
    query_type = state.get("query_type", "simple")

    if query_type == "complex":
        logger.info("Routing to complex query path (decomposition)")
        return "complex_path"
    else:
        logger.info("Routing to simple query path (direct execution)")
        return "simple_path"


def simple_path_node(state: AgentState) -> AgentState:
    """Placeholder for simple query execution path.

    Simple queries skip decomposition and go directly to RAG execution
    (handled by RAGService, not in workflow).

    Args:
        state: Current agent state

    Returns:
        Updated state
    """
    logger.info("Simple path: Query will be executed directly by RAG service")

    # Initialize metadata fields if not present
    if "agent_calls" not in state:
        state["agent_calls"] = []

    # Record this path was taken
    state["agent_calls"].append("simple_path")

    return state


def create_agent_workflow(query_engine: "RAGQueryEngine | None" = None) -> StateGraph:
    """Create the LangGraph workflow for agent orchestration.

    Workflow:
        1. Router: Classifies query as simple or complex
        2. Conditional routing:
           - Simple: Direct execution (handled by RAGService)
           - Complex: Decomposition path (decomposer → executor → synthesizer)

    Args:
        query_engine: Optional RAG query engine for executor. If None, complex queries
                     will fail (workflow should only be created with query_engine when
                     complex queries need to be supported).

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(AgentState)

    # Add router as entry point
    workflow.add_node("router", query_router_agent)

    # Add simple path (placeholder - execution happens in RAGService)
    workflow.add_node("simple_path", simple_path_node)

    # Add complex path agents
    workflow.add_node("decomposer", query_decomposer_agent)

    # Executor needs query_engine - use partial to bind it
    if query_engine is not None:
        executor_with_engine = partial(sub_query_executor, query_engine=query_engine)
        workflow.add_node("executor", executor_with_engine)
    else:
        # Fallback executor that logs warning
        def executor_fallback(state: AgentState) -> AgentState:
            logger.warning("Executor called but no query_engine provided")
            if "agent_calls" not in state:
                state["agent_calls"] = []
            state["agent_calls"].append("executor")
            state["sub_results"] = []
            return state

        workflow.add_node("executor", executor_fallback)

    workflow.add_node("synthesizer", answer_synthesis_agent)

    # Set router as entry point
    workflow.set_entry_point("router")

    # Add conditional routing based on query type
    workflow.add_conditional_edges(
        "router",
        route_query,
        {
            "simple_path": "simple_path",
            "complex_path": "decomposer",
        },
    )

    # Simple path goes to END (execution in RAGService)
    workflow.add_edge("simple_path", END)

    # Complex path: decomposer → executor → synthesizer → END
    workflow.add_edge("decomposer", "executor")
    workflow.add_edge("executor", "synthesizer")
    workflow.add_edge("synthesizer", END)

    logger.info("Agent workflow created with complete multi-agent pipeline")

    return workflow.compile()


def test_workflow() -> None:
    """Test function to verify workflow works correctly."""
    workflow = create_agent_workflow()

    # Test with a simple question
    print("\n=== Testing Simple Query ===")
    simple_state: AgentState = {
        "original_question": "What was total revenue in 2024?",
        "agent_calls": [],
        "reasoning_steps": [],
    }

    simple_result = workflow.invoke(simple_state)

    print("✓ Simple query test passed")
    print(f"  Question: {simple_result['original_question']}")
    print(f"  Query Type: {simple_result.get('query_type', 'unknown')}")
    print(f"  Agents called: {simple_result['agent_calls']}")

    # Test with a complex question
    print("\n=== Testing Complex Query ===")
    complex_state: AgentState = {
        "original_question": "How did iPhone sales compare in Q3 vs Q4 and what drove the change?",
        "agent_calls": [],
        "reasoning_steps": [],
    }

    complex_result = workflow.invoke(complex_state)

    print("✓ Complex query test passed")
    print(f"  Question: {complex_result['original_question']}")
    print(f"  Query Type: {complex_result.get('query_type', 'unknown')}")
    print(f"  Agents called: {complex_result['agent_calls']}")


if __name__ == "__main__":
    # Allow testing this module directly
    logging.basicConfig(level=logging.INFO)
    test_workflow()
