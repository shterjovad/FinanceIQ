# FinanceIQ

A multi-agent RAG (Retrieval-Augmented Generation) system for intelligent financial document analysis. FinanceIQ processes and extracts insights from PDF documents such as 10-K reports, earnings reports, and other financial statements.

## Features

### Current Features (Phase 1: Document Processing)
- **PDF Upload & Validation**
  - Multi-file upload support with drag-and-drop interface
  - File size validation (configurable max: 50MB)
  - File type validation (PDF only)
  - Password-protected PDF detection
  - Corrupted PDF detection

- **Text Extraction**
  - Automated text extraction from native PDFs
  - Page count and character count metrics
  - Scanned PDF detection with user-friendly error messages
  - Processing time tracking

- **Document Storage**
  - Date-based file organization (YYYY/MM/DD)
  - Automatic filename collision handling
  - Metadata preservation (filename, page count, file size, extraction date)

- **User Interface**
  - Real-time progress indicators
  - Interactive text preview (first 1000 characters)
  - Comprehensive error messaging aligned with functional specs
  - Responsive design with Streamlit

- **Code Quality**
  - 100% type hint coverage with mypy strict mode
  - Comprehensive error handling with custom exception hierarchy
  - Structured logging
  - Pytest test suite
  - Ruff linting and formatting (100% compliant)

### Roadmap (Future Phases)
- **Phase 2**: Multi-Agent Intelligence & Query Decomposition
  - LangGraph-based agent orchestration
  - Query analysis and decomposition
  - Multi-step reasoning system

- **Phase 3**: RAG Core & Vector Database
  - Document chunking with semantic awareness
  - Vector embeddings with Qdrant
  - Semantic search and retrieval

## Requirements

- Python 3.10+ (developed and tested on Python 3.12)
- [uv](https://github.com/astral-sh/uv) package manager

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/shterjovad/FinanceIQ.git
   cd FinanceIQ
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Create `.env` file (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration if needed
   ```

4. **Run the application:**
   ```bash
   ./run.sh
   ```

   Or manually:
   ```bash
   PYTHONPATH=. uv run streamlit run src/ui/app.py
   ```

5. **Open your browser:**
   Navigate to `http://localhost:8501`

## Project Structure

```
FinanceIQ/
├── src/
│   ├── config/
│   │   └── settings.py           # Pydantic Settings configuration
│   ├── pdf_processor/
│   │   ├── exceptions.py         # Custom exception hierarchy
│   │   ├── extractors.py         # PDF text extraction logic
│   │   ├── logging_config.py     # Logging configuration
│   │   ├── models.py             # Pydantic data models
│   │   ├── service.py            # PDF processing service orchestration
│   │   ├── storage.py            # File storage management
│   │   └── validators.py         # File validation logic
│   └── ui/
│       ├── app.py                # Main Streamlit application
│       └── components/
│           └── upload.py         # PDF upload component
├── tests/
│   └── test_error_messages.py   # Error message validation tests
├── data/
│   └── uploads/                  # Uploaded PDF files (gitignored)
├── logs/                         # Application logs (gitignored)
├── context/                      # Project documentation and specs
│   ├── product/                  # Product docs (roadmap, architecture)
│   └── spec/                     # Technical specifications
├── .env                          # Environment variables (gitignored)
├── .env.example                  # Example environment configuration
├── pyproject.toml                # Project dependencies and tool config
└── run.sh                        # Application startup script
```

## Configuration

Configuration is managed via environment variables in `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_FILE_SIZE_MB` | Maximum file size for uploads (MB) | 50 |
| `ALLOWED_MIME_TYPES` | Allowed MIME types | application/pdf |
| `UPLOAD_DIR` | Directory for uploaded files | data/uploads |
| `LOG_DIR` | Directory for log files | logs |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |

## Development

### Technology Stack

- **Frontend**: [Streamlit](https://streamlit.io/) - Fast web UI framework for ML/AI applications
- **PDF Processing**: [pypdf](https://pypdf.readthedocs.io/) - PDF text extraction library
- **Data Validation**: [Pydantic](https://docs.pydantic.dev/) - Runtime type checking and data validation
- **Package Management**: [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- **Type Checking**: [mypy](http://mypy-lang.org/) - Static type checker (strict mode enabled)
- **Linting/Formatting**: [ruff](https://docs.astral.sh/ruff/) - Fast Python linter and formatter
- **Testing**: [pytest](https://docs.pytest.org/) - Testing framework

### Development Setup

1. **Install dev dependencies:**
   ```bash
   uv sync --extra dev
   ```

2. **Run linting:**
   ```bash
   uv run ruff check src/
   ```

3. **Run formatting:**
   ```bash
   uv run ruff format src/ tests/
   ```

4. **Run type checking:**
   ```bash
   uv run mypy src/
   ```

5. **Run tests:**
   ```bash
   uv run pytest tests/ -v
   ```

6. **Run all quality checks:**
   ```bash
   uv run ruff check src/ && uv run ruff format --check src/ tests/ && uv run mypy src/ && uv run pytest tests/
   ```

### Architecture

**Layered Architecture:**
1. **Presentation Layer** (`src/ui/`): Streamlit-based user interface
2. **Service Layer** (`src/pdf_processor/service.py`): Orchestrates business logic
3. **Business Logic Layer** (`src/pdf_processor/`): PDF processing, validation, extraction
4. **Data Layer** (`src/pdf_processor/storage.py`): File system storage management
5. **Configuration Layer** (`src/config/`): Application settings and environment variables

**Key Design Patterns:**
- **Dependency Injection**: Services receive dependencies via constructor for loose coupling
- **Exception Hierarchy**: Custom exceptions for clear, type-safe error handling
- **Type Safety**: Full type hint coverage with Pydantic models and mypy strict mode
- **Service Orchestration**: Centralized processing pipeline in `PDFProcessingService`

## Error Handling

FinanceIQ provides comprehensive error handling with user-friendly messages:

- **File Size Exceeded**: "File size exceeds 50MB limit. Please upload a smaller document."
- **Invalid File Type**: "Only PDF files are supported. Please upload a .pdf file."
- **Password Protected**: "This PDF is password-protected. Please upload an unprotected version."
- **Corrupted PDF**: "This PDF file appears to be corrupted and cannot be processed. Please check the file and try again."
- **No Text Content**: "Unable to extract text from this PDF. Please ensure it contains selectable text (not scanned images)."

All error messages are validated against the functional specification via automated tests.

## Testing

The project includes a test suite that validates:
- Error message accuracy against functional specifications
- Type safety with mypy strict mode
- Code quality with ruff linting

Run tests with:
```bash
uv run pytest tests/ -v
```

## License

This project is part of a portfolio demonstration.

## Contributing

This is a portfolio project. For questions or suggestions, please open an issue.

---

**Built with modern Python development practices** • Type-safe • Well-tested • Production-ready code quality
