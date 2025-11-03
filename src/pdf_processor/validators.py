"""PDF file validation logic."""

import logging
from io import BytesIO

from pypdf import PdfReader

from src.pdf_processor.exceptions import (
    CorruptedPDFError,
    FileSizeExceededError,
    InvalidFileTypeError,
    PasswordProtectedPDFError,
)
from src.pdf_processor.models import (
    FileValidationResult,
    FileValidationStatus,
    UploadedFile,
)

logger = logging.getLogger(__name__)


class PDFValidator:
    """Validates PDF files for size, type, and structure."""

    def __init__(self, max_size_mb: int, allowed_mime_types: list[str]):
        """Initialize the validator.

        Args:
            max_size_mb: Maximum allowed file size in megabytes
            allowed_mime_types: List of allowed MIME types
        """
        self.max_size_mb = max_size_mb
        self.allowed_mime_types = allowed_mime_types
        logger.debug(f"PDFValidator initialized with max_size={max_size_mb}MB")

    def validate_file(self, file: UploadedFile) -> FileValidationResult:
        """Validate an uploaded file.

        Args:
            file: The uploaded file to validate

        Returns:
            FileValidationResult with validation status and any error messages
        """
        logger.info(f"Validating file: {file.name} ({file.size_mb}MB)")

        try:
            # Step 1: Validate file size
            self._validate_size(file)

            # Step 2: Validate file type
            self._validate_type(file)

            # Step 3: Validate PDF structure
            self._validate_pdf_structure(file)

            # All validations passed
            logger.info(f"File validation successful: {file.name}")
            return FileValidationResult(
                status=FileValidationStatus.VALID,
                is_valid=True,
                error_message=None,
            )

        except FileSizeExceededError as e:
            logger.warning(f"File size validation failed: {e.message}")
            return FileValidationResult(
                status=FileValidationStatus.INVALID_SIZE,
                is_valid=False,
                error_message=e.message,
            )

        except InvalidFileTypeError as e:
            logger.warning(f"File type validation failed: {e.message}")
            return FileValidationResult(
                status=FileValidationStatus.INVALID_TYPE,
                is_valid=False,
                error_message=e.message,
            )

        except PasswordProtectedPDFError as e:
            logger.warning(f"Password-protected PDF detected: {file.name}")
            return FileValidationResult(
                status=FileValidationStatus.PASSWORD_PROTECTED,
                is_valid=False,
                error_message=e.message,
            )

        except CorruptedPDFError as e:
            logger.error(f"Corrupted PDF detected: {file.name}")
            return FileValidationResult(
                status=FileValidationStatus.CORRUPTED,
                is_valid=False,
                error_message=e.message,
            )

        except Exception as e:
            # Catch any unexpected errors
            logger.error(f"Unexpected error during validation: {str(e)}", exc_info=True)
            return FileValidationResult(
                status=FileValidationStatus.CORRUPTED,
                is_valid=False,
                error_message=f"Unexpected error: {str(e)}",
            )

    def _validate_size(self, file: UploadedFile) -> None:
        """Validate file size.

        Args:
            file: The uploaded file to validate

        Raises:
            FileSizeExceededError: If file size exceeds maximum
        """
        if file.size_mb > self.max_size_mb:
            raise FileSizeExceededError(file_size_mb=file.size_mb, max_size_mb=self.max_size_mb)

    def _validate_type(self, file: UploadedFile) -> None:
        """Validate file type using extension and MIME type.

        Args:
            file: The uploaded file to validate

        Raises:
            InvalidFileTypeError: If file type is not allowed
        """
        # Check extension
        if file.extension != "pdf":
            raise InvalidFileTypeError(file_type=f".{file.extension}")

        # Check MIME type
        if file.mime_type not in self.allowed_mime_types:
            raise InvalidFileTypeError(file_type=file.mime_type)

    def _validate_pdf_structure(self, file: UploadedFile) -> None:
        """Validate PDF structure and check for encryption.

        Args:
            file: The uploaded file to validate

        Raises:
            PasswordProtectedPDFError: If PDF is password-protected
            CorruptedPDFError: If PDF is corrupted or cannot be read
        """
        try:
            # Attempt to read PDF
            pdf_reader = PdfReader(BytesIO(file.content))

            # Check if encrypted
            if pdf_reader.is_encrypted:
                raise PasswordProtectedPDFError()

            # Try to access metadata to verify structure
            _ = pdf_reader.metadata

            # Try to access first page if available
            if len(pdf_reader.pages) > 0:
                _ = pdf_reader.pages[0]

            logger.debug(f"PDF structure validation passed: {len(pdf_reader.pages)} pages")

        except PasswordProtectedPDFError:
            # Re-raise password error as-is
            raise

        except Exception as e:
            # Any other error indicates corrupted PDF
            logger.error(f"PDF structure validation failed: {str(e)}")
            raise CorruptedPDFError(details=str(e)) from e
