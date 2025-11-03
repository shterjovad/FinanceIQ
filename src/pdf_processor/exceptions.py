"""Custom exceptions for PDF processing."""


class PDFProcessingError(Exception):
    """Base exception for all PDF processing errors."""

    def __init__(self, message: str):
        """Initialize the exception with a message.

        Args:
            message: Error message describing what went wrong
        """
        self.message = message
        super().__init__(self.message)


class FileSizeExceededError(PDFProcessingError):
    """Raised when uploaded file exceeds maximum allowed size."""

    def __init__(self, file_size_mb: float, max_size_mb: int):
        """Initialize with size details.

        Args:
            file_size_mb: Actual file size in megabytes
            max_size_mb: Maximum allowed file size in megabytes
        """
        self.file_size_mb = file_size_mb
        self.max_size_mb = max_size_mb
        message = (
            f"File size ({file_size_mb:.2f}MB) exceeds maximum allowed size "
            f"({max_size_mb}MB)"
        )
        super().__init__(message)


class InvalidFileTypeError(PDFProcessingError):
    """Raised when uploaded file is not a valid PDF."""

    def __init__(self, file_type: str):
        """Initialize with file type details.

        Args:
            file_type: The detected file type or extension
        """
        self.file_type = file_type
        message = f"Invalid file type: {file_type}. Only PDF files are supported."
        super().__init__(message)


class PasswordProtectedPDFError(PDFProcessingError):
    """Raised when attempting to process a password-protected PDF."""

    def __init__(self):
        """Initialize with standard message."""
        message = "This PDF is password-protected. Please upload an unprotected version."
        super().__init__(message)


class CorruptedPDFError(PDFProcessingError):
    """Raised when PDF file is corrupted or cannot be read."""

    def __init__(self, details: str = ""):
        """Initialize with optional details.

        Args:
            details: Additional details about the corruption
        """
        self.details = details
        message = "The PDF file is corrupted or cannot be read."
        if details:
            message += f" Details: {details}"
        super().__init__(message)


class NoTextContentError(PDFProcessingError):
    """Raised when PDF contains no extractable text."""

    def __init__(self, text_length: int = 0):
        """Initialize with text length details.

        Args:
            text_length: Number of characters extracted (likely 0 or very small)
        """
        self.text_length = text_length
        message = (
            "No text content found in PDF. This may be a scanned document or image-based PDF. "
            "Please upload a text-based PDF."
        )
        super().__init__(message)
