"""PDF processing service orchestration layer."""

import logging
import time

from src.pdf_processor.exceptions import NoTextContentError
from src.pdf_processor.extractors import PDFTextExtractor
from src.pdf_processor.models import (
    ExtractedDocument,
    ProcessingResult,
    UploadedFile,
)
from src.pdf_processor.storage import FileStorageManager
from src.pdf_processor.validators import PDFValidator

logger = logging.getLogger(__name__)


class PDFProcessingService:
    """Orchestrates PDF processing pipeline: validation, extraction, and storage."""

    def __init__(
        self,
        validator: PDFValidator,
        extractor: PDFTextExtractor,
        storage_manager: FileStorageManager,
    ):
        """Initialize the PDF processing service.

        Args:
            validator: PDF validator instance for file validation
            extractor: PDF text extractor for text extraction and metadata
            storage_manager: File storage manager for saving files to disk
        """
        self.validator = validator
        self.extractor = extractor
        self.storage_manager = storage_manager
        logger.debug("PDFProcessingService initialized")

    def process_upload(self, file: UploadedFile) -> ProcessingResult:
        """Process an uploaded PDF file through the complete pipeline.

        This method orchestrates the entire processing workflow:
        1. Validate file (size, type, structure)
        2. Extract text content
        3. Save file to disk
        4. Extract metadata
        5. Return processing result

        Args:
            file: The uploaded PDF file to process

        Returns:
            ProcessingResult containing either success (with ExtractedDocument)
            or failure (with error message)
        """
        logger.info(f"Starting processing pipeline for file: {file.name}")
        start_time = time.time()

        try:
            # Step 1: Validate file
            logger.debug("Step 1: Validating file")
            validation_result = self.validator.validate_file(file)

            if not validation_result.is_valid:
                processing_time = time.time() - start_time
                logger.warning(
                    f"File validation failed for {file.name}: {validation_result.error_message}"
                )
                return ProcessingResult(
                    success=False,
                    document=None,
                    error_message=validation_result.error_message,
                    processing_time_seconds=processing_time,
                )

            logger.info(f"File validation passed: {file.name}")

            # Step 2: Extract text
            logger.debug("Step 2: Extracting text from PDF")
            try:
                extracted_text = self.extractor.extract_text(file)
                logger.info(f"Text extraction successful: {len(extracted_text)} characters")
            except NoTextContentError as e:
                processing_time = time.time() - start_time
                logger.error(f"Text extraction failed: {e.message}")
                return ProcessingResult(
                    success=False,
                    document=None,
                    error_message=e.message,
                    processing_time_seconds=processing_time,
                )
            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"Unexpected error during text extraction: {str(e)}", exc_info=True)
                return ProcessingResult(
                    success=False,
                    document=None,
                    error_message=f"Text extraction failed: {str(e)}",
                    processing_time_seconds=processing_time,
                )

            # Step 3: Save file to disk
            logger.debug("Step 3: Saving file to disk")
            try:
                file_path = self.storage_manager.save_file(file)
                logger.info(f"File saved successfully: {file_path}")
            except OSError as e:
                processing_time = time.time() - start_time
                logger.error(f"Failed to save file: {str(e)}")
                return ProcessingResult(
                    success=False,
                    document=None,
                    error_message=f"Failed to save file: {str(e)}",
                    processing_time_seconds=processing_time,
                )
            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"Unexpected error saving file: {str(e)}", exc_info=True)
                return ProcessingResult(
                    success=False,
                    document=None,
                    error_message=f"Failed to save file: {str(e)}",
                    processing_time_seconds=processing_time,
                )

            # Step 4: Extract metadata
            logger.debug("Step 4: Extracting metadata")
            try:
                metadata = self.extractor.extract_metadata(file, extracted_text)
                logger.info(f"Metadata extracted: {metadata.page_count} pages")
            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"Failed to extract metadata: {str(e)}", exc_info=True)
                return ProcessingResult(
                    success=False,
                    document=None,
                    error_message=f"Failed to extract metadata: {str(e)}",
                    processing_time_seconds=processing_time,
                )

            # Step 5: Create ExtractedDocument and return success
            logger.debug("Step 5: Creating ExtractedDocument")
            document = ExtractedDocument(
                filename=file.name,
                file_path=file_path,
                extracted_text=extracted_text,
                metadata=metadata,
            )

            processing_time = time.time() - start_time
            logger.info(
                f"Processing completed successfully for {file.name} "
                f"in {processing_time:.2f} seconds"
            )

            return ProcessingResult(
                success=True,
                document=document,
                error_message=None,
                processing_time_seconds=processing_time,
            )

        except Exception as e:
            # Catch-all for any unexpected errors
            processing_time = time.time() - start_time
            logger.error(
                f"Unexpected error in processing pipeline for {file.name}: {str(e)}",
                exc_info=True,
            )
            return ProcessingResult(
                success=False,
                document=None,
                error_message=f"Unexpected processing error: {str(e)}",
                processing_time_seconds=processing_time,
            )
