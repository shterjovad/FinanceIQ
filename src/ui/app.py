"""FinanceIQ - Financial Document Analysis Application.

This is the main entry point for the Streamlit web application.
"""

import streamlit as st

from src.pdf_processor.logging_config import setup_logging
from src.ui.components.upload import PDFUploadComponent

# Initialize logging
setup_logging()


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

    # Render upload component
    upload_component = PDFUploadComponent()
    upload_component.render()


if __name__ == "__main__":
    main()
