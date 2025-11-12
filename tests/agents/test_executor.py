"""Unit tests for Sub-Query Executor Agent."""

from unittest.mock import MagicMock

from src.agents.executor import sub_query_executor
from src.agents.models import AgentState
from src.rag.models import QueryResult, SourceCitation


class TestSubQueryExecutor:
    """Test suite for sub_query_executor function."""

    def test_parallel_execution(self):
        """Test parallel execution of sub-queries."""
        # Mock query engine
        mock_engine = MagicMock()

        # Mock results for each sub-query
        result1 = QueryResult(
            success=True,
            answer="Q3 sales were $50M",
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
        )

        result2 = QueryResult(
            success=True,
            answer="Q4 sales were $60M",
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
        )

        mock_engine.query.side_effect = [result1, result2]

        # Create state
        state: AgentState = {
            "sub_queries": ["Q3 sales?", "Q4 sales?"],
            "execution_order": "parallel",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute
        result = sub_query_executor(state, mock_engine)

        # Verify results
        assert len(result["sub_results"]) == 2
        assert result["sub_results"][0].answer == "Q3 sales were $50M"
        assert result["sub_results"][1].answer == "Q4 sales were $60M"
        assert "executor" in result["agent_calls"]
        assert len(result["reasoning_steps"]) == 1
        assert result["reasoning_steps"][0]["agent"] == "executor"

    def test_sequential_execution(self):
        """Test sequential execution of sub-queries."""
        # Mock query engine
        mock_engine = MagicMock()

        # Mock results
        result1 = QueryResult(
            success=True,
            answer="Revenue streams: Products, Services",
            sources=[],
            chunks_retrieved=2,
            query_time_seconds=0.5,
        )

        result2 = QueryResult(
            success=True,
            answer="Services grew fastest at 20%",
            sources=[],
            chunks_retrieved=2,
            query_time_seconds=0.6,
        )

        mock_engine.query.side_effect = [result1, result2]

        # Create state
        state: AgentState = {
            "sub_queries": ["What are revenue streams?", "Which grew fastest?"],
            "execution_order": "sequential",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute
        result = sub_query_executor(state, mock_engine)

        # Verify results
        assert len(result["sub_results"]) == 2
        assert result["sub_results"][0].answer == "Revenue streams: Products, Services"
        assert result["sub_results"][1].answer == "Services grew fastest at 20%"
        assert "executor" in result["agent_calls"]

        # Verify sequential order (called in order)
        assert mock_engine.query.call_count == 2

    def test_empty_sub_queries(self):
        """Test handling of empty sub-queries list."""
        # Mock query engine
        mock_engine = MagicMock()

        # Create state with no sub-queries
        state: AgentState = {
            "sub_queries": [],
            "execution_order": "parallel",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute
        result = sub_query_executor(state, mock_engine)

        # Verify empty results
        assert result["sub_results"] == []
        assert "executor" in result["agent_calls"]
        assert mock_engine.query.call_count == 0

    def test_single_sub_query(self):
        """Test execution with a single sub-query."""
        # Mock query engine
        mock_engine = MagicMock()

        result1 = QueryResult(
            success=True,
            answer="Single answer",
            sources=[],
            chunks_retrieved=1,
            query_time_seconds=0.5,
        )

        mock_engine.query.return_value = result1

        # Create state
        state: AgentState = {
            "sub_queries": ["Single query?"],
            "execution_order": "parallel",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute
        result = sub_query_executor(state, mock_engine)

        # Verify single result
        assert len(result["sub_results"]) == 1
        assert result["sub_results"][0].answer == "Single answer"
        assert "executor" in result["agent_calls"]

    def test_query_engine_exception_parallel(self):
        """Test handling of query engine exceptions in parallel mode."""
        # Mock query engine that raises exception
        mock_engine = MagicMock()

        # First query succeeds, second fails
        result1 = QueryResult(
            success=True,
            answer="First answer",
            sources=[],
            chunks_retrieved=1,
            query_time_seconds=0.5,
        )

        mock_engine.query.side_effect = [result1, Exception("Query failed")]

        # Create state
        state: AgentState = {
            "sub_queries": ["Query 1", "Query 2"],
            "execution_order": "parallel",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute
        result = sub_query_executor(state, mock_engine)

        # Verify we have 2 results (one success, one error)
        assert len(result["sub_results"]) == 2
        assert result["sub_results"][0].answer == "First answer"
        assert "Error" in result["sub_results"][1].answer
        assert "executor" in result["agent_calls"]

    def test_query_engine_exception_sequential(self):
        """Test handling of query engine exceptions in sequential mode."""
        # Mock query engine that raises exception
        mock_engine = MagicMock()

        # First query succeeds, second fails, third succeeds
        result1 = QueryResult(
            success=True,
            answer="First answer",
            sources=[],
            chunks_retrieved=1,
            query_time_seconds=0.5,
        )

        result3 = QueryResult(
            success=True,
            answer="Third answer",
            sources=[],
            chunks_retrieved=1,
            query_time_seconds=0.5,
        )

        mock_engine.query.side_effect = [result1, Exception("Query 2 failed"), result3]

        # Create state
        state: AgentState = {
            "sub_queries": ["Query 1", "Query 2", "Query 3"],
            "execution_order": "sequential",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute
        result = sub_query_executor(state, mock_engine)

        # Verify we have 3 results (2 success, 1 error)
        assert len(result["sub_results"]) == 3
        assert result["sub_results"][0].answer == "First answer"
        assert "Error" in result["sub_results"][1].answer
        assert result["sub_results"][2].answer == "Third answer"
        assert "executor" in result["agent_calls"]

    def test_reasoning_steps_recorded(self):
        """Test that reasoning steps are properly recorded."""
        # Mock query engine
        mock_engine = MagicMock()

        result1 = QueryResult(
            success=True,
            answer="Answer",
            sources=[],
            chunks_retrieved=5,
            query_time_seconds=0.5,
        )

        mock_engine.query.return_value = result1

        # Create state
        state: AgentState = {
            "sub_queries": ["Query 1"],
            "execution_order": "parallel",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute
        result = sub_query_executor(state, mock_engine)

        # Verify reasoning steps structure
        assert len(result["reasoning_steps"]) == 1
        step = result["reasoning_steps"][0]
        assert step["agent"] == "executor"
        assert step["action"] == "sub_query_execution"
        assert "input" in step
        assert "output" in step
        assert "duration_ms" in step
        assert step["output"]["results_count"] == 1
        assert step["output"]["total_chunks_retrieved"] == 5

    def test_state_without_metadata_fields(self):
        """Test that executor initializes metadata fields if missing."""
        # Mock query engine
        mock_engine = MagicMock()

        result1 = QueryResult(
            success=True,
            answer="Answer",
            sources=[],
            chunks_retrieved=1,
            query_time_seconds=0.5,
        )

        mock_engine.query.return_value = result1

        # Create state without metadata fields
        state: AgentState = {
            "sub_queries": ["Query 1"],
            "execution_order": "parallel",
        }

        # Verify fields don't exist yet
        assert "agent_calls" not in state
        assert "reasoning_steps" not in state

        # Execute
        result = sub_query_executor(state, mock_engine)

        # Verify fields were initialized
        assert "agent_calls" in result
        assert "reasoning_steps" in result
        assert isinstance(result["agent_calls"], list)
        assert isinstance(result["reasoning_steps"], list)

    def test_total_chunks_calculation(self):
        """Test that total chunks retrieved is calculated correctly."""
        # Mock query engine
        mock_engine = MagicMock()

        # Mock results with different chunk counts
        result1 = QueryResult(
            success=True,
            answer="Answer 1",
            sources=[],
            chunks_retrieved=3,
            query_time_seconds=0.5,
        )

        result2 = QueryResult(
            success=True,
            answer="Answer 2",
            sources=[],
            chunks_retrieved=5,
            query_time_seconds=0.6,
        )

        result3 = QueryResult(
            success=True,
            answer="Answer 3",
            sources=[],
            chunks_retrieved=2,
            query_time_seconds=0.4,
        )

        mock_engine.query.side_effect = [result1, result2, result3]

        # Create state
        state: AgentState = {
            "sub_queries": ["Q1", "Q2", "Q3"],
            "execution_order": "parallel",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute
        result = sub_query_executor(state, mock_engine)

        # Verify total chunks calculation
        step = result["reasoning_steps"][0]
        assert step["output"]["total_chunks_retrieved"] == 10  # 3 + 5 + 2

    def test_default_execution_order(self):
        """Test that missing execution_order defaults to parallel."""
        # Mock query engine
        mock_engine = MagicMock()

        result1 = QueryResult(
            success=True,
            answer="Answer",
            sources=[],
            chunks_retrieved=1,
            query_time_seconds=0.5,
        )

        mock_engine.query.return_value = result1

        # Create state without execution_order
        state: AgentState = {
            "sub_queries": ["Query 1"],
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute (should default to parallel)
        result = sub_query_executor(state, mock_engine)

        # Verify execution completed
        assert len(result["sub_results"]) == 1
        assert "executor" in result["agent_calls"]
