"""Integration tests for agent workflow."""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.models import AgentState
from src.agents.workflow import (
    complex_path_node,
    create_agent_workflow,
    route_query,
    simple_path_node,
)


class TestRouteQuery:
    """Test suite for route_query function."""

    def test_routes_simple_queries(self):
        """Test that simple queries are routed to simple_path."""
        state: AgentState = {
            "query_type": "simple",
            "original_question": "What was revenue?",
        }

        result = route_query(state)

        assert result == "simple_path"

    def test_routes_complex_queries(self):
        """Test that complex queries are routed to complex_path."""
        state: AgentState = {
            "query_type": "complex",
            "original_question": "How did revenue compare across quarters?",
        }

        result = route_query(state)

        assert result == "complex_path"

    def test_defaults_to_simple_when_missing(self):
        """Test that missing query_type defaults to simple routing."""
        state: AgentState = {
            "original_question": "What was revenue?",
        }

        result = route_query(state)

        assert result == "simple_path"


class TestSimplePathNode:
    """Test suite for simple_path_node function."""

    def test_initializes_metadata_fields(self):
        """Test that metadata fields are initialized if missing."""
        state: AgentState = {
            "original_question": "What was revenue?",
        }

        result = simple_path_node(state)

        assert "agent_calls" in result
        assert isinstance(result["agent_calls"], list)

    def test_records_agent_call(self):
        """Test that simple_path is recorded in agent_calls."""
        state: AgentState = {
            "original_question": "What was revenue?",
            "agent_calls": [],
        }

        result = simple_path_node(state)

        assert "simple_path" in result["agent_calls"]


class TestComplexPathNode:
    """Test suite for complex_path_node function."""

    def test_initializes_metadata_fields(self):
        """Test that metadata fields are initialized if missing."""
        state: AgentState = {
            "original_question": "How did revenue compare?",
        }

        result = complex_path_node(state)

        assert "agent_calls" in result
        assert isinstance(result["agent_calls"], list)

    def test_records_agent_call(self):
        """Test that complex_path is recorded in agent_calls."""
        state: AgentState = {
            "original_question": "How did revenue compare?",
            "agent_calls": [],
        }

        result = complex_path_node(state)

        assert "complex_path" in result["agent_calls"]


class TestCreateAgentWorkflow:
    """Test suite for create_agent_workflow function."""

    @patch("src.agents.workflow.query_router_agent")
    def test_workflow_executes_simple_path(self, mock_router):
        """Test that workflow executes simple query path correctly."""
        # Mock router to classify as simple
        def mock_router_fn(state: AgentState) -> AgentState:
            state["query_type"] = "simple"
            state["complexity_reasoning"] = "Test reasoning"
            if "agent_calls" not in state:
                state["agent_calls"] = []
            state["agent_calls"].append("router")
            return state

        mock_router.side_effect = mock_router_fn

        # Create workflow
        workflow = create_agent_workflow()

        # Execute with simple question
        initial_state: AgentState = {
            "original_question": "What was revenue?",
            "agent_calls": [],
        }

        result = workflow.invoke(initial_state)

        # Verify correct path was taken
        assert result["query_type"] == "simple"
        assert "router" in result["agent_calls"]
        assert "simple_path" in result["agent_calls"]
        assert "complex_path" not in result["agent_calls"]

    @patch("src.agents.workflow.query_router_agent")
    def test_workflow_executes_complex_path(self, mock_router):
        """Test that workflow executes complex query path correctly."""
        # Mock router to classify as complex
        def mock_router_fn(state: AgentState) -> AgentState:
            state["query_type"] = "complex"
            state["complexity_reasoning"] = "Test reasoning"
            if "agent_calls" not in state:
                state["agent_calls"] = []
            state["agent_calls"].append("router")
            return state

        mock_router.side_effect = mock_router_fn

        # Create workflow
        workflow = create_agent_workflow()

        # Execute with complex question
        initial_state: AgentState = {
            "original_question": "How did revenue compare across quarters?",
            "agent_calls": [],
        }

        result = workflow.invoke(initial_state)

        # Verify correct path was taken
        assert result["query_type"] == "complex"
        assert "router" in result["agent_calls"]
        assert "complex_path" in result["agent_calls"]
        assert "simple_path" not in result["agent_calls"]

    @patch("src.agents.workflow.query_router_agent")
    def test_workflow_handles_empty_state(self, mock_router):
        """Test that workflow handles empty initial state."""
        # Mock router to add required fields
        def mock_router_fn(state: AgentState) -> AgentState:
            state["query_type"] = "simple"
            state["complexity_reasoning"] = "Test reasoning"
            state["agent_calls"] = ["router"]
            return state

        mock_router.side_effect = mock_router_fn

        # Create workflow
        workflow = create_agent_workflow()

        # Execute with minimal state
        initial_state: AgentState = {
            "original_question": "Test question",
        }

        result = workflow.invoke(initial_state)

        # Verify workflow completed
        assert "query_type" in result
        assert "agent_calls" in result
        assert len(result["agent_calls"]) >= 2  # router + path node

    @patch("src.agents.workflow.query_router_agent")
    def test_workflow_preserves_existing_state(self, mock_router):
        """Test that workflow preserves fields from initial state."""
        # Mock router
        def mock_router_fn(state: AgentState) -> AgentState:
            state["query_type"] = "simple"
            state["complexity_reasoning"] = "Test reasoning"
            if "agent_calls" not in state:
                state["agent_calls"] = []
            state["agent_calls"].append("router")
            return state

        mock_router.side_effect = mock_router_fn

        # Create workflow
        workflow = create_agent_workflow()

        # Execute with extra state fields
        initial_state: AgentState = {
            "original_question": "Test question",
            "agent_calls": [],
            "reasoning_steps": [{"test": "data"}],
        }

        result = workflow.invoke(initial_state)

        # Verify existing fields preserved
        assert result["original_question"] == "Test question"
        assert len(result["reasoning_steps"]) == 1
        assert result["reasoning_steps"][0]["test"] == "data"
