"""Answer Synthesis Agent - Combines sub-answers into coherent final response."""

import logging
import time

import litellm

from src.agents.models import AgentState
from src.config.settings import settings
from src.rag.models import SourceCitation

logger = logging.getLogger(__name__)


def answer_synthesis_agent(state: AgentState) -> AgentState:
    """Synthesize sub-query results into a coherent final answer.

    Uses GPT-4 to combine multiple sub-answers into a comprehensive response
    that directly addresses the original question. Maintains citation integrity
    and provides well-structured output.

    Args:
        state: Current agent state containing sub_results and original_question

    Returns:
        Updated state with final_answer and all_sources populated

    The synthesizer:
    1. Collects all sub-answers and their sources
    2. Builds context from sub-results
    3. Uses LLM to create coherent synthesis
    4. Maintains all source citations
    5. Records reasoning for transparency
    """
    start_time = time.time()

    original_question = state.get("original_question", "")
    sub_queries = state.get("sub_queries", [])
    sub_results = state.get("sub_results", [])

    logger.info(
        f"Synthesizer combining {len(sub_results)} sub-answers for: {original_question[:100]}..."
    )

    # Initialize metadata fields if not present
    if "agent_calls" not in state:
        state["agent_calls"] = []
    if "reasoning_steps" not in state:
        state["reasoning_steps"] = []

    try:
        # Build context from sub-results
        context_parts = []
        all_sources: list[SourceCitation] = []

        for i, (sub_q, result) in enumerate(zip(sub_queries, sub_results, strict=True), 1):
            # Format each sub-answer with sources
            source_info = ""
            if result.sources:
                source_refs = [
                    f"Page {', '.join(map(str, s.page_numbers))}"
                    for s in result.sources
                ]
                source_info = f"\nSources: {'; '.join(source_refs)}"

            context_parts.append(
                f"Sub-Question {i}: {sub_q}\n"
                f"Answer: {result.answer}{source_info}"
            )

            # Collect all unique sources
            for source in result.sources:
                # Avoid duplicate sources
                if not any(
                    s.document_id == source.document_id
                    and s.page_numbers == source.page_numbers
                    for s in all_sources
                ):
                    all_sources.append(source)

        synthesis_context = "\n\n".join(context_parts)

        # System prompt for synthesis
        system_prompt = """You are an expert at synthesizing information from multiple sources.
Your task is to combine sub-answers into a comprehensive, coherent response.

Requirements:
1. Directly address the original question
2. Integrate information from all sub-answers smoothly
3. Maintain logical flow and structure
4. Be clear and concise
5. Use markdown formatting for readability
6. Do NOT invent information not present in sub-answers
7. If sub-answers contain conflicting information, acknowledge it

Style Guidelines:
- Use proper paragraphs and sections
- Use bullet points or numbered lists when appropriate
- Bold key terms or numbers
- Keep the tone professional and informative
"""

        user_prompt = f"""Original Question: {original_question}

Sub-Answers:
{synthesis_context}

Provide a comprehensive final answer that directly addresses the original question by synthesizing the information above:"""

        # Call LLM for synthesis
        response = litellm.completion(
            model=settings.AGENT_SYNTHESIZER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,  # Slightly creative for better synthesis
            max_tokens=1000,
        )

        final_answer = response.choices[0].message.content

        # Update state
        state["final_answer"] = final_answer
        state["all_sources"] = all_sources

        # Record reasoning step
        duration_ms = int((time.time() - start_time) * 1000)

        state["reasoning_steps"].append(
            {
                "agent": "synthesizer",
                "action": "answer_synthesis",
                "input": {
                    "original_question": original_question,
                    "sub_results_count": len(sub_results),
                },
                "output": {
                    "final_answer_length": len(final_answer),
                    "total_sources": len(all_sources),
                },
                "duration_ms": duration_ms,
            }
        )

        state["agent_calls"].append("synthesizer")

        logger.info(
            f"Synthesis completed in {duration_ms}ms "
            f"({len(all_sources)} sources, {len(final_answer)} chars)"
        )

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Synthesizer unexpected error: {e}", exc_info=True)
        duration_ms = int((time.time() - start_time) * 1000)

        # Fallback: concatenate sub-answers
        logger.warning("Falling back to simple concatenation of sub-answers")

        fallback_parts = []
        all_sources = []

        for _i, (sub_q, result) in enumerate(zip(sub_queries, sub_results, strict=True), 1):
            fallback_parts.append(f"**{sub_q}**\n{result.answer}")

            # Collect sources
            for source in result.sources:
                if not any(
                    s.document_id == source.document_id
                    and s.page_numbers == source.page_numbers
                    for s in all_sources
                ):
                    all_sources.append(source)

        state["final_answer"] = "\n\n".join(fallback_parts)
        state["all_sources"] = all_sources

        state["reasoning_steps"].append(
            {
                "agent": "synthesizer",
                "action": "synthesis_failed",
                "input": {"original_question": original_question},
                "output": {"error": str(e), "fallback": "concatenation"},
                "duration_ms": duration_ms,
            }
        )

        state["agent_calls"].append("synthesizer")
        state["error"] = f"Synthesizer error: {str(e)}"

    return state
