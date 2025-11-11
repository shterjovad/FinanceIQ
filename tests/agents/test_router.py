"""Unit tests for Query Router Agent."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.agents.models import AgentState
from src.agents.router import query_router_agent


class TestQueryRouterAgent:
    """Test suite for query_router_agent function."""

    @patch("src.agents.router.litellm.completion")
    def test_simple_query_classification(self, mock_completion):
        """Test that simple queries are correctly classified."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "type": "simple",
            "reasoning": "Single fact query about revenue",
        })
        mock_completion.return_value = mock_response

        # Create state with simple query
        state: AgentState = {
            "original_question": "What was total revenue in 2024?",
        }

        # Execute router
        result = query_router_agent(state)

        # Verify classification
        assert result["query_type"] == "simple"
        assert "revenue" in result["complexity_reasoning"].lower()
        assert "router" in result["agent_calls"]
        assert len(result["reasoning_steps"]) == 1
        assert result["reasoning_steps"][0]["agent"] == "router"
        assert result["reasoning_steps"][0]["action"] == "query_classification"

    @patch("src.agents.router.litellm.completion")
    def test_complex_query_classification(self, mock_completion):
        """Test that complex queries are correctly classified."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "type": "complex",
            "reasoning": "Requires comparison across time periods and multiple metrics",
        })
        mock_completion.return_value = mock_response

        # Create state with complex query
        state: AgentState = {
            "original_question": "How did iPhone sales compare in Q3 vs Q4 and what drove the change?",
        }

        # Execute router
        result = query_router_agent(state)

        # Verify classification
        assert result["query_type"] == "complex"
        assert "comparison" in result["complexity_reasoning"].lower() or "period" in result["complexity_reasoning"].lower()
        assert "router" in result["agent_calls"]

    @patch("src.agents.router.litellm.completion")
    def test_empty_query_handling(self, mock_completion):
        """Test handling of empty or missing query."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "type": "simple",
            "reasoning": "Empty query defaults to simple",
        })
        mock_completion.return_value = mock_response

        # Create state with empty query
        state: AgentState = {}

        # Execute router (should not crash)
        result = query_router_agent(state)

        # Should default to simple and not crash
        assert result["query_type"] in ["simple", "complex"]
        assert "router" in result["agent_calls"]

    @patch("src.agents.router.litellm.completion")
    def test_very_long_query_handling(self, mock_completion):
        """Test handling of very long queries."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "type": "complex",
            "reasoning": "Multi-part question with many clauses",
        })
        mock_completion.return_value = mock_response

        # Create state with very long query
        long_query = "What was " + " and ".join([f"metric{i}" for i in range(100)]) + "?"
        state: AgentState = {
            "original_question": long_query,
        }

        # Execute router (should not crash)
        result = query_router_agent(state)

        # Should handle gracefully
        assert result["query_type"] in ["simple", "complex"]
        assert "router" in result["agent_calls"]

    @patch("src.agents.router.litellm.completion")
    def test_invalid_json_response(self, mock_completion):
        """Test handling of invalid JSON from LLM."""
        # Mock LLM returning invalid JSON
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "This is not valid JSON"
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "What was revenue?",
        }

        # Execute router
        result = query_router_agent(state)

        # Should fallback to simple
        assert result["query_type"] == "simple"
        assert "JSON parse error" in result["complexity_reasoning"]
        assert "router" in result["agent_calls"]

    @patch("src.agents.router.litellm.completion")
    def test_invalid_type_in_response(self, mock_completion):
        """Test handling of invalid type value in response."""
        # Mock LLM returning invalid type
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "type": "medium",  # Invalid type
            "reasoning": "Some reasoning",
        })
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "What was revenue?",
        }

        # Execute router
        result = query_router_agent(state)

        # Should fallback to simple
        assert result["query_type"] == "simple"
        assert "Invalid classification" in result["complexity_reasoning"]
        assert "router" in result["agent_calls"]

    @patch("src.agents.router.litellm.completion")
    def test_llm_exception_handling(self, mock_completion):
        """Test handling of LLM exceptions."""
        # Mock LLM raising exception
        mock_completion.side_effect = Exception("API rate limit exceeded")

        # Create state
        state: AgentState = {
            "original_question": "What was revenue?",
        }

        # Execute router
        result = query_router_agent(state)

        # Should fallback to simple and record error
        assert result["query_type"] == "simple"
        assert "Classification failed" in result["complexity_reasoning"]
        assert "router" in result["agent_calls"]
        assert "error" in result
        assert "Router error" in result["error"]

    @patch("src.agents.router.litellm.completion")
    def test_reasoning_steps_recorded(self, mock_completion):
        """Test that reasoning steps are properly recorded."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "type": "simple",
            "reasoning": "Single metric query",
        })
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "What was revenue?",
        }

        # Execute router
        result = query_router_agent(state)

        # Verify reasoning steps structure
        assert len(result["reasoning_steps"]) == 1
        step = result["reasoning_steps"][0]
        assert step["agent"] == "router"
        assert step["action"] == "query_classification"
        assert "question" in step["input"]
        assert "type" in step["output"]
        assert "reasoning" in step["output"]
        assert isinstance(step["duration_ms"], int)
        assert step["duration_ms"] >= 0

    @patch("src.agents.router.litellm.completion")
    def test_state_without_metadata_fields(self, mock_completion):
        """Test that router initializes metadata fields if missing."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "type": "simple",
            "reasoning": "Simple query",
        })
        mock_completion.return_value = mock_response

        # Create state without metadata fields
        state: AgentState = {
            "original_question": "What was revenue?",
        }

        # Verify fields don't exist yet
        assert "agent_calls" not in state
        assert "reasoning_steps" not in state

        # Execute router
        result = query_router_agent(state)

        # Verify fields were initialized
        assert "agent_calls" in result
        assert "reasoning_steps" in result
        assert isinstance(result["agent_calls"], list)
        assert isinstance(result["reasoning_steps"], list)

    @patch("src.agents.router.litellm.completion")
    def test_llm_called_with_correct_parameters(self, mock_completion):
        """Test that LLM is called with correct parameters."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "type": "simple",
            "reasoning": "Simple query",
        })
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "What was revenue?",
        }

        # Execute router
        query_router_agent(state)

        # Verify LLM was called with correct parameters
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]

        assert call_kwargs["temperature"] == 0.0
        assert call_kwargs["max_tokens"] == 200
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"
        assert "What was revenue?" in call_kwargs["messages"][1]["content"]
