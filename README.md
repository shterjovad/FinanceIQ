# FinanceIQ

A production-ready, multi-agent RAG (Retrieval-Augmented Generation) system for intelligent financial document analysis. FinanceIQ processes and extracts insights from PDF documents such as 10-K reports, earnings reports, and other financial statements with browser-based session isolation for secure multi-user deployment.

**🚀 [Live Demo](https://financeiq-production.up.railway.app)** - Try it out with your own documents!

## Features

### Current Features

#### Document Processing
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

#### RAG (Retrieval-Augmented Generation) System
- **Document Chunking**
  - Semantic-aware text chunking with configurable size and overlap
  - Page number tracking for accurate citations
  - Token counting for context management
  - Preserves document structure across chunks

- **Vector Embeddings & Storage**
  - OpenAI text-embedding-3-small for high-quality embeddings
  - Qdrant vector database for fast similarity search
  - Automatic collection management
  - Batch processing for efficient embedding generation

- **Intelligent Query Engine**
  - GPT-4-turbo for accurate answer generation
  - Automatic fallback to GPT-3.5-turbo for reliability
  - Relevance threshold filtering (configurable)
  - Source citation with page numbers and relevance scores
  - Query guardrails to prevent hallucinations

- **Multi-Agent Query Processing** (Phase 3)
  - **Query Router Agent**: Classifies queries as simple or complex
  - **Query Decomposer Agent**: Breaks complex queries into 2-5 sub-queries
  - **Parallel Executor Agent**: Executes sub-queries concurrently (2.5x speedup)
  - **Answer Synthesis Agent**: Combines results into coherent final answer
  - **LangGraph Orchestration**: State machine-based agent workflow
  - **Reasoning Transparency**: Full visibility into agent decision-making
  - **UI Toggle**: Enable/disable agents on demand in the interface
  - **Performance Optimized**: <20s for complex queries, <5s for simple queries

- **Browser-Session Isolation** (Phase 4)
  - **Per-Tab Document Storage**: Each browser tab maintains isolated documents
  - **UUID-Based Sessions**: Cryptographically random session IDs
  - **Automatic Cleanup**: Session data cleared when tab closes
  - **Zero Data Leakage**: Complete isolation between concurrent users
  - **Qdrant Payload Filtering**: Efficient session-based vector search
  - **Production-Ready**: Suitable for public deployment and portfolio demonstrations

- **Conversational Chat Interface**
  - Full conversation history within session
  - ChatGPT-style interface with message bubbles
  - Real-time "Thinking..." indicators
  - Expandable source citations per answer
  - Agent reasoning step visualization (when multi-agent mode enabled)
  - Runtime agent mode toggle

- **Service Orchestration**
  - Clean RAGService layer coordinating all components
  - Automatic error handling with structured results
  - Performance monitoring and timing metrics
  - Document lifecycle management (index/query/delete)
  - Agent workflow integration with fallback support

#### Code Quality
  - 96% test coverage across all modules
  - 160+ unit tests + 7 integration tests + 6 performance benchmarks
  - 100% type hint coverage with mypy strict mode
  - Comprehensive error handling with custom exception hierarchy
  - Structured logging throughout
  - Ruff linting and formatting (100% compliant)

### Roadmap (Future Phases)
- **Phase 5**: Advanced Multi-Document Features
  - Multi-document comparison and analysis
  - Time-series analysis for financial trends
  - Custom entity extraction for financial metrics
  - Export and reporting capabilities
  - Document similarity detection

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

3. **Start Qdrant vector database:**
   ```bash
   docker compose up -d
   ```

   Verify Qdrant is running at `http://localhost:6333/dashboard`

4. **Create `.env` file with your OpenAI API key:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add:
   ```
   OPENAI_API_KEY=sk-your-api-key-here
   ```

5. **Run the application:**
   ```bash
   ./run.sh
   ```

   Or manually:
   ```bash
   PYTHONPATH=. uv run streamlit run src/ui/app.py
   ```

6. **Open your browser:**
   Navigate to `http://localhost:8501`

7. **Upload and query documents:**
   - Go to "Upload Documents" tab and upload a PDF (e.g., 10-K report)
   - Wait for indexing to complete (~10-30s depending on document size)
   - Go to "Ask Questions" tab and start chatting with your document!

## Project Structure

```
FinanceIQ/
├── src/
│   ├── agents/                   # Multi-agent query processing
│   │   ├── decomposer.py        # Query decomposition agent
│   │   ├── executor.py          # Parallel sub-query executor
│   │   ├── models.py            # Agent state definitions
│   │   ├── router.py            # Query classification agent
│   │   ├── synthesizer.py       # Answer synthesis agent
│   │   └── workflow.py          # LangGraph workflow orchestration
│   ├── config/
│   │   └── settings.py          # Pydantic Settings configuration
│   ├── pdf_processor/
│   │   ├── exceptions.py        # Custom exception hierarchy
│   │   ├── extractors.py        # PDF text extraction logic
│   │   ├── logging_config.py    # Logging configuration
│   │   ├── models.py            # Pydantic data models
│   │   ├── service.py           # PDF processing service orchestration
│   │   ├── storage.py           # File storage management
│   │   └── validators.py        # File validation logic
│   ├── rag/                     # RAG system components
│   │   ├── chunker.py           # Document chunking
│   │   ├── embedder.py          # Embedding generation
│   │   ├── models.py            # RAG data models
│   │   ├── query_engine.py      # RAG query processing
│   │   ├── service.py           # RAG service orchestration
│   │   └── vector_store.py      # Qdrant vector store manager
│   └── ui/
│       ├── app.py               # Main Streamlit application
│       └── components/
│           ├── chat.py          # Conversational chat interface
│           └── upload.py        # PDF upload component
├── tests/
│   ├── agents/                  # Agent unit tests (49 tests)
│   ├── integration/             # Integration tests (7 tests)
│   ├── performance/             # Performance benchmarks (6 tests)
│   ├── pdf_processor/           # PDF processing tests
│   └── rag/                     # RAG system tests
├── data/
│   └── uploads/                 # Uploaded PDF files (gitignored)
├── logs/                        # Application logs (gitignored)
├── scripts/                     # Helper scripts for local development
│   ├── start_qdrant.sh          # Start local Qdrant instance
│   └── verify_qdrant_setup.sh  # Verify Qdrant configuration
├── .streamlit/
│   └── config.toml              # Streamlit production configuration
├── Dockerfile                   # Docker containerization for deployment
├── railway.toml                 # Railway deployment configuration
├── docker-compose.yml           # Local Qdrant setup
├── .env                         # Environment variables (gitignored)
├── .env.example                 # Example environment configuration
├── pyproject.toml               # Project dependencies and tool config
└── run.sh                       # Application startup script
```

## Configuration

Configuration is managed via environment variables in `.env` file.

**Note:** Default values shown are for local development. See production deployment section for cloud configuration.

| Variable | Description | Default (Local) |
|----------|-------------|---------|
| `MAX_FILE_SIZE_MB` | Maximum file size for uploads (MB) | 50 |
| `ALLOWED_MIME_TYPES` | Allowed MIME types | application/pdf |
| `UPLOAD_DIR` | Directory for uploaded files | data/uploads |
| `LOG_DIR` | Directory for log files | logs |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `OPENAI_API_KEY` | OpenAI API key for embeddings and LLM | **Required** |
| `QDRANT_HOST` | Qdrant vector database host | localhost |
| `QDRANT_PORT` | Qdrant vector database port | 6333 |
| `QDRANT_COLLECTION` | Qdrant collection name | financial_docs |
| `QDRANT_API_KEY` | Qdrant Cloud API key (for production) | None |
| `QDRANT_USE_HTTPS` | Use HTTPS for Qdrant connection (Cloud) | false |
| `EMBEDDING_MODEL` | OpenAI embedding model | text-embedding-3-small |
| `PRIMARY_LLM` | Primary LLM for answer generation | gpt-4-turbo-preview |
| `FALLBACK_LLM` | Fallback LLM if primary fails | gpt-3.5-turbo |
| `CHUNK_SIZE` | Document chunk size (tokens) | 1000 |
| `CHUNK_OVERLAP` | Chunk overlap (tokens) | 200 |
| `TOP_K_CHUNKS` | Number of chunks to retrieve per query | 5 |
| `MIN_RELEVANCE_SCORE` | Minimum similarity score (0-1) | 0.3 |
| `USE_AGENTS` | Enable multi-agent query processing | true |
| `AGENT_ROUTER_MODEL` | LLM for query classification | gpt-4-turbo-preview |
| `AGENT_DECOMPOSER_MODEL` | LLM for query decomposition | gpt-4-turbo-preview |
| `AGENT_SYNTHESIZER_MODEL` | LLM for answer synthesis | gpt-4-turbo-preview |
| `MAX_SUB_QUERIES` | Maximum sub-queries for decomposition | 5 |

## Development

### Technology Stack

- **Frontend**: [Streamlit](https://streamlit.io/) - Fast web UI framework for ML/AI applications
- **PDF Processing**: [pypdf](https://pypdf.readthedocs.io/) - PDF text extraction library
- **RAG Components**:
  - [LiteLLM](https://www.litellm.ai/) - Unified LLM API with automatic fallbacks
  - [Qdrant](https://qdrant.tech/) - High-performance vector database
  - [OpenAI](https://openai.com/) - Embeddings (text-embedding-3-small) and LLM (GPT-4-turbo)
  - [LangChain](https://www.langchain.com/) - Document chunking and text processing
  - [LangGraph](https://www.langchain.com/langgraph) - State machine orchestration for multi-agent workflows
  - [tiktoken](https://github.com/openai/tiktoken) - Token counting for OpenAI models
- **Data Validation**: [Pydantic](https://docs.pydantic.dev/) - Runtime type checking and data validation
- **Package Management**: [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- **Type Checking**: [mypy](http://mypy-lang.org/) - Static type checker (strict mode enabled)
- **Linting/Formatting**: [ruff](https://docs.astral.sh/ruff/) - Fast Python linter and formatter
- **Testing**: [pytest](https://docs.pytest.org/) - Testing framework with 96% coverage

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
2. **Service Layer** (`src/rag/service.py`): Orchestrates RAG and agent workflows
3. **Agent Layer** (`src/agents/`): Multi-agent query processing orchestration
4. **Business Logic Layer**:
   - `src/pdf_processor/`: PDF processing, validation, extraction
   - `src/rag/`: Document chunking, embeddings, vector search
5. **Data Layer**: File system storage and Qdrant vector database
6. **Configuration Layer** (`src/config/`): Application settings and environment variables

**Key Design Patterns:**
- **Dependency Injection**: Services receive dependencies via constructor for loose coupling
- **State Machine Pattern**: LangGraph-based agent orchestration with typed state
- **Exception Hierarchy**: Custom exceptions for clear, type-safe error handling
- **Type Safety**: Full type hint coverage with Pydantic models and mypy strict mode
- **Service Orchestration**: Centralized processing pipeline with agent workflow integration
- **Parallel Processing**: ThreadPoolExecutor for concurrent sub-query execution

## Production Deployment

FinanceIQ is production-ready and can be deployed to cloud platforms like Railway, Render, or Fly.io.

### Requirements for Production:
- **Cloud Vector Database**: Qdrant Cloud (free tier available)
- **Container Platform**: Any Docker-compatible hosting (Railway, Render, Fly.io)
- **Environment Variables**: Configure for HTTPS and cloud services

### Key Configuration Changes for Production:
```bash
# Use Qdrant Cloud instead of localhost
QDRANT_HOST=your-cluster.qdrant.io
QDRANT_PORT=6333
QDRANT_API_KEY=your-api-key
QDRANT_USE_HTTPS=true

# Adjust relevance threshold for better results
MIN_RELEVANCE_SCORE=0.3

# Enable multi-agent processing
USE_AGENTS=true
```

### Session Isolation in Production:
- Each browser tab gets a unique UUID-based session
- Documents are isolated per session using Qdrant payload filtering
- Sessions automatically clear when tabs close
- No data leakage between concurrent users
- Suitable for public portfolio demonstrations

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
