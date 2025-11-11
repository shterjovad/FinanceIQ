"""Unit tests for Query Decomposer Agent."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.agents.decomposer import query_decomposer_agent
from src.agents.models import AgentState


class TestQueryDecomposerAgent:
    """Test suite for query_decomposer_agent function."""

    @patch("src.agents.decomposer.litellm.completion")
    def test_parallel_decomposition(self, mock_completion):
        """Test decomposition with parallel execution order."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            {
                "sub_queries": [
                    "What were Apple's iPhone sales in Q3?",
                    "What were Apple's iPhone sales in Q4?",
                    "What factors affected iPhone sales?",
                ],
                "execution_order": "parallel",
                "reasoning": "All queries are independent",
            }
        )
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "How did iPhone sales compare Q3 vs Q4?",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute decomposer
        result = query_decomposer_agent(state)

        # Verify decomposition
        assert len(result["sub_queries"]) == 3
        assert result["execution_order"] == "parallel"
        assert "decomposer" in result["agent_calls"]
        assert len(result["reasoning_steps"]) == 1
        assert result["reasoning_steps"][0]["agent"] == "decomposer"
        assert result["reasoning_steps"][0]["action"] == "query_decomposition"

    @patch("src.agents.decomposer.litellm.completion")
    def test_sequential_decomposition(self, mock_completion):
        """Test decomposition with sequential execution order."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            {
                "sub_queries": [
                    "What are the main revenue streams?",
                    "Which revenue stream grew fastest?",
                ],
                "execution_order": "sequential",
                "reasoning": "Need revenue streams first, then compare growth",
            }
        )
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "What are revenue streams and which grew fastest?",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute decomposer
        result = query_decomposer_agent(state)

        # Verify decomposition
        assert len(result["sub_queries"]) == 2
        assert result["execution_order"] == "sequential"
        assert "decomposer" in result["agent_calls"]

    @patch("src.agents.decomposer.litellm.completion")
    def test_maximum_sub_queries_limit(self, mock_completion):
        """Test that decomposer enforces MAX_SUB_QUERIES limit."""
        # Mock LLM response with 10 sub-queries
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            {
                "sub_queries": [f"Query {i}" for i in range(10)],
                "execution_order": "parallel",
                "reasoning": "Too many queries",
            }
        )
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "Complex question",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute decomposer
        result = query_decomposer_agent(state)

        # Verify limit enforced (MAX_SUB_QUERIES = 5 in settings)
        assert len(result["sub_queries"]) <= 5
        assert "decomposer" in result["agent_calls"]

    @patch("src.agents.decomposer.litellm.completion")
    def test_invalid_execution_order_fallback(self, mock_completion):
        """Test that invalid execution order defaults to parallel."""
        # Mock LLM response with invalid execution order
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            {
                "sub_queries": ["Query 1", "Query 2"],
                "execution_order": "invalid_order",
                "reasoning": "Test reasoning",
            }
        )
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "Test question",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute decomposer
        result = query_decomposer_agent(state)

        # Verify fallback to parallel
        assert result["execution_order"] == "parallel"
        assert "decomposer" in result["agent_calls"]

    @patch("src.agents.decomposer.litellm.completion")
    def test_invalid_json_response_fallback(self, mock_completion):
        """Test handling of invalid JSON from LLM."""
        # Mock LLM returning invalid JSON
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "This is not valid JSON"
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "Test question",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute decomposer
        result = query_decomposer_agent(state)

        # Verify fallback to single query
        assert result["sub_queries"] == ["Test question"]
        assert result["execution_order"] == "parallel"
        assert "decomposer" in result["agent_calls"]
        assert "error" in result
        assert "JSON" in result["error"]

    @patch("src.agents.decomposer.litellm.completion")
    def test_llm_exception_handling(self, mock_completion):
        """Test handling of LLM exceptions."""
        # Mock LLM raising exception
        mock_completion.side_effect = Exception("API error")

        # Create state
        state: AgentState = {
            "original_question": "Test question",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute decomposer
        result = query_decomposer_agent(state)

        # Verify fallback to single query
        assert result["sub_queries"] == ["Test question"]
        assert result["execution_order"] == "parallel"
        assert "decomposer" in result["agent_calls"]
        assert "error" in result
        assert "API error" in result["error"]

    @patch("src.agents.decomposer.litellm.completion")
    def test_reasoning_steps_recorded(self, mock_completion):
        """Test that reasoning steps are properly recorded."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            {
                "sub_queries": ["Query 1", "Query 2"],
                "execution_order": "parallel",
                "reasoning": "Test reasoning",
            }
        )
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "Test question",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute decomposer
        result = query_decomposer_agent(state)

        # Verify reasoning steps structure
        assert len(result["reasoning_steps"]) == 1
        step = result["reasoning_steps"][0]
        assert step["agent"] == "decomposer"
        assert step["action"] == "query_decomposition"
        assert "input" in step
        assert "output" in step
        assert "duration_ms" in step
        assert isinstance(step["duration_ms"], int)
        assert step["duration_ms"] >= 0

    @patch("src.agents.decomposer.litellm.completion")
    def test_state_without_metadata_fields(self, mock_completion):
        """Test that decomposer initializes metadata fields if missing."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            {
                "sub_queries": ["Query 1"],
                "execution_order": "parallel",
                "reasoning": "Test",
            }
        )
        mock_completion.return_value = mock_response

        # Create state without metadata fields
        state: AgentState = {
            "original_question": "Test question",
        }

        # Verify fields don't exist yet
        assert "agent_calls" not in state
        assert "reasoning_steps" not in state

        # Execute decomposer
        result = query_decomposer_agent(state)

        # Verify fields were initialized
        assert "agent_calls" in result
        assert "reasoning_steps" in result
        assert isinstance(result["agent_calls"], list)
        assert isinstance(result["reasoning_steps"], list)

    @patch("src.agents.decomposer.litellm.completion")
    def test_empty_query_handling(self, mock_completion):
        """Test handling of empty query."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            {
                "sub_queries": [""],
                "execution_order": "parallel",
                "reasoning": "Empty query",
            }
        )
        mock_completion.return_value = mock_response

        # Create state with empty query
        state: AgentState = {
            "original_question": "",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute decomposer (should not crash)
        result = query_decomposer_agent(state)

        # Should complete without errors
        assert "sub_queries" in result
        assert "decomposer" in result["agent_calls"]

    @patch("src.agents.decomposer.litellm.completion")
    def test_llm_called_with_correct_parameters(self, mock_completion):
        """Test that LLM is called with correct parameters."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            {
                "sub_queries": ["Query 1"],
                "execution_order": "parallel",
                "reasoning": "Test",
            }
        )
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "Test question",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute decomposer
        query_decomposer_agent(state)

        # Verify LLM was called with correct parameters
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]

        assert call_kwargs["temperature"] == 0.0
        assert call_kwargs["max_tokens"] == 500
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"
        assert "Test question" in call_kwargs["messages"][1]["content"]

    @patch("src.agents.decomposer.litellm.completion")
    def test_missing_fields_in_response(self, mock_completion):
        """Test handling of missing fields in LLM response."""
        # Mock LLM response with missing fields
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            {
                "sub_queries": ["Query 1"]
                # Missing execution_order and reasoning
            }
        )
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "Test question",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute decomposer
        result = query_decomposer_agent(state)

        # Verify defaults are applied
        assert result["sub_queries"] == ["Query 1"]
        assert result["execution_order"] == "parallel"  # Default
        assert "decomposer" in result["agent_calls"]
