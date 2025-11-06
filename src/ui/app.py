"""FinanceIQ - Financial Document Analysis Application.

This is the main entry point for the Streamlit web application.
"""

import logging

import streamlit as st
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from src.config.settings import settings
from src.pdf_processor.logging_config import setup_logging
from src.rag.embedder import EmbeddingGenerator
from src.rag.query_engine import RAGQueryEngine
from src.rag.vector_store import VectorStoreManager
from src.ui.components.upload import PDFUploadComponent

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)


def check_qdrant_connection() -> bool:
    """Check if Qdrant is accessible at the configured host and port.

    Returns:
        bool: True if connection successful, False otherwise.
    """
    try:
        client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            timeout=3,  # Short timeout for quick feedback
        )
        # Try to get collections to verify connection
        client.get_collections()
        logger.info(
            f"Successfully connected to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}"
        )
        return True
    except (UnexpectedResponse, ConnectionError, TimeoutError, Exception) as e:
        logger.warning(f"Failed to connect to Qdrant: {str(e)}")
        return False


def initialize_rag_components() -> tuple[EmbeddingGenerator | None, VectorStoreManager | None]:
    """Initialize RAG components (embedder and vector store).

    Returns:
        Tuple of (embedder, vector_store). Both will be None if initialization fails.
    """
    try:
        # Check if API key is configured
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not configured, RAG indexing disabled")
            return None, None

        # Initialize embedding generator
        embedder = EmbeddingGenerator(
            embedding_model=settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
        )
        logger.info(f"Initialized EmbeddingGenerator with model {settings.EMBEDDING_MODEL}")

        # Initialize vector store
        vector_store = VectorStoreManager(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            collection_name=settings.QDRANT_COLLECTION,
        )
        logger.info(
            f"Initialized VectorStoreManager connected to {settings.QDRANT_HOST}:{settings.QDRANT_PORT}"
        )

        return embedder, vector_store

    except Exception as e:
        logger.warning(f"Failed to initialize RAG components: {str(e)}")
        return None, None


def render_query_interface(query_engine: RAGQueryEngine | None) -> None:
    """Render the query interface for asking questions.

    Args:
        query_engine: RAGQueryEngine instance, or None if unavailable
    """
    st.header("Ask Questions About Your Documents")

    if query_engine is None:
        st.warning(
            "⚠ Query engine unavailable. Please ensure:\n\n"
            "1. Qdrant is running: `docker compose up -d`\n"
            "2. OPENAI_API_KEY is configured in .env\n"
            "3. Documents have been uploaded and indexed"
        )
        return

    # Example questions
    st.markdown("**Example questions:**")
    example_col1, example_col2 = st.columns(2)
    with example_col1:
        st.caption("• What were the main revenue drivers?")
        st.caption("• What are the top risk factors?")
    with example_col2:
        st.caption("• How did operating expenses change?")
        st.caption("• What is the company's cash position?")

    st.markdown("---")

    # Query input
    question = st.text_input(
        "Your question:",
        placeholder="Ask a question about your uploaded documents...",
        help="Ask any question about the financial documents you've uploaded",
    )

    # Submit button
    if st.button("🔍 Search", type="primary"):
        if not question or not question.strip():
            st.warning("Please enter a question")
        else:
            # Show spinner while processing
            with st.spinner("Searching documents and generating answer..."):
                try:
                    # Query the engine
                    result = query_engine.query(question)

                    # Display answer
                    st.markdown("### Answer")
                    st.markdown(result.answer)

                    # Display query time
                    st.caption(f"⏱️ Query time: {result.query_time_seconds:.2f}s")

                    # Display sources
                    if result.sources:
                        st.markdown("---")
                        st.markdown("### 📚 Sources")

                        for i, source in enumerate(result.sources, 1):
                            with st.expander(
                                f"Source {i} - Pages {', '.join(map(str, source.page_numbers))} "
                                f"(Relevance: {source.relevance_score:.1%})"
                            ):
                                st.markdown(f"**Document ID:** `{source.document_id}`")
                                st.markdown(
                                    f"**Pages:** {', '.join(map(str, source.page_numbers))}"
                                )
                                st.markdown(
                                    f"**Relevance Score:** {source.relevance_score:.4f} ({source.relevance_score:.1%})"
                                )
                                st.markdown("**Content Preview:**")
                                st.text(source.snippet)
                    else:
                        st.info("No sources found for this query")

                except Exception as e:
                    logger.error(f"Query failed: {str(e)}", exc_info=True)
                    st.error(f"❌ Query failed: {str(e)}")

    # Technical details in expander
    with st.expander("🔧 System Configuration"):
        st.markdown(
            f"**Vector Database:** Qdrant @ {settings.QDRANT_HOST}:{settings.QDRANT_PORT}\n\n"
            f"**Embedding Model:** {settings.EMBEDDING_MODEL}\n\n"
            f"**Primary LLM:** {settings.PRIMARY_LLM}\n\n"
            f"**Fallback LLM:** {settings.FALLBACK_LLM}\n\n"
            f"**Retrieval Settings:** Top {settings.TOP_K_CHUNKS} chunks, "
            f"min relevance {settings.MIN_RELEVANCE_SCORE}"
        )


def main() -> None:
    """Main application entry point."""
    # Set page configuration
    st.set_page_config(
        page_title="FinanceIQ",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Display main title
    st.title("FinanceIQ - Financial Document Analysis")

    # Initialize RAG components
    embedder, vector_store = initialize_rag_components()

    # Initialize query engine if RAG components available
    query_engine = None
    if embedder and vector_store:
        try:
            query_engine = RAGQueryEngine(
                vector_store=vector_store,
                embedder=embedder,
                primary_llm=settings.PRIMARY_LLM,
                fallback_llm=settings.FALLBACK_LLM,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                top_k=settings.TOP_K_CHUNKS,
                min_score=settings.MIN_RELEVANCE_SCORE,
            )
            logger.info("Initialized RAGQueryEngine")
        except Exception as e:
            logger.warning(f"Failed to initialize query engine: {str(e)}")

    # Show RAG status in sidebar
    with st.sidebar:
        st.subheader("System Status")
        if query_engine:
            st.success("✓ RAG System Ready")
            st.caption(f"Model: {settings.EMBEDDING_MODEL}")
            st.caption(f"Vector DB: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
            st.caption(f"LLM: {settings.PRIMARY_LLM}")
        else:
            st.warning("⚠ RAG System Unavailable")
            st.caption("Documents can be uploaded but queries unavailable")

    # Create tabs for different functionality
    tab1, tab2 = st.tabs(["📄 Upload Documents", "💬 Ask Questions"])

    with tab1:
        # Render upload component with RAG components
        upload_component = PDFUploadComponent(
            embedder=embedder,
            vector_store=vector_store,
        )
        upload_component.render()

    with tab2:
        # Render query interface
        render_query_interface(query_engine)


if __name__ == "__main__":
    main()
