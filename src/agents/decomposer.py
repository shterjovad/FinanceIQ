"""Query Decomposer Agent - Breaks complex queries into sub-queries."""

import json
import logging
import time

import litellm

from src.agents.models import AgentState
from src.config.settings import settings

logger = logging.getLogger(__name__)


def query_decomposer_agent(state: AgentState) -> AgentState:
    """Decompose complex query into manageable sub-queries.

    Uses GPT-4 to break down complex questions into 2-5 independent sub-queries
    that can be executed separately and then synthesized.

    Args:
        state: Current agent state containing original_question

    Returns:
        Updated state with sub_queries, execution_order, and reasoning metadata

    The decomposer:
    1. Analyzes the complex query structure
    2. Identifies key components that need separate answers
    3. Creates clear, specific sub-queries
    4. Determines if sub-queries should run parallel or sequential
    5. Records reasoning for transparency
    """
    start_time = time.time()

    original_question = state.get("original_question", "")
    logger.info(f"Decomposer analyzing query: {original_question[:100]}...")

    # Initialize metadata fields if not present
    if "agent_calls" not in state:
        state["agent_calls"] = []
    if "reasoning_steps" not in state:
        state["reasoning_steps"] = []

    try:
        # System prompt with clear guidelines
        system_prompt = """You are a query decomposition expert. Your task is to break complex questions into 2-5 simple, independently answerable sub-queries.

Guidelines:
1. Each sub-query must be independently answerable from document search
2. Sub-queries should cover all aspects of the original question
3. Use clear, specific language (avoid pronouns like "it", "they")
4. Include context in each sub-query so it stands alone
5. Limit to 5 sub-queries maximum to control costs

Execution Order:
- "parallel": Sub-queries are independent and can run simultaneously
- "sequential": Later sub-queries depend on earlier results

Return JSON format:
{
    "sub_queries": ["query1", "query2", ...],
    "execution_order": "parallel" or "sequential",
    "reasoning": "Brief explanation of decomposition strategy"
}

Examples:

Input: "How did iPhone sales compare Q3 vs Q4 and what drove the change?"
Output: {
    "sub_queries": [
        "What were Apple's iPhone sales figures in Q3?",
        "What were Apple's iPhone sales figures in Q4?",
        "What factors or events affected iPhone sales during Q3 and Q4?"
    ],
    "execution_order": "parallel",
    "reasoning": "Need Q3 and Q4 sales data plus contributing factors. All queries independent."
}

Input: "What are the main revenue streams and which grew fastest year-over-year?"
Output: {
    "sub_queries": [
        "What are the main revenue streams or business segments?",
        "What was the year-over-year growth rate for each revenue stream?"
    ],
    "execution_order": "sequential",
    "reasoning": "Need to identify revenue streams first, then compare their growth rates."
}

Input: "Compare gross margin to operating margin and explain the difference"
Output: {
    "sub_queries": [
        "What is the gross margin percentage?",
        "What is the operating margin percentage?",
        "What are the key differences between gross margin and operating margin?"
    ],
    "execution_order": "parallel",
    "reasoning": "All queries can be answered independently from financial definitions and data."
}"""

        user_prompt = f"Original Question: {original_question}"

        # Call LLM for decomposition
        response = litellm.completion(
            model=settings.AGENT_DECOMPOSER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,  # Deterministic for consistency
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        # Parse JSON response
        result = json.loads(response.choices[0].message.content)

        # Validate and extract fields
        sub_queries = result.get("sub_queries", [])
        execution_order = result.get("execution_order", "parallel")
        reasoning = result.get("reasoning", "")

        # Enforce maximum sub-queries limit
        if len(sub_queries) > settings.MAX_SUB_QUERIES:
            logger.warning(
                f"Decomposer generated {len(sub_queries)} sub-queries, "
                f"limiting to {settings.MAX_SUB_QUERIES}"
            )
            sub_queries = sub_queries[: settings.MAX_SUB_QUERIES]

        # Validate execution order
        if execution_order not in ["parallel", "sequential"]:
            logger.warning(
                f"Invalid execution order '{execution_order}', defaulting to 'parallel'"
            )
            execution_order = "parallel"

        # Update state
        state["sub_queries"] = sub_queries
        state["execution_order"] = execution_order

        # Record reasoning step
        duration_ms = int((time.time() - start_time) * 1000)
        state["reasoning_steps"].append(
            {
                "agent": "decomposer",
                "action": "query_decomposition",
                "input": {"question": original_question},
                "output": {
                    "sub_queries": sub_queries,
                    "execution_order": execution_order,
                    "reasoning": reasoning,
                },
                "duration_ms": duration_ms,
            }
        )

        state["agent_calls"].append("decomposer")

        logger.info(
            f"Query decomposed into {len(sub_queries)} sub-queries "
            f"({execution_order}) in {duration_ms}ms"
        )
        logger.debug(f"Sub-queries: {sub_queries}")

    except json.JSONDecodeError as e:
        # Handle JSON parse errors
        logger.error(f"Decomposer JSON parse error: {e}", exc_info=True)
        duration_ms = int((time.time() - start_time) * 1000)

        # Fallback: treat as single query
        state["sub_queries"] = [original_question]
        state["execution_order"] = "parallel"

        state["reasoning_steps"].append(
            {
                "agent": "decomposer",
                "action": "decomposition_failed",
                "input": {"question": original_question},
                "output": {"error": "JSON parse error", "fallback": "single_query"},
                "duration_ms": duration_ms,
            }
        )

        state["agent_calls"].append("decomposer")
        state["error"] = f"Decomposer JSON error: {str(e)}"

        logger.warning("Falling back to single query due to JSON parse error")

    except Exception as e:
        # Handle any other errors
        logger.error(f"Decomposer unexpected error: {e}", exc_info=True)
        duration_ms = int((time.time() - start_time) * 1000)

        # Fallback: treat as single query
        state["sub_queries"] = [original_question]
        state["execution_order"] = "parallel"

        state["reasoning_steps"].append(
            {
                "agent": "decomposer",
                "action": "decomposition_failed",
                "input": {"question": original_question},
                "output": {"error": str(e), "fallback": "single_query"},
                "duration_ms": duration_ms,
            }
        )

        state["agent_calls"].append("decomposer")
        state["error"] = f"Decomposer error: {str(e)}"

        logger.warning(f"Falling back to single query due to error: {e}")

    return state
