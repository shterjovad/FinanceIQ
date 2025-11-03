"""PDF upload UI component."""

import logging

import streamlit as st

from src.config.settings import settings
from src.pdf_processor.extractors import PDFTextExtractor
from src.pdf_processor.models import UploadedFile
from src.pdf_processor.service import PDFProcessingService
from src.pdf_processor.storage import FileStorageManager
from src.pdf_processor.validators import PDFValidator

logger = logging.getLogger(__name__)


class PDFUploadComponent:
    """Handles PDF file upload and validation UI."""

    def __init__(self):
        """Initialize the upload component."""
        # Create validator instance with settings from config
        validator = PDFValidator(
            max_size_mb=settings.MAX_FILE_SIZE_MB,
            allowed_mime_types=settings.ALLOWED_MIME_TYPES,
        )
        # Create text extractor instance
        extractor = PDFTextExtractor(min_text_length=100)
        # Create storage manager instance
        storage_manager = FileStorageManager(base_dir=settings.UPLOAD_DIR)

        # Create processing service with dependency injection
        self.service = PDFProcessingService(
            validator=validator,
            extractor=extractor,
            storage_manager=storage_manager,
        )
        logger.debug("PDFUploadComponent initialized with PDFProcessingService")

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

                # Process the file through the service
                result = self.service.process_upload(file_model)

                # Display processing result
                if result.success:
                    # Success case - display success message and metadata
                    st.success(
                        f"✓ Document processed successfully! "
                        f"({result.processing_time_seconds:.2f}s)"
                    )
                    st.success(f"✓ File saved to: `{result.document.file_path}`")

                    # Display metadata in 4 columns
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Pages", result.document.metadata.page_count)
                    with col2:
                        st.metric("Size", f"{result.document.metadata.file_size_mb} MB")
                    with col3:
                        st.metric("Characters", f"{result.document.metadata.text_length:,}")
                    with col4:
                        st.metric("Processing Time", f"{result.processing_time_seconds:.2f}s")

                    # Display text preview in expander
                    with st.expander("📄 Text Preview (first 1000 characters)"):
                        preview_text = result.document.extracted_text[:1000]
                        if len(result.document.extracted_text) > 1000:
                            preview_text += "..."
                        st.text(preview_text)

                else:
                    # Failure case - display error message
                    st.error(f"✗ Processing failed: {result.error_message}")

            except Exception as e:
                logger.error(f"Error processing uploaded file: {str(e)}", exc_info=True)
                st.error(f"An unexpected error occurred: {str(e)}")
