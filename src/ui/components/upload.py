"""PDF upload UI component."""

import logging

import streamlit as st

from src.config.settings import settings
from src.pdf_processor.exceptions import NoTextContentError
from src.pdf_processor.extractors import PDFTextExtractor
from src.pdf_processor.models import UploadedFile
from src.pdf_processor.storage import FileStorageManager
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
        # Create text extractor instance
        self.extractor = PDFTextExtractor(min_text_length=100)
        # Create storage manager instance
        self.storage = FileStorageManager(base_dir=settings.UPLOAD_DIR)
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

                    # Extract text from PDF
                    try:
                        extracted_text = self.extractor.extract_text(file_model)
                        metadata = self.extractor.extract_metadata(file_model, extracted_text)

                        st.success("✓ Text extraction successful!")

                        # Save file to disk
                        try:
                            file_path = self.storage.save_file(file_model)
                            st.success(f"✓ File saved successfully to: `{file_path}`")
                        except IOError as e:
                            st.error(f"✗ Failed to save file: {str(e)}")

                        # Display metrics in columns
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Pages", metadata.page_count)
                        with col2:
                            st.metric("Size", f"{metadata.file_size_mb} MB")
                        with col3:
                            st.metric("Characters", f"{metadata.text_length:,}")

                        # Display text preview in expander
                        with st.expander("📄 Text Preview (first 1000 characters)"):
                            preview_text = extracted_text[:1000]
                            if len(extracted_text) > 1000:
                                preview_text += "..."
                            st.text(preview_text)

                    except NoTextContentError as e:
                        st.error(f"✗ Text extraction failed: {e.message}")

                else:
                    # Display error message based on validation status
                    st.error(f"✗ Validation failed: {validation_result.error_message}")

            except Exception as e:
                logger.error(f"Error processing uploaded file: {str(e)}", exc_info=True)
                st.error(f"An unexpected error occurred: {str(e)}")
