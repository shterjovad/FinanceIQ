"""LangGraph workflow definition for multi-agent query processing."""

import logging

from langgraph.graph import END, StateGraph

from src.agents.models import AgentState

logger = logging.getLogger(__name__)


def passthrough_node(state: AgentState) -> AgentState:
    """Minimal passthrough node for testing.

    This is a placeholder that will be replaced with real agents.
    For now, it just logs the question and returns the state unchanged.
    """
    question = state.get("original_question", "")
    logger.info(f"Passthrough node received question: {question}")

    # Initialize metadata fields if not present
    if "agent_calls" not in state:
        state["agent_calls"] = []
    if "reasoning_steps" not in state:
        state["reasoning_steps"] = []

    # Record that this node was called
    state["agent_calls"].append("passthrough")

    return state


def create_agent_workflow() -> StateGraph:
    """Create the LangGraph workflow for agent orchestration.

    For Slice 1, this is a minimal pass-through workflow to verify
    LangGraph setup works correctly. Future slices will add real agents.

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(AgentState)

    # Add passthrough node (temporary - will be replaced with real agents)
    workflow.add_node("passthrough", passthrough_node)

    # Set entry point
    workflow.set_entry_point("passthrough")

    # Connect to end
    workflow.add_edge("passthrough", END)

    logger.info("Agent workflow created (passthrough mode)")

    return workflow.compile()


def test_workflow() -> None:
    """Test function to verify workflow works correctly."""
    workflow = create_agent_workflow()

    # Test with a simple question
    initial_state: AgentState = {
        "original_question": "What was total revenue in 2024?",
        "agent_calls": [],
        "reasoning_steps": [],
    }

    result = workflow.invoke(initial_state)

    print("✓ Workflow test passed")
    print(f"  Question: {result['original_question']}")
    print(f"  Agents called: {result['agent_calls']}")


if __name__ == "__main__":
    # Allow testing this module directly
    logging.basicConfig(level=logging.INFO)
    test_workflow()
