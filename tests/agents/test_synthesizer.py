"""Unit tests for Answer Synthesis Agent."""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.models import AgentState
from src.agents.synthesizer import answer_synthesis_agent
from src.rag.models import QueryResult, SourceCitation


class TestAnswerSynthesisAgent:
    """Test suite for answer_synthesis_agent function."""

    @patch("src.agents.synthesizer.litellm.completion")
    def test_successful_synthesis(self, mock_completion):
        """Test successful synthesis of sub-answers."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = (
            "iPhone sales increased from $50M in Q3 to $60M in Q4, "
            "representing a 20% growth driven by new product launches."
        )
        mock_completion.return_value = mock_response

        # Create state with sub-results
        state: AgentState = {
            "original_question": "How did iPhone sales change Q3 to Q4?",
            "sub_queries": [
                "What were iPhone sales in Q3?",
                "What were iPhone sales in Q4?",
            ],
            "sub_results": [
                QueryResult(
                    success=True,
                    answer="Q3 iPhone sales were $50M",
                    sources=[
                        SourceCitation(
                            document_id="doc1",
                            page_numbers=[1],
                            relevance_score=0.9,
                            snippet="Q3 sales data",
                        )
                    ],
                    chunks_retrieved=3,
                    query_time_seconds=0.5,
                ),
                QueryResult(
                    success=True,
                    answer="Q4 iPhone sales were $60M",
                    sources=[
                        SourceCitation(
                            document_id="doc1",
                            page_numbers=[2],
                            relevance_score=0.85,
                            snippet="Q4 sales data",
                        )
                    ],
                    chunks_retrieved=3,
                    query_time_seconds=0.6,
                ),
            ],
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute synthesizer
        result = answer_synthesis_agent(state)

        # Verify synthesis
        assert "final_answer" in result
        assert len(result["final_answer"]) > 0
        assert "all_sources" in result
        assert len(result["all_sources"]) == 2
        assert "synthesizer" in result["agent_calls"]
        assert len(result["reasoning_steps"]) == 1
        assert result["reasoning_steps"][0]["agent"] == "synthesizer"

    @patch("src.agents.synthesizer.litellm.completion")
    def test_deduplicates_sources(self, mock_completion):
        """Test that duplicate sources are removed."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Synthesized answer"
        mock_completion.return_value = mock_response

        # Create state with duplicate sources
        duplicate_source = SourceCitation(
            document_id="doc1",
            page_numbers=[1],
            relevance_score=0.9,
            snippet="Same data",
        )

        state: AgentState = {
            "original_question": "Test question",
            "sub_queries": ["Query 1", "Query 2"],
            "sub_results": [
                QueryResult(
                    success=True,
                    answer="Answer 1",
                    sources=[duplicate_source],
                    chunks_retrieved=1,
                    query_time_seconds=0.5,
                ),
                QueryResult(
                    success=True,
                    answer="Answer 2",
                    sources=[duplicate_source],  # Same source
                    chunks_retrieved=1,
                    query_time_seconds=0.5,
                ),
            ],
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute synthesizer
        result = answer_synthesis_agent(state)

        # Verify sources were deduplicated
        assert len(result["all_sources"]) == 1

    @patch("src.agents.synthesizer.litellm.completion")
    def test_empty_sub_results(self, mock_completion):
        """Test handling of empty sub-results."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "No sub-answers provided"
        mock_completion.return_value = mock_response

        # Create state with no sub-results
        state: AgentState = {
            "original_question": "Test question",
            "sub_queries": [],
            "sub_results": [],
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute synthesizer (should not crash)
        result = answer_synthesis_agent(state)

        # Verify it completes
        assert "final_answer" in result
        assert "all_sources" in result
        assert "synthesizer" in result["agent_calls"]

    @patch("src.agents.synthesizer.litellm.completion")
    def test_llm_exception_fallback(self, mock_completion):
        """Test fallback to concatenation when LLM fails."""
        # Mock LLM raising exception
        mock_completion.side_effect = Exception("API error")

        # Create state
        state: AgentState = {
            "original_question": "Test question",
            "sub_queries": ["Query 1", "Query 2"],
            "sub_results": [
                QueryResult(
                    success=True,
                    answer="Answer 1",
                    sources=[],
                    chunks_retrieved=1,
                    query_time_seconds=0.5,
                ),
                QueryResult(
                    success=True,
                    answer="Answer 2",
                    sources=[],
                    chunks_retrieved=1,
                    query_time_seconds=0.5,
                ),
            ],
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute synthesizer
        result = answer_synthesis_agent(state)

        # Verify fallback to concatenation
        assert "final_answer" in result
        assert "Query 1" in result["final_answer"]
        assert "Query 2" in result["final_answer"]
        assert "synthesizer" in result["agent_calls"]
        assert "error" in result
        assert "API error" in result["error"]

    @patch("src.agents.synthesizer.litellm.completion")
    def test_reasoning_steps_recorded(self, mock_completion):
        """Test that reasoning steps are properly recorded."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Synthesized answer"
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "Test question",
            "sub_queries": ["Query 1"],
            "sub_results": [
                QueryResult(
                    success=True,
                    answer="Answer 1",
                    sources=[
                        SourceCitation(
                            document_id="doc1",
                            page_numbers=[1],
                            relevance_score=0.9,
                            snippet="Data",
                        )
                    ],
                    chunks_retrieved=1,
                    query_time_seconds=0.5,
                )
            ],
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute synthesizer
        result = answer_synthesis_agent(state)

        # Verify reasoning steps structure
        assert len(result["reasoning_steps"]) == 1
        step = result["reasoning_steps"][0]
        assert step["agent"] == "synthesizer"
        assert step["action"] == "answer_synthesis"
        assert "input" in step
        assert "output" in step
        assert "duration_ms" in step
        assert step["output"]["total_sources"] == 1

    @patch("src.agents.synthesizer.litellm.completion")
    def test_state_without_metadata_fields(self, mock_completion):
        """Test that synthesizer initializes metadata fields if missing."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Answer"
        mock_completion.return_value = mock_response

        # Create state without metadata fields
        state: AgentState = {
            "original_question": "Test question",
            "sub_queries": ["Query 1"],
            "sub_results": [
                QueryResult(
                    success=True,
                    answer="Answer",
                    sources=[],
                    chunks_retrieved=1,
                    query_time_seconds=0.5,
                )
            ],
        }

        # Verify fields don't exist yet
        assert "agent_calls" not in state
        assert "reasoning_steps" not in state

        # Execute synthesizer
        result = answer_synthesis_agent(state)

        # Verify fields were initialized
        assert "agent_calls" in result
        assert "reasoning_steps" in result
        assert isinstance(result["agent_calls"], list)
        assert isinstance(result["reasoning_steps"], list)

    @patch("src.agents.synthesizer.litellm.completion")
    def test_sub_results_without_sources(self, mock_completion):
        """Test handling of sub-results with no sources."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Synthesized answer"
        mock_completion.return_value = mock_response

        # Create state with sourceless results
        state: AgentState = {
            "original_question": "Test question",
            "sub_queries": ["Query 1", "Query 2"],
            "sub_results": [
                QueryResult(
                    success=True,
                    answer="Answer 1",
                    sources=[],  # No sources
                    chunks_retrieved=0,
                    query_time_seconds=0.5,
                ),
                QueryResult(
                    success=True,
                    answer="Answer 2",
                    sources=[],  # No sources
                    chunks_retrieved=0,
                    query_time_seconds=0.5,
                ),
            ],
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute synthesizer
        result = answer_synthesis_agent(state)

        # Verify it handles gracefully
        assert "final_answer" in result
        assert "all_sources" in result
        assert len(result["all_sources"]) == 0

    @patch("src.agents.synthesizer.litellm.completion")
    def test_llm_called_with_correct_parameters(self, mock_completion):
        """Test that LLM is called with correct parameters."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Synthesized"
        mock_completion.return_value = mock_response

        # Create state
        state: AgentState = {
            "original_question": "Test question",
            "sub_queries": ["Query 1"],
            "sub_results": [
                QueryResult(
                    success=True,
                    answer="Answer",
                    sources=[],
                    chunks_retrieved=1,
                    query_time_seconds=0.5,
                )
            ],
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute synthesizer
        answer_synthesis_agent(state)

        # Verify LLM was called with correct parameters
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]

        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["max_tokens"] == 1000
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"
        assert "Test question" in call_kwargs["messages"][1]["content"]

    @patch("src.agents.synthesizer.litellm.completion")
    def test_preserves_all_unique_sources(self, mock_completion):
        """Test that all unique sources are preserved."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Synthesized"
        mock_completion.return_value = mock_response

        # Create state with multiple unique sources
        state: AgentState = {
            "original_question": "Test question",
            "sub_queries": ["Q1", "Q2", "Q3"],
            "sub_results": [
                QueryResult(
                    success=True,
                    answer="A1",
                    sources=[
                        SourceCitation(
                            document_id="doc1",
                            page_numbers=[1],
                            relevance_score=0.9,
                            snippet="S1",
                        )
                    ],
                    chunks_retrieved=1,
                    query_time_seconds=0.5,
                ),
                QueryResult(
                    success=True,
                    answer="A2",
                    sources=[
                        SourceCitation(
                            document_id="doc1",
                            page_numbers=[2],
                            relevance_score=0.8,
                            snippet="S2",
                        ),
                        SourceCitation(
                            document_id="doc2",
                            page_numbers=[1],
                            relevance_score=0.7,
                            snippet="S3",
                        ),
                    ],
                    chunks_retrieved=2,
                    query_time_seconds=0.5,
                ),
                QueryResult(
                    success=True,
                    answer="A3",
                    sources=[
                        SourceCitation(
                            document_id="doc3",
                            page_numbers=[5],
                            relevance_score=0.6,
                            snippet="S4",
                        )
                    ],
                    chunks_retrieved=1,
                    query_time_seconds=0.5,
                ),
            ],
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute synthesizer
        result = answer_synthesis_agent(state)

        # Verify all unique sources preserved
        assert len(result["all_sources"]) == 4
