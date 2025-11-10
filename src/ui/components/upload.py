"""PDF upload UI component."""

import logging

import streamlit as st

from src.config.settings import settings
from src.pdf_processor.extractors import PDFTextExtractor
from src.pdf_processor.models import UploadedFile
from src.pdf_processor.service import PDFProcessingService
from src.pdf_processor.storage import FileStorageManager
from src.pdf_processor.validators import PDFValidator
from src.rag.chunker import DocumentChunker
from src.rag.service import RAGService

logger = logging.getLogger(__name__)


class PDFUploadComponent:
    """Handles PDF file upload and validation UI."""

    def __init__(
        self,
        rag_service: RAGService | None = None,
    ) -> None:
        """Initialize the upload component.

        Args:
            rag_service: Optional RAG service for document indexing
        """
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

        # Create document chunker for chunk preview
        self.chunker = DocumentChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

        # Store RAG service (optional)
        self.rag_service = rag_service

        logger.debug(f"PDFUploadComponent initialized (RAG enabled: {rag_service is not None})")

    def render(self) -> None:
        """Render the file upload component and handle validation."""
        st.header("Upload Financial Documents")
        st.write(
            "Upload PDF files containing financial documents such as "
            "10-K reports, earnings reports, or other financial statements."
        )

        # File uploader - supports multiple files
        uploaded_files = st.file_uploader(
            "Choose PDF file(s)",
            type=["pdf"],
            accept_multiple_files=True,
            help=f"Maximum file size: {settings.MAX_FILE_SIZE_MB}MB per file",
        )

        if uploaded_files:
            logger.info(f"{len(uploaded_files)} file(s) uploaded via UI")

            # Process each uploaded file
            for uploaded_file in uploaded_files:
                # Use expander for each file's processing
                with st.container():
                    st.markdown(f"### {uploaded_file.name}")

                    # Convert Streamlit UploadedFile to our UploadedFile model
                    try:
                        file_model = UploadedFile(
                            name=uploaded_file.name,
                            content=uploaded_file.read(),
                            size=uploaded_file.size,
                            mime_type=uploaded_file.type or "application/pdf",
                        )

                        # Create progress bar
                        progress_bar = st.progress(0, text="Validating file...")

                        # Update progress: Starting validation
                        progress_bar.progress(10, text="Validating file...")

                        # Process the file through the service
                        # We'll update progress during processing
                        progress_bar.progress(30, text="Extracting text...")

                        result = self.service.process_upload(file_model)

                        # Update progress: Complete
                        progress_bar.progress(100, text="Complete!")

                        # Clear progress bar
                        progress_bar.empty()

                        # Display processing result
                        if result.success:
                            # Success case - display success message per functional spec
                            assert result.document is not None  # Type narrowing for mypy
                            st.success(
                                f"Document uploaded successfully! {result.document.filename} "
                                f"is ready for analysis. You can now ask questions about this document."
                            )

                            # Display metadata in 4 columns
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Pages", result.document.metadata.page_count)
                            with col2:
                                st.metric("Size", f"{result.document.metadata.file_size_mb} MB")
                            with col3:
                                st.metric("Characters", f"{result.document.metadata.text_length:,}")
                            with col4:
                                st.metric(
                                    "Processing Time", f"{result.processing_time_seconds:.2f}s"
                                )

                            # Display text preview in expander
                            with st.expander("📄 Text Preview (first 1000 characters)"):
                                preview_text = result.document.extracted_text[:1000]
                                if len(result.document.extracted_text) > 1000:
                                    preview_text += "..."
                                st.text(preview_text)

                            # Display chunk preview
                            try:
                                chunks = self.chunker.chunk_document(result.document)

                                with st.expander(
                                    f"📑 Document Chunks (showing first 3 of {len(chunks)})"
                                ):
                                    st.write(f"**Total chunks created:** {len(chunks)}")
                                    st.write(
                                        f"**Chunk settings:** {settings.CHUNK_SIZE} tokens, {settings.CHUNK_OVERLAP} overlap"
                                    )
                                    st.markdown("---")

                                    # Show first 3 chunks
                                    for i, chunk in enumerate(chunks[:3]):
                                        st.markdown(f"**Chunk {i + 1}**")

                                        # Display chunk metadata in columns
                                        col1, col2, col3 = st.columns(3)
                                        with col1:
                                            st.metric("Token Count", chunk.token_count)
                                        with col2:
                                            pages_str = ", ".join(map(str, chunk.page_numbers))
                                            st.metric("Pages", pages_str)
                                        with col3:
                                            st.metric("Chunk Index", chunk.chunk_index)

                                        # Display chunk content preview
                                        chunk_preview = chunk.content[:300]
                                        if len(chunk.content) > 300:
                                            chunk_preview += "..."
                                        st.text_area(
                                            "Content Preview",
                                            chunk_preview,
                                            height=150,
                                            key=f"chunk_{result.document.document_id}_{i}",
                                            disabled=True,
                                        )

                                        if i < 2 and i < len(chunks) - 1:
                                            st.markdown("---")
                            except Exception as e:
                                logger.warning(f"Failed to generate chunk preview: {str(e)}")
                                # Don't fail the whole upload if chunking preview fails
                                st.warning("⚠️ Could not generate chunk preview")

                            # Index document if RAG service is available
                            if self.rag_service:
                                with st.spinner("Indexing document for search..."):
                                    try:
                                        # Process document through RAG service
                                        rag_result = self.rag_service.process_document(
                                            result.document
                                        )

                                        if rag_result.success:
                                            # Show success message
                                            st.success(
                                                f"✓ Indexed {rag_result.chunks_indexed} chunks in "
                                                f"{rag_result.processing_time_seconds:.2f}s. "
                                                f"You can now ask questions!"
                                            )

                                            # Store document ID in session state for chat reference
                                            st.session_state.current_document_id = (
                                                rag_result.document_id
                                            )

                                            logger.info(
                                                f"Successfully indexed document {rag_result.document_id}: "
                                                f"{rag_result.chunks_indexed} chunks"
                                            )
                                        else:
                                            # Indexing failed
                                            st.warning(
                                                f"⚠️ Document uploaded but indexing failed: {rag_result.error_message}\n\n"
                                                "You can still view the document but cannot ask questions."
                                            )
                                            logger.warning(
                                                f"Document indexing failed: {rag_result.error_message}"
                                            )

                                    except Exception as e:
                                        logger.error(
                                            f"Unexpected error during indexing: {str(e)}",
                                            exc_info=True,
                                        )
                                        st.warning(
                                            f"⚠️ Document uploaded but indexing failed: {str(e)}\n\n"
                                            "You can still view the document but cannot ask questions."
                                        )

                        else:
                            # Failure case - display error message
                            st.error(f"✗ {result.error_message}")

                        # Add separator between files
                        st.markdown("---")

                    except Exception as e:
                        logger.error(f"Error processing uploaded file: {str(e)}", exc_info=True)
                        st.error(f"An unexpected error occurred: {str(e)}")
                        st.markdown("---")
