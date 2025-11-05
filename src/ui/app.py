"""FinanceIQ - Financial Document Analysis Application.

This is the main entry point for the Streamlit web application.
"""

import logging

import streamlit as st
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from src.config.settings import settings
from src.pdf_processor.logging_config import setup_logging
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


def render_chat_placeholder() -> None:
    """Render placeholder content for the Ask Questions tab."""
    st.header("RAG Query System - Coming Soon!")

    # Display Qdrant connection status
    st.subheader("System Status")
    is_connected = check_qdrant_connection()

    if is_connected:
        st.success(
            f"✓ Connected to Qdrant vector database at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}"
        )
    else:
        st.warning(
            f"⚠ Cannot connect to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}. "
            "Please ensure Qdrant is running:\n\n"
            "```bash\n"
            "docker compose up -d\n"
            "```"
        )

    # Display information about what's coming
    st.markdown("---")
    st.info(
        "🚀 **What's Coming:**\n\n"
        "This tab will allow you to ask natural language questions about your uploaded financial documents. "
        "The RAG (Retrieval-Augmented Generation) system will:\n\n"
        "- Search through your document collection using semantic similarity\n"
        "- Retrieve the most relevant passages to answer your question\n"
        "- Generate accurate, context-aware answers using GPT-4\n"
        "- Cite specific sources from your documents"
    )

    # Example questions section
    st.subheader("Example Questions You'll Be Able to Ask")
    st.markdown(
        "- What was the company's revenue growth in the last quarter?\n"
        "- What are the main risk factors mentioned in the 10-K?\n"
        "- How much did R&D spending increase year-over-year?\n"
        "- What were the key highlights from the earnings call?\n"
        "- What is the company's cash position and liquidity?"
    )

    # Technical details in expander
    with st.expander("🔧 Technical Details"):
        st.markdown(
            f"**Vector Database:** Qdrant ({settings.QDRANT_HOST}:{settings.QDRANT_PORT})\n\n"
            f"**Embedding Model:** {settings.EMBEDDING_MODEL}\n\n"
            f"**LLM Model:** {settings.PRIMARY_LLM}\n\n"
            f"**Chunk Size:** {settings.CHUNK_SIZE} tokens\n\n"
            f"**Retrieval:** Top {settings.TOP_K_CHUNKS} chunks with minimum relevance {settings.MIN_RELEVANCE_SCORE}"
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

    # Create tabs for different functionality
    tab1, tab2 = st.tabs(["📄 Upload Documents", "💬 Ask Questions"])

    with tab1:
        # Render upload component
        upload_component = PDFUploadComponent()
        upload_component.render()

    with tab2:
        # Render chat placeholder
        render_chat_placeholder()


if __name__ == "__main__":
    main()
