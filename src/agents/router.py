"""Query Router Agent - Classifies queries as simple or complex."""

import json
import logging
import time
from typing import Any

import litellm

from src.agents.models import AgentState
from src.config.settings import settings

logger = logging.getLogger(__name__)


def query_router_agent(state: AgentState) -> AgentState:
    """Classify query as simple or complex.

    Uses GPT-3.5-turbo (cheaper/faster) to determine if a query requires
    decomposition or can be answered directly.

    Classification criteria:
    - Simple: Single fact, single metric, single document section
    - Complex: Multiple parts, comparisons, multi-step reasoning

    Args:
        state: Current agent state with original_question

    Returns:
        Updated state with query_type and complexity_reasoning
    """
    start_time = time.time()

    question = state.get("original_question", "")
    logger.info(f"Router analyzing query: {question[:100]}...")

    # System prompt with few-shot examples
    system_prompt = """You are a query classifier for a financial document Q&A system.

Classify each question as either SIMPLE or COMPLEX.

SIMPLE queries:
- Ask for a single fact or metric
- Reference one document section
- No comparisons or multi-step reasoning

Examples:
- "What was Apple's total revenue in 2024?"
- "Who is the CEO?"
- "What is the company's mission statement?"
- "How many employees does the company have?"

COMPLEX queries:
- Ask multiple questions at once
- Require comparisons (time periods, products, metrics)
- Need multi-step reasoning
- Span multiple document sections

Examples:
- "How did iPhone sales compare in Q3 vs Q4 and what drove the change?"
- "What are the top 3 revenue drivers and how did they change year-over-year?"
- "Compare R&D spending between 2023 and 2024 and explain the investments"
- "What were the biggest risks and how does management plan to address them?"

Return JSON only:
{
    "type": "simple" or "complex",
    "reasoning": "Brief explanation of classification"
}"""

    user_prompt = f"Classify this query:\n\n{question}"

    try:
        # Call LLM with JSON mode
        response = litellm.completion(
            model=settings.AGENT_ROUTER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,  # Deterministic
            max_tokens=200,  # Keep response short
        )

        # Parse JSON response
        result = json.loads(response.choices[0].message.content)

        query_type = result.get("type", "simple")
        reasoning = result.get("reasoning", "No reasoning provided")

        # Validate query_type
        if query_type not in ["simple", "complex"]:
            logger.warning(
                f"Invalid query_type '{query_type}' returned, defaulting to 'simple'"
            )
            query_type = "simple"
            reasoning = f"Invalid classification returned: {query_type}. Defaulting to simple."

        # Update state
        state["query_type"] = query_type  # type: ignore
        state["complexity_reasoning"] = reasoning

        # Initialize metadata fields if not present
        if "agent_calls" not in state:
            state["agent_calls"] = []
        if "reasoning_steps" not in state:
            state["reasoning_steps"] = []

        # Record this agent call
        state["agent_calls"].append("router")

        # Add to reasoning steps for transparency
        duration_ms = int((time.time() - start_time) * 1000)
        state["reasoning_steps"].append(
            {
                "agent": "router",
                "action": "query_classification",
                "input": {"question": question},
                "output": {"type": query_type, "reasoning": reasoning},
                "duration_ms": duration_ms,
            }
        )

        logger.info(
            f"Query classified as '{query_type}' in {duration_ms}ms: {reasoning}"
        )

        return state

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse router response as JSON: {e}")
        # Fallback to simple
        state["query_type"] = "simple"  # type: ignore
        state["complexity_reasoning"] = (
            "Classification failed (JSON parse error), defaulting to simple query"
        )
        if "agent_calls" not in state:
            state["agent_calls"] = []
        state["agent_calls"].append("router")
        return state

    except Exception as e:
        logger.error(f"Router agent failed: {e}", exc_info=True)
        # Fallback to simple on any error
        state["query_type"] = "simple"  # type: ignore
        state["complexity_reasoning"] = (
            f"Classification failed ({type(e).__name__}), defaulting to simple query"
        )
        state["error"] = f"Router error: {str(e)}"
        if "agent_calls" not in state:
            state["agent_calls"] = []
        state["agent_calls"].append("router")
        return state
