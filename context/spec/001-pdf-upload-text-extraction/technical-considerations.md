# Technical Specification: PDF Upload & Text Extraction

- **Functional Specification:** `context/spec/001-pdf-upload-text-extraction/functional-spec.md`
- **Status:** Draft
- **Author(s):** Development Team

---

## 1. High-Level Technical Approach

This feature implements a **layered service architecture** for PDF document processing:

1. **Streamlit UI Layer** - Provides file upload interface with multi-file support and real-time progress feedback
2. **Service Orchestration Layer** - Coordinates the validation → extraction → storage pipeline
3. **Validation Layer** - Performs file size, type, and PDF structure validation
4. **Extraction Layer** - Extracts text content and metadata using pypdf
5. **Storage Layer** - Manages local filesystem storage with date-based organization

All data flows through **Pydantic models** for type safety and validation. Custom domain exceptions provide clear, user-friendly error messages. The architecture follows dependency injection principles for testability.

**Affected Systems:** New implementation - no existing systems affected.

---

## 2. Proposed Solution & Implementation Plan

### 2.1 Project Structure

```
FinanceIQ/
├── src/
│   ├── __init__.py
│   ├── pdf_processor/
│   │   ├── __init__.py              # Package init with logging setup
│   │   ├── models.py                # Pydantic data models
│   │   ├── validators.py            # File validation logic
│   │   ├── extractors.py            # PDF text extraction
│   │   ├── storage.py               # File storage management
│   │   ├── exceptions.py            # Custom domain exceptions
│   │   └── service.py               # Orchestration service
│   ├── ui/
│   │   ├── __init__.py
│   │   └── components/
│   │       ├── __init__.py
│   │       └── upload.py            # Streamlit upload component
│   └── config/
│       ├── __init__.py
│       └── settings.py              # Pydantic Settings for configuration
├── data/
│   └── uploads/                     # Stored PDF files (YYYY/MM/DD structure)
├── logs/                            # Application logs
├── .env.example                     # Environment variable template
├── .env                             # Local environment variables (gitignored)
├── pyproject.toml                   # uv project configuration
├── ruff.toml                        # Ruff configuration
└── README.md
```

### 2.2 Data Models (Pydantic)

**File: `src/pdf_processor/models.py`**

All data structures use Pydantic for validation and type safety:

```python
class UploadedFile(BaseModel):
    """Represents an uploaded file before processing."""
    filename: str
    content: bytes
    size_bytes: int
    mime_type: str

    @property
    def size_mb(self) -> float: ...

class FileValidationResult(BaseModel):
    """Result of file validation."""
    status: FileValidationStatus  # Enum: VALID, INVALID_SIZE, etc.
    is_valid: bool
    error_message: Optional[str]
    filename: str

class DocumentMetadata(BaseModel):
    """Metadata extracted from a PDF document."""
    filename: str
    upload_timestamp: datetime
    page_count: int
    file_size_mb: float
    file_path: Path
    text_length: int

class ExtractedDocument(BaseModel):
    """Fully processed PDF with extracted text."""
    metadata: DocumentMetadata
    text_content: str
    extraction_timestamp: datetime

class ProcessingResult(BaseModel):
    """Result of complete PDF processing pipeline."""
    success: bool
    document: Optional[ExtractedDocument]
    error_message: Optional[str]
    processing_time_seconds: float
```

### 2.3 Custom Exception Hierarchy

**File: `src/pdf_processor/exceptions.py`**

Domain-specific exceptions for clear error handling:

```python
class PDFProcessingError(Exception):
    """Base exception for all PDF processing errors."""

class FileSizeExceededError(PDFProcessingError):
    """File > 50MB limit."""

class InvalidFileTypeError(PDFProcessingError):
    """Non-PDF file uploaded."""

class PasswordProtectedPDFError(PDFProcessingError):
    """PDF is encrypted."""

class CorruptedPDFError(PDFProcessingError):
    """PDF is malformed/corrupted."""

class NoTextContentError(PDFProcessingError):
    """PDF has no extractable text (scanned)."""
```

Each exception includes the filename and user-friendly error message matching the functional spec requirements.

### 2.4 Configuration Management

**File: `src/config/settings.py`**

Pydantic Settings for type-safe configuration:

```python
class Settings(BaseSettings):
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_MIME_TYPES: list[str] = ["application/pdf"]
    UPLOAD_DIR: Path = Path("data/uploads")
    LOG_LEVEL: str = "INFO"
    LOG_DIR: Path = Path("logs")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )
```

Configuration loaded from `.env` file with sensible defaults.

### 2.5 Validation Layer

**File: `src/pdf_processor/validators.py`**

```python
class PDFValidator:
    """Validates PDF files before processing."""

    def validate_file(self, file: UploadedFile) -> FileValidationResult:
        """
        Perform complete validation pipeline.
        Steps: size check → type check → PDF structure check
        """
```

**Validation Steps:**
1. **Size validation**: Check `file.size_mb <= MAX_FILE_SIZE_MB`
2. **Type validation**: Check extension is `.pdf` and MIME type is `application/pdf`
3. **PDF structure validation**:
   - Attempt to open with pypdf's `PdfReader`
   - Check `reader.is_encrypted` for password protection
   - Access first page to validate structure

Returns `FileValidationResult` with status and error message if invalid.

### 2.6 Text Extraction Layer

**File: `src/pdf_processor/extractors.py`**

```python
class PDFTextExtractor:
    """Extracts text content from PDF documents."""

    def extract_text(self, file: UploadedFile) -> str:
        """Extract text from all pages."""

    def extract_metadata(
        self,
        file: UploadedFile,
        file_path: Path,
        text_content: str
    ) -> DocumentMetadata:
        """Extract metadata (page count, size, etc.)."""
```

**Extraction Process:**
1. Open PDF with `PdfReader(BytesIO(file.content))`
2. Iterate through `reader.pages` and call `page.extract_text()`
3. Concatenate all page text with `\n\n` separator
4. Validate text length > 100 characters (configurable minimum)
5. Extract metadata: page count, file size, text length

### 2.7 Storage Layer

**File: `src/pdf_processor/storage.py`**

```python
class FileStorageManager:
    """Manages storage of uploaded PDF files."""

    def save_file(self, file: UploadedFile) -> Path:
        """Save file to disk with date-based organization."""
```

**Storage Strategy:**
- **Directory structure**: `data/uploads/YYYY/MM/DD/filename.pdf`
- **Collision handling**: Append timestamp suffix if filename exists
- **Atomic writes**: Use `Path.write_bytes()` for reliability

Returns the `Path` to the saved file.

### 2.8 Service Orchestration Layer

**File: `src/pdf_processor/service.py`**

```python
class PDFProcessingService:
    """Orchestrates the complete PDF processing pipeline."""

    def __init__(
        self,
        validator: PDFValidator,
        extractor: PDFTextExtractor,
        storage_manager: FileStorageManager
    ):
        """Dependency injection for testability."""

    def process_upload(self, file: UploadedFile) -> ProcessingResult:
        """
        Execute complete processing pipeline:
        1. Validate file
        2. Extract text
        3. Save to filesystem
        4. Extract metadata
        5. Return ProcessingResult
        """
```

**Pipeline Flow:**
1. Call `validator.validate_file()` → return error if invalid
2. Call `extractor.extract_text()` → may raise domain exceptions
3. Call `storage_manager.save_file()` → get file path
4. Call `extractor.extract_metadata()` → get metadata
5. Create `ExtractedDocument` and wrap in `ProcessingResult`
6. Catch all exceptions and convert to failed `ProcessingResult`

**Never propagates exceptions to UI layer** - always returns `ProcessingResult`.

### 2.9 Streamlit UI Component

**File: `src/ui/components/upload.py`**

```python
class PDFUploadComponent:
    """Streamlit component for PDF file upload."""

    def __init__(self, service: PDFProcessingService):
        self.service = service

    def render(self) -> None:
        """Render upload UI in Streamlit."""
```

**UI Flow:**
1. Display `st.file_uploader()` with `accept_multiple_files=True`
2. For each uploaded file:
   - Show progress bar with status text
   - Convert Streamlit `UploadedFile` to our `UploadedFile` model
   - Call `service.process_upload()`
   - Display success metrics (pages, size, characters, time) or error message
3. Success message matches functional spec:
   > "Document uploaded successfully! [filename] is ready for analysis. You can now ask questions about this document."
4. Error messages match functional spec exactly

**Progress Bar States:**
- 0%: "Validating file..."
- 30%: "Extracting text..."
- 100%: "Complete!"

### 2.10 Logging Strategy

**File: `src/pdf_processor/__init__.py`**

Structured logging configuration:

```python
def setup_logging() -> None:
    """Configure application logging."""
    # Console handler: INFO level
    # File handler: DEBUG level (logs/financeiq.log)
    # Format: timestamp - logger - level - message
```

**Logging Levels:**
- **INFO**: Major operations (validation start, extraction complete, file saved)
- **WARNING**: Recoverable issues (page extraction failure, but process continues)
- **ERROR**: Processing failures with context (filename, exception)
- **DEBUG**: Detailed diagnostic info

**Logger Hierarchy:**
- `financeiq.pdf_processor.validators`
- `financeiq.pdf_processor.extractors`
- `financeiq.pdf_processor.storage`
- `financeiq.pdf_processor.service`

### 2.11 Dependencies

**File: `pyproject.toml`**

```toml
[project]
name = "financeiq"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "streamlit>=1.28.0",
    "pypdf>=3.17.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.1.9",
    "mypy>=1.8.0",
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP"]

[tool.mypy]
python_version = "3.10"
strict = true
disallow_untyped_defs = true
```

---

## 3. Impact and Risk Analysis

### 3.1 System Dependencies

**No existing system dependencies** - this is the first feature implementation for FinanceIQ.

**External Dependencies:**
- **pypdf library**: Mature, well-maintained library for PDF processing
- **Streamlit**: Stable framework for ML/AI demos
- **Local filesystem**: Requires write permissions to `data/uploads/` and `logs/`

**Future Integration Points:**
- Extracted text will feed into the chunking pipeline (Phase 1, next spec)
- Metadata will be stored in Qdrant payload (Phase 1, separate spec)

### 3.2 Potential Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Large files causing memory issues** | High | Validate 50MB limit strictly; pypdf streams content efficiently |
| **Malicious file uploads** | Medium | Validate file type and structure; run pypdf in sandboxed process (current Python environment) |
| **Disk space exhaustion** | Low | Monitor `data/uploads/` size; implement cleanup strategy in future version |
| **pypdf extraction failures** | Medium | Comprehensive exception handling; clear error messages guide users to upload better files |
| **Concurrent uploads** | Low | Streamlit is single-user for v1; unique filename generation prevents collisions |
| **Missing extractable text** | Medium | Detect and provide clear error message; suggest non-scanned PDFs |

**Security Considerations:**
- File type validation prevents execution of non-PDF files
- No user authentication in v1, but files are isolated by date/time
- File paths use `Path` for safe path construction (prevents path traversal)

**Performance Considerations:**
- 50MB PDFs may take 10-30 seconds to process
- Progress bar provides user feedback
- Processing is synchronous (acceptable for v1 single-user demo)

---

## 4. Testing Strategy

### 4.1 Unit Testing

**Test Coverage Areas:**
- `validators.py`: All validation scenarios (size, type, encryption, corruption, no text)
- `extractors.py`: Text extraction from valid PDFs, metadata extraction
- `storage.py`: File saving, directory creation, collision handling
- `service.py`: Complete pipeline execution, error propagation

**Test Fixtures Required:**
- `valid_financial.pdf` - Standard 10-K or earnings report
- `oversized.pdf` - File > 50MB
- `password_protected.pdf` - Encrypted PDF
- `corrupted.pdf` - Malformed PDF file
- `scanned_only.pdf` - PDF with only images, no text
- `small_valid.pdf` - Small test PDF for quick tests

**Testing Approach:**
```python
def test_validate_file_size_exceeded():
    validator = PDFValidator(max_size_mb=50)
    file = UploadedFile(
        filename="large.pdf",
        content=b"x" * (51 * 1024 * 1024),  # 51MB
        size_bytes=51 * 1024 * 1024,
        mime_type="application/pdf"
    )
    result = validator.validate_file(file)
    assert not result.is_valid
    assert result.status == FileValidationStatus.INVALID_SIZE
```

### 4.2 Integration Testing

**Test Scenarios:**
1. Upload valid PDF → verify `ProcessingResult.success == True`
2. Upload oversized PDF → verify error message matches spec
3. Upload password-protected PDF → verify specific error
4. Upload multiple PDFs → verify all processed independently
5. Upload corrupted PDF → verify graceful error handling

### 4.3 Manual Testing / Demo

**Test Plan for Demo:**
1. Download real financial documents (Tesla 10-K, Apple earnings report)
2. Upload via Streamlit UI
3. Verify progress bar appears
4. Verify success message and metadata display
5. Test error scenarios with prepared test PDFs
6. Verify files saved to `data/uploads/` with correct structure
7. Check `logs/financeiq.log` for proper logging

---

## 5. Implementation Checklist

- [ ] Initialize project with `uv init` and configure `pyproject.toml`
- [ ] Create project structure (directories and `__init__.py` files)
- [ ] Implement `models.py` (Pydantic models)
- [ ] Implement `exceptions.py` (custom exceptions)
- [ ] Implement `settings.py` (configuration)
- [ ] Implement `validators.py` (file validation)
- [ ] Implement `extractors.py` (text extraction)
- [ ] Implement `storage.py` (file storage)
- [ ] Implement `service.py` (orchestration)
- [ ] Implement `upload.py` (Streamlit UI component)
- [ ] Configure logging in `__init__.py`
- [ ] Create `.env.example` and `.env` files
- [ ] Test with sample PDFs covering all scenarios
- [ ] Run `ruff check` and `ruff format`
- [ ] Run `mypy` for type checking
- [ ] Update README with setup instructions
