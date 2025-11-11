"""Multi-agent orchestration for complex query decomposition.

This module implements a LangGraph-based multi-agent system that can:
1. Analyze query complexity (simple vs complex)
2. Decompose complex queries into sub-queries
3. Execute sub-queries in parallel or sequential order
4. Synthesize comprehensive final answers

Agents:
- QueryRouterAgent: Classifies queries as simple or complex
- QueryDecomposerAgent: Breaks complex queries into sub-queries
- SubQueryExecutor: Executes sub-queries using RAG system
- AnswerSynthesisAgent: Combines sub-answers into final response
"""

from src.agents.models import AgentState

__all__ = ["AgentState"]
