"""Pydantic data models for PDF processing."""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class FileValidationStatus(str, Enum):
    """Status of file validation."""

    VALID = "valid"
    INVALID_SIZE = "invalid_size"
    INVALID_TYPE = "invalid_type"
    PASSWORD_PROTECTED = "password_protected"
    CORRUPTED = "corrupted"
    NO_TEXT = "no_text"


class UploadedFile(BaseModel):
    """Model representing an uploaded file."""

    name: str
    content: bytes
    size: int = Field(ge=0, description="File size in bytes")
    mime_type: str

    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        return round(self.size / (1024 * 1024), 2)

    @property
    def extension(self) -> str:
        """Get file extension (lowercase, without dot)."""
        return Path(self.name).suffix.lower().lstrip(".")

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class FileValidationResult(BaseModel):
    """Result of file validation."""

    status: FileValidationStatus
    is_valid: bool
    error_message: str | None = None


class DocumentMetadata(BaseModel):
    """Metadata extracted from a PDF document."""

    page_count: int = Field(gt=0, description="Number of pages in the document")
    file_size_mb: float = Field(gt=0, description="File size in megabytes")
    text_length: int = Field(ge=0, description="Number of characters in extracted text")
    extraction_date: datetime = Field(default_factory=datetime.now)

    @field_validator("page_count")
    @classmethod
    def validate_page_count(cls, v: int) -> int:
        """Validate page count is positive."""
        if v <= 0:
            raise ValueError("Page count must be greater than 0")
        return v

    @field_validator("file_size_mb")
    @classmethod
    def validate_file_size(cls, v: float) -> float:
        """Validate file size is positive."""
        if v <= 0:
            raise ValueError("File size must be greater than 0")
        return round(v, 2)


class ExtractedDocument(BaseModel):
    """Model representing an extracted PDF document."""

    filename: str
    file_path: Path
    extracted_text: str
    metadata: DocumentMetadata

    @property
    def document_id(self) -> str:
        """Generate a unique document ID based on filename and extraction date."""
        timestamp = self.metadata.extraction_date.strftime("%Y%m%d_%H%M%S")
        return f"{Path(self.filename).stem}_{timestamp}"

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class ProcessingResult(BaseModel):
    """Result of PDF processing operation."""

    success: bool
    document: ExtractedDocument | None = None
    error_message: str | None = None
    processing_time_seconds: float = Field(ge=0, description="Time taken to process")

    @field_validator("processing_time_seconds")
    @classmethod
    def round_processing_time(cls, v: float) -> float:
        """Round processing time to 2 decimal places."""
        return round(v, 2)
