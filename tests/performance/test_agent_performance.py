"""Performance benchmarking tests for multi-agent system.

These tests measure actual performance metrics and can be used for:
- Regression testing (ensuring performance doesn't degrade)
- Performance profiling (identifying bottlenecks)
- Comparison testing (agents vs non-agents)
"""

import time

import pytest

from src.agents.models import AgentState
from src.agents.router import query_router_agent
from src.agents.workflow import create_agent_workflow
from src.rag.models import QueryResult, SourceCitation


@pytest.mark.performance
class TestAgentPerformance:
    """Performance benchmarking tests for agent system."""

    def test_router_latency(self):
        """Test that query router completes within acceptable time."""
        # Test simple query classification
        simple_state: AgentState = {
            "original_question": "What was total revenue?",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        start_time = time.time()
        result = query_router_agent(simple_state)
        latency = time.time() - start_time

        # Router should complete in <3s (LLM call)
        assert latency < 3.0, f"Router took {latency:.2f}s, expected <3.0s"
        assert result["query_type"] in ["simple", "complex"]

        # Test complex query classification
        complex_state: AgentState = {
            "original_question": "How did iPhone sales compare in Q3 vs Q4 and what drove the change?",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        start_time = time.time()
        result = query_router_agent(complex_state)
        latency = time.time() - start_time

        # Router should complete in <3s (LLM call)
        assert latency < 3.0, f"Router took {latency:.2f}s, expected <3.0s"
        assert result["query_type"] in ["simple", "complex"]

    def test_simple_query_performance(self):
        """Test that simple queries complete within acceptable time."""

        class FastMockQueryEngine:
            """Mock query engine with realistic timing."""

            def query(self, question: str) -> QueryResult:
                time.sleep(0.5)  # Simulate RAG query time
                return QueryResult(
                    success=True,
                    answer="Total revenue was $100M",
                    sources=[
                        SourceCitation(
                            document_id="test_doc",
                            page_numbers=[1],
                            relevance_score=0.9,
                            snippet="Revenue: $100M",
                        )
                    ],
                    chunks_retrieved=3,
                    query_time_seconds=0.5,
                )

        workflow = create_agent_workflow(query_engine=FastMockQueryEngine())

        initial_state: AgentState = {
            "original_question": "What was total revenue?",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        start_time = time.time()
        result = workflow.invoke(initial_state)
        total_time = time.time() - start_time

        # Simple path should complete in <5s
        # Router (~3s) + Simple path execution (0.5s) = ~3.5s
        assert total_time < 5.0, f"Simple query took {total_time:.2f}s, expected <5.0s"
        assert result["query_type"] == "simple"

    def test_complex_query_performance(self):
        """Test that complex queries complete within acceptable time."""

        class FastMockQueryEngine:
            """Mock query engine with realistic timing."""

            def query(self, question: str) -> QueryResult:
                time.sleep(0.5)  # Simulate RAG query time
                return QueryResult(
                    success=True,
                    answer=f"Answer for: {question}",
                    sources=[
                        SourceCitation(
                            document_id="test_doc",
                            page_numbers=[1],
                            relevance_score=0.9,
                            snippet="Relevant content",
                        )
                    ],
                    chunks_retrieved=3,
                    query_time_seconds=0.5,
                )

        workflow = create_agent_workflow(query_engine=FastMockQueryEngine())

        initial_state: AgentState = {
            "original_question": "How did iPhone sales compare in Q3 vs Q4 and what drove the change?",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        start_time = time.time()
        result = workflow.invoke(initial_state)
        total_time = time.time() - start_time

        # Complex path should complete in <20s
        # Router (~3s) + Decomposer (~5s) + Executor parallel (0.5s) + Synthesizer (~5s) = ~13.5s
        assert total_time < 20.0, f"Complex query took {total_time:.2f}s, expected <20.0s"

        if result["query_type"] == "complex":
            # Verify all agents executed
            assert "decomposer" in result["agent_calls"]
            assert "executor" in result["agent_calls"]
            assert "synthesizer" in result["agent_calls"]

    def test_per_agent_timing(self):
        """Test that each agent's execution time is tracked."""

        class FastMockQueryEngine:
            """Mock query engine with realistic timing."""

            def query(self, question: str) -> QueryResult:
                time.sleep(0.1)  # Fast mock
                return QueryResult(
                    success=True,
                    answer="Mock answer",
                    sources=[],
                    chunks_retrieved=1,
                    query_time_seconds=0.1,
                )

        workflow = create_agent_workflow(query_engine=FastMockQueryEngine())

        initial_state: AgentState = {
            "original_question": "Compare Q3 and Q4 revenue",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        result = workflow.invoke(initial_state)

        # Verify reasoning steps contain timing information
        reasoning_steps = result.get("reasoning_steps", [])
        assert len(reasoning_steps) > 0, "No reasoning steps recorded"

        for step in reasoning_steps:
            assert "agent" in step
            assert "duration_ms" in step
            assert isinstance(step["duration_ms"], int)
            assert step["duration_ms"] >= 0

            # Log timing for visibility
            print(f"Agent: {step['agent']}, Duration: {step['duration_ms']}ms")

    def test_parallel_vs_sequential_speedup(self):
        """Test that parallel execution provides speedup over sequential."""

        class SlowMockQueryEngine:
            """Mock query engine with artificial delay."""

            def query(self, question: str) -> QueryResult:
                time.sleep(1.0)  # 1 second delay per query
                return QueryResult(
                    success=True,
                    answer="Mock answer",
                    sources=[],
                    chunks_retrieved=1,
                    query_time_seconds=1.0,
                )

        workflow = create_agent_workflow(query_engine=SlowMockQueryEngine())

        initial_state: AgentState = {
            "original_question": "Compare Q1, Q2, Q3, and Q4 revenue and explain trends",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        result = workflow.invoke(initial_state)

        if result["query_type"] == "complex" and result.get("execution_order") == "parallel":
            num_sub_queries = len(result.get("sub_queries", []))

            # Get executor timing from reasoning steps
            reasoning_steps = result.get("reasoning_steps", [])
            executor_step = next(
                (s for s in reasoning_steps if s.get("agent") == "executor"), None
            )

            if executor_step and num_sub_queries >= 2:
                executor_time_ms = executor_step.get("duration_ms", 0)
                executor_time_s = executor_time_ms / 1000

                # Parallel execution should be much faster than sequential
                # For N queries of 1s each:
                # - Sequential would take N seconds
                # - Parallel should take ~1 second (plus small overhead)
                # Allow up to 2.5x the single query time for parallel execution (overhead)
                max_parallel_time = 1.0 * 2.5  # 2.5 seconds max

                assert (
                    executor_time_s < max_parallel_time
                ), f"Executor took {executor_time_s:.2f}s for {num_sub_queries} queries (parallel), expected <{max_parallel_time:.2f}s"

                # Calculate speedup factor
                sequential_time = num_sub_queries * 1.0
                speedup = sequential_time / executor_time_s

                print(f"Parallel speedup: {speedup:.2f}x ({num_sub_queries} queries)")
                print(f"Sequential would take: {sequential_time:.2f}s")
                print(f"Parallel took: {executor_time_s:.2f}s")

                # Speedup should be at least 1.5x for 2+ queries
                assert (
                    speedup >= 1.5
                ), f"Parallel speedup was only {speedup:.2f}x, expected >=1.5x"

    def test_memory_efficiency(self):
        """Test that agent workflow doesn't leak memory or grow state excessively."""
        import sys

        class FastMockQueryEngine:
            """Mock query engine."""

            def query(self, question: str) -> QueryResult:
                return QueryResult(
                    success=True,
                    answer="Mock answer",
                    sources=[],
                    chunks_retrieved=1,
                    query_time_seconds=0.1,
                )

        workflow = create_agent_workflow(query_engine=FastMockQueryEngine())

        initial_state: AgentState = {
            "original_question": "Compare revenue across quarters",
            "agent_calls": [],
            "reasoning_steps": [],
        }

        result = workflow.invoke(initial_state)

        # Check that state size is reasonable
        state_size = sys.getsizeof(result)

        # State should be <1MB (very generous limit)
        assert state_size < 1_000_000, f"State size is {state_size} bytes, expected <1MB"

        # Verify state doesn't have excessive nesting
        def get_max_depth(obj, current_depth=0, max_depth=10):
            """Get maximum nesting depth of a dictionary."""
            if current_depth > max_depth or not isinstance(obj, dict):
                return current_depth

            if not obj:
                return current_depth

            return max(
                get_max_depth(v, current_depth + 1, max_depth) for v in obj.values()
            )

        max_depth = get_max_depth(result)
        # State should not be nested more than 5 levels deep
        assert max_depth <= 5, f"State has {max_depth} levels of nesting, expected <=5"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])  # -s shows print statements
