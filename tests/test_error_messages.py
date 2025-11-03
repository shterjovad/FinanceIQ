"""Verify error messages match functional spec.

These tests ensure that all error messages displayed to users match
the exact wording specified in the functional specification document.

Reference: context/spec/001-pdf-upload-text-extraction/functional-spec.md
"""

from src.pdf_processor.exceptions import (
    CorruptedPDFError,
    FileSizeExceededError,
    InvalidFileTypeError,
    NoTextContentError,
    PasswordProtectedPDFError,
)


def test_file_size_exceeded_error_message():
    """Test that file size error matches functional spec."""
    error = FileSizeExceededError(file_size_mb=60, max_size_mb=50)
    expected = "File size exceeds 50MB limit. Please upload a smaller document."
    assert error.message == expected


def test_invalid_file_type_error_message():
    """Test that invalid file type error matches functional spec."""
    error = InvalidFileTypeError(file_type=".docx")
    expected = "Only PDF files are supported. Please upload a .pdf file."
    assert error.message == expected


def test_password_protected_error_message():
    """Test that password protected error matches functional spec."""
    error = PasswordProtectedPDFError()
    expected = "This PDF is password-protected. Please upload an unprotected version."
    assert error.message == expected


def test_corrupted_pdf_error_message():
    """Test that corrupted PDF error matches functional spec."""
    error = CorruptedPDFError()
    expected = (
        "This PDF file appears to be corrupted and cannot be processed. "
        "Please check the file and try again."
    )
    assert error.message == expected


def test_no_text_content_error_message():
    """Test that no text content error matches functional spec."""
    error = NoTextContentError()
    expected = (
        "Unable to extract text from this PDF. "
        "Please ensure it contains selectable text (not scanned images)."
    )
    assert error.message == expected
