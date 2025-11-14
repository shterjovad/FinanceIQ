"""Chat component for conversational RAG interface."""

import logging
from typing import Any, TypedDict

import streamlit as st

from src.rag.models import SourceCitation
from src.rag.service import RAGService

logger = logging.getLogger(__name__)


class ChatMessage(TypedDict):
    """Type definition for chat messages in session state."""

    role: str
    content: str
    sources: list[SourceCitation] | None
    reasoning_steps: list[dict[str, Any]] | None
    query_type: str | None


class ChatComponent:
    """Handles conversational chat interface for RAG queries.

    Provides a ChatGPT-like interface with:
    - Persistent chat history
    - Source citations in expandable sections
    - Agent reasoning steps display (when multi-agent mode is enabled)
    - Error handling for unavailable services
    """

    def __init__(
        self,
        rag_service: RAGService | None,
        session_id: str | None = None,
    ) -> None:
        """Initialize the chat component.

        Args:
            rag_service: RAGService instance for processing queries, or None if unavailable
            session_id: Browser session ID for query isolation
        """
        self.rag_service = rag_service
        self.session_id = session_id
        logger.debug(
            f"ChatComponent initialized (rag_service available: {rag_service is not None}, "
            f"session_id: {session_id[:8] if session_id else 'None'}...)"
        )

    def render(self) -> None:
        """Render the chat interface with history and input."""
        st.header("Chat with Your Documents")

        # Check if RAG service is available
        if self.rag_service is None:
            st.warning(
                "⚠ RAG system unavailable. Please ensure:\n\n"
                "1. Qdrant is running: `docker compose up -d`\n"
                "2. OPENAI_API_KEY is configured in .env\n"
                "3. Documents have been uploaded and indexed"
            )
            return

        # Initialize chat history in session state
        if "messages" not in st.session_state:
            st.session_state.messages = []
            logger.info("Initialized empty chat history in session state")

        # Initialize processing flag
        if "processing_query" not in st.session_state:
            st.session_state.processing_query = False

        # Check if we need to process a pending query
        if st.session_state.processing_query:
            # Get the last user message (the pending query)
            last_message = st.session_state.messages[-1]
            if last_message["role"] == "user":
                # Display all messages up to this point
                for message in st.session_state.messages:
                    self._render_message(message)

                # Show spinner and process the query
                with st.spinner("Thinking..."):
                    self._process_query(last_message["content"])

                # Reset processing flag
                st.session_state.processing_query = False
                st.rerun()
            else:
                # Something went wrong, reset flag
                st.session_state.processing_query = False

        # Display chat history (only when not processing, since processing block above handles it)
        if not st.session_state.processing_query:
            for message in st.session_state.messages:
                self._render_message(message)

        # Chat input at the bottom
        if prompt := st.chat_input("Ask a question about your documents..."):
            self._handle_user_input(prompt)

    def _handle_user_input(self, user_message: str) -> None:
        """Handle user input by adding message to chat and triggering processing.

        Args:
            user_message: The user's question or message
        """
        if not user_message or not user_message.strip():
            logger.warning("Empty user message received")
            return

        logger.info(f"Received user message: {user_message[:100]}...")

        # Add user message to session state
        user_msg: ChatMessage = {
            "role": "user",
            "content": user_message,
            "sources": None,
            "reasoning_steps": None,
            "query_type": None,
        }
        st.session_state.messages.append(user_msg)

        # Set processing flag to trigger query on next render
        st.session_state.processing_query = True

        # Rerun to display the question and show spinner
        st.rerun()

    def _process_query(self, user_message: str) -> None:
        """Process a query using the RAG service and add response to chat.

        Args:
            user_message: The user's question to process
        """
        logger.info(f"Processing query: {user_message[:100]}...")

        try:
            # Temporarily override use_agents based on UI toggle
            original_use_agents = self.rag_service.use_agents  # type: ignore[union-attr]
            use_agents_from_ui = st.session_state.get("use_agents", False)

            self.rag_service.use_agents = use_agents_from_ui  # type: ignore[union-attr]

            try:
                # Call RAG service with session isolation
                result = self.rag_service.query(  # type: ignore[union-attr]
                    user_message,
                    session_id=self.session_id,
                )

                # Extract agent metadata if agents were used
                reasoning_steps = None
                query_type = None

                if use_agents_from_ui and self.rag_service.agent_workflow:  # type: ignore[union-attr]
                    # Get reasoning steps from last agent execution
                    reasoning_steps, agent_query_type = self.rag_service.get_last_reasoning_steps()  # type: ignore[union-attr]

                    if agent_query_type:
                        query_type = "agent-processed"

                # Add assistant response to session state
                assistant_msg: ChatMessage = {
                    "role": "assistant",
                    "content": result.answer,
                    "sources": result.sources,
                    "reasoning_steps": reasoning_steps,
                    "query_type": query_type,
                }
                st.session_state.messages.append(assistant_msg)

                logger.info(
                    f"Query completed in {result.query_time_seconds:.2f}s "
                    f"with {len(result.sources)} sources"
                )

            finally:
                # Restore original use_agents setting
                self.rag_service.use_agents = original_use_agents  # type: ignore[union-attr]

        except Exception as e:
            logger.error(f"Query failed: {str(e)}", exc_info=True)

            # Add error message to chat
            error_msg: ChatMessage = {
                "role": "assistant",
                "content": f"❌ Sorry, I encountered an error: {str(e)}",
                "sources": None,
                "reasoning_steps": None,
                "query_type": None,
            }
            st.session_state.messages.append(error_msg)

    def _render_message(self, message: ChatMessage) -> None:
        """Render a single chat message with optional sources and agent info.

        Args:
            message: Message dictionary with role, content, sources, and agent metadata
        """
        role = message["role"]
        content = message["content"]
        sources = message.get("sources")
        query_type = message.get("query_type")
        reasoning_steps = message.get("reasoning_steps")

        with st.chat_message(role):
            # Show agent processing badge if applicable
            if role == "assistant" and query_type == "agent-processed":
                st.caption("🤖 Processed with multi-agent system")

            st.markdown(content)

            # Display reasoning steps if available
            if role == "assistant" and reasoning_steps:
                self._display_reasoning_steps(reasoning_steps)

            # Display sources if available (only for assistant messages)
            if role == "assistant" and sources:
                self._display_sources(sources)

    def _display_sources(self, sources: list[SourceCitation]) -> None:
        """Display source citations in expandable sections.

        Args:
            sources: List of source citations to display
        """
        if not sources:
            return

        st.markdown("---")
        st.markdown("**📚 Sources**")

        for i, source in enumerate(sources, 1):
            # Create expandable section for each source
            with st.expander(
                f"Source {i} - Pages {', '.join(map(str, source.page_numbers))} "
                f"(Relevance: {source.relevance_score:.1%})"
            ):
                st.markdown(f"**Document ID:** `{source.document_id}`")
                st.markdown(f"**Pages:** {', '.join(map(str, source.page_numbers))}")
                st.markdown(
                    f"**Relevance Score:** {source.relevance_score:.4f} ({source.relevance_score:.1%})"
                )
                st.markdown("**Content Preview:**")
                st.text(source.snippet)

    def _display_reasoning_steps(self, reasoning_steps: list[dict[str, Any]]) -> None:
        """Display agent reasoning steps in expandable sections.

        Args:
            reasoning_steps: List of reasoning step dictionaries from agent workflow
        """
        if not reasoning_steps:
            return

        st.markdown("---")
        st.markdown("**🧠 Agent Reasoning**")

        with st.expander(f"View {len(reasoning_steps)} reasoning steps", expanded=False):
            for i, step in enumerate(reasoning_steps, 1):
                agent = step.get("agent", "unknown")
                action = step.get("action", "unknown")
                duration_ms = step.get("duration_ms", 0)

                # Display step header
                st.markdown(f"**Step {i}: {agent.title()} - {action.replace('_', ' ').title()}**")
                st.caption(f"⏱ Duration: {duration_ms}ms")

                # Display input/output based on agent type
                output_data = step.get("output", {})

                if agent == "router":
                    st.markdown(f"**Classification:** {output_data.get('type', 'N/A')}")
                    st.markdown(f"**Reasoning:** {output_data.get('reasoning', 'N/A')}")

                elif agent == "decomposer":
                    sub_queries = output_data.get("sub_queries", [])
                    execution_order = output_data.get("execution_order", "N/A")
                    st.markdown(f"**Sub-queries ({len(sub_queries)}):**")
                    for j, sq in enumerate(sub_queries, 1):
                        st.markdown(f"{j}. {sq}")
                    st.markdown(f"**Execution:** {execution_order}")

                elif agent == "executor":
                    results_count = output_data.get("results_count", 0)
                    total_chunks = output_data.get("total_chunks_retrieved", 0)
                    st.markdown(f"**Results:** {results_count} sub-queries executed")
                    st.markdown(f"**Chunks Retrieved:** {total_chunks}")

                elif agent == "synthesizer":
                    answer_length = output_data.get("final_answer_length", 0)
                    total_sources = output_data.get("total_sources", 0)
                    st.markdown(f"**Answer Length:** {answer_length} characters")
                    st.markdown(f"**Sources Combined:** {total_sources}")

                # Add separator between steps
                if i < len(reasoning_steps):
                    st.markdown("---")
