"""Chat component for conversational RAG interface."""

import logging
from typing import TypedDict

import streamlit as st

from src.rag.models import SourceCitation
from src.rag.query_engine import RAGQueryEngine

logger = logging.getLogger(__name__)


class ChatMessage(TypedDict):
    """Type definition for chat messages in session state."""

    role: str
    content: str
    sources: list[SourceCitation] | None


class ChatComponent:
    """Handles conversational chat interface for RAG queries.

    Provides a ChatGPT-like interface with:
    - Persistent chat history
    - Example questions for new sessions
    - Source citations in expandable sections
    - Error handling for unavailable services
    """

    def __init__(self, query_engine: RAGQueryEngine | None) -> None:
        """Initialize the chat component.

        Args:
            query_engine: RAGQueryEngine instance for processing queries, or None if unavailable
        """
        self.query_engine = query_engine
        logger.debug(
            f"ChatComponent initialized (query_engine available: {query_engine is not None})"
        )

    def render(self) -> None:
        """Render the chat interface with history and input."""
        st.header("Chat with Your Documents")

        # Check if query engine is available
        if self.query_engine is None:
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

        # Show example questions if chat history is empty
        if not st.session_state.messages:
            self._show_example_questions()
        else:
            # Display existing chat history
            for message in st.session_state.messages:
                self._render_message(message)

        # Chat input at the bottom
        if prompt := st.chat_input("Ask a question about your documents..."):
            self._handle_user_input(prompt)

    def _show_example_questions(self) -> None:
        """Display example questions that users can click to start a conversation."""
        st.markdown("### Example Questions")
        st.markdown("Get started by asking one of these questions:")

        # Create 2 columns for 4 example questions
        col1, col2 = st.columns(2)

        examples = [
            "What were the main revenue drivers?",
            "What are the top risk factors?",
            "How did operating expenses change?",
            "What is the company's cash position?",
        ]

        with col1:
            if st.button(examples[0], key="example_0", use_container_width=True):
                self._handle_user_input(examples[0])
            if st.button(examples[1], key="example_1", use_container_width=True):
                self._handle_user_input(examples[1])

        with col2:
            if st.button(examples[2], key="example_2", use_container_width=True):
                self._handle_user_input(examples[2])
            if st.button(examples[3], key="example_3", use_container_width=True):
                self._handle_user_input(examples[3])

    def _handle_user_input(self, user_message: str) -> None:
        """Handle user input by querying the RAG engine and updating chat history.

        Args:
            user_message: The user's question or message
        """
        if not user_message or not user_message.strip():
            logger.warning("Empty user message received")
            return

        logger.info(f"Processing user message: {user_message[:100]}...")

        # Add user message to session state
        user_msg: ChatMessage = {
            "role": "user",
            "content": user_message,
            "sources": None,
        }
        st.session_state.messages.append(user_msg)

        # Query the RAG engine
        try:
            # Call query engine
            result = self.query_engine.query(user_message)  # type: ignore[union-attr]

            # Add assistant response to session state
            assistant_msg: ChatMessage = {
                "role": "assistant",
                "content": result.answer,
                "sources": result.sources,
            }
            st.session_state.messages.append(assistant_msg)

            logger.info(
                f"Query completed in {result.query_time_seconds:.2f}s "
                f"with {len(result.sources)} sources"
            )

        except Exception as e:
            logger.error(f"Query failed: {str(e)}", exc_info=True)

            # Add error message to chat
            error_msg: ChatMessage = {
                "role": "assistant",
                "content": f"❌ Sorry, I encountered an error: {str(e)}",
                "sources": None,
            }
            st.session_state.messages.append(error_msg)

        # Force Streamlit to rerun and display messages in correct order
        st.rerun()

    def _render_message(self, message: ChatMessage) -> None:
        """Render a single chat message with optional sources.

        Args:
            message: Message dictionary with role, content, and optional sources
        """
        role = message["role"]
        content = message["content"]
        sources = message.get("sources")

        with st.chat_message(role):
            st.markdown(content)

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
