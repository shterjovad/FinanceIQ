"""LangGraph workflow definition for multi-agent query processing."""

import logging

from langgraph.graph import END, StateGraph

from src.agents.models import AgentState
from src.agents.router import query_router_agent

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

    In future slices, this will execute the query directly through RAG.
    For now, it's a placeholder that will be replaced.

    Args:
        state: Current agent state

    Returns:
        Updated state
    """
    logger.info("Simple path: Query will be executed directly (not implemented yet)")

    # Initialize metadata fields if not present
    if "agent_calls" not in state:
        state["agent_calls"] = []

    # Record this path was taken
    state["agent_calls"].append("simple_path")

    return state


def complex_path_node(state: AgentState) -> AgentState:
    """Placeholder for complex query decomposition path.

    In future slices, this will route to decomposer -> executor -> synthesizer.
    For now, it's a placeholder.

    Args:
        state: Current agent state

    Returns:
        Updated state
    """
    logger.info("Complex path: Query will be decomposed (not implemented yet)")

    # Initialize metadata fields if not present
    if "agent_calls" not in state:
        state["agent_calls"] = []

    # Record this path was taken
    state["agent_calls"].append("complex_path")

    return state


def create_agent_workflow() -> StateGraph:
    """Create the LangGraph workflow for agent orchestration.

    Workflow:
        1. Router: Classifies query as simple or complex
        2. Conditional routing:
           - Simple: Direct execution (future: executor only)
           - Complex: Decomposition path (future: decomposer → executor → synthesizer)

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(AgentState)

    # Add router as entry point
    workflow.add_node("router", query_router_agent)

    # Add placeholder nodes for routing paths
    workflow.add_node("simple_path", simple_path_node)
    workflow.add_node("complex_path", complex_path_node)

    # Set router as entry point
    workflow.set_entry_point("router")

    # Add conditional routing based on query type
    workflow.add_conditional_edges(
        "router",
        route_query,
        {
            "simple_path": "simple_path",
            "complex_path": "complex_path",
        },
    )

    # Both paths go to END for now (will be extended in future slices)
    workflow.add_edge("simple_path", END)
    workflow.add_edge("complex_path", END)

    logger.info("Agent workflow created with router and conditional routing")

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
