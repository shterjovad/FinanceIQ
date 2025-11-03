"""PDF upload UI component."""

import logging

import streamlit as st

from src.config.settings import settings
from src.pdf_processor.models import UploadedFile
from src.pdf_processor.validators import PDFValidator

logger = logging.getLogger(__name__)


class PDFUploadComponent:
    """Handles PDF file upload and validation UI."""

    def __init__(self):
        """Initialize the upload component."""
        # Create validator instance with settings from config
        self.validator = PDFValidator(
            max_size_mb=settings.MAX_FILE_SIZE_MB,
            allowed_mime_types=settings.ALLOWED_MIME_TYPES,
        )
        logger.debug("PDFUploadComponent initialized")

    def render(self) -> None:
        """Render the file upload component and handle validation."""
        st.header("Upload Financial Documents")
        st.write(
            "Upload PDF files containing financial documents such as "
            "10-K reports, earnings reports, or other financial statements."
        )

        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            accept_multiple_files=False,
            help=f"Maximum file size: {settings.MAX_FILE_SIZE_MB}MB",
        )

        if uploaded_file is not None:
            logger.info(f"File uploaded via UI: {uploaded_file.name}")

            # Convert Streamlit UploadedFile to our UploadedFile model
            try:
                file_model = UploadedFile(
                    name=uploaded_file.name,
                    content=uploaded_file.read(),
                    size=uploaded_file.size,
                    mime_type=uploaded_file.type or "application/pdf",
                )

                # Validate the file
                validation_result = self.validator.validate_file(file_model)

                # Display validation result
                if validation_result.is_valid:
                    st.success("✓ File validation successful!")
                    st.info(
                        f"**File:** {file_model.name}  \n"
                        f"**Size:** {file_model.size_mb}MB  \n"
                        f"**Type:** {file_model.mime_type}"
                    )
                else:
                    # Display error message based on validation status
                    st.error(f"✗ Validation failed: {validation_result.error_message}")

            except Exception as e:
                logger.error(f"Error processing uploaded file: {str(e)}", exc_info=True)
                st.error(f"An unexpected error occurred: {str(e)}")
