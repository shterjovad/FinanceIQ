# Technical Specification: RAG Query System & Chat Interface

- **Functional Specification:** [functional-spec.md](./functional-spec.md)
- **Status:** Draft
- **Author(s):** Technical Team

---

## 1. High-Level Technical Approach

**Core Strategy:**

We will implement a Retrieval-Augmented Generation (RAG) system that enables users to have natural language conversations with their uploaded financial documents. The implementation follows these key principles:

1. **Create a new `src/rag/` module** parallel to `src/pdf_processor/` to maintain separation of concerns
2. **Use LangChain + LiteLM** for flexible, multi-provider LLM orchestration
3. **Integrate Qdrant** (local Docker instance) as the vector database for semantic search
4. **Implement a `RAGService`** following the same orchestration pattern as `PDFProcessingService`
5. **Add a new `ChatComponent`** using Streamlit's native chat UI components
6. **Hook RAG processing** into the existing document upload flow as an optional step

**Technology Stack:**
- **LangChain**: RAG framework, chain orchestration, embeddings interface
- **LiteLM**: Multi-provider LLM proxy library (OpenAI, Anthropic, Azure, etc.)
- **Qdrant**: Vector database (local Docker container)
- **OpenAI API**: Default provider for embeddings (`text-embedding-3-small`) and LLM (`gpt-4-turbo-preview`)
- **Streamlit**: Chat interface using `st.chat_message` and `st.chat_input`

**Document Processing Flow:**
```
Upload PDF → Extract Text → [Existing Pipeline]
                                    ↓
              Chunk Document → Generate Embeddings → Store in Qdrant
```

**Query Processing Flow:**
```
User Question → Embed Query → Search Qdrant → Retrieve Top-K Chunks
                                                       ↓
                                    Format Context with Citations
                                                       ↓
                                    LLM (via LiteLM) + System Prompt
                                                       ↓
                                    Generate Answer with Sources
```

---

## 2. Proposed Solution & Implementation Plan (The "How")

### **Architecture Changes**

**New Module Structure:**
```
src/rag/
├── __init__.py
├── models.py           # Pydantic models for RAG data structures
├── exceptions.py       # RAG-specific exception hierarchy
├── chunker.py          # Document chunking logic
├── embedder.py         # Embedding generation (OpenAI via LiteLM)
├── vector_store.py     # Qdrant client integration
├── query_engine.py     # Query processing & answer generation
└── service.py          # RAG orchestration service
```

**Integration Points:**
1. **Document Upload Flow**: After successful PDF processing, `PDFUploadComponent` optionally calls `RAGService.process_document()` to index the document
2. **Chat Interface**: New `ChatComponent` in `src/ui/components/chat.py` for conversational queries
3. **Data Flow**: `RAGService` receives `ExtractedDocument` from existing pipeline, processes it, and stores chunks in Qdrant

**Architectural Principles:**
- **Dependency Injection**: Services receive dependencies via constructor (consistent with `PDFProcessingService`)
- **Separation of Concerns**: RAG module is independent of PDF processing
- **Optional Processing**: RAG can be enabled/disabled via configuration
- **Type Safety**: 100% type hint coverage, Pydantic models for all data structures

---

### **Data Model / Storage Changes**

**New Pydantic Models** (`src/rag/models.py`):

```python
class DocumentChunk(BaseModel):
    """A chunk of document text with metadata."""
    content: str
    chunk_id: str  # UUID for unique identification
    document_id: str  # Links back to ExtractedDocument
    chunk_index: int  # Position in document (0-based)
    page_numbers: list[int]  # Pages this chunk spans
    char_start: int  # Character position in original text
    char_end: int
    token_count: int
    embedding: list[float] | None = None  # 1536-dim vector

class QueryResult(BaseModel):
    """Result of a RAG query."""
    success: bool
    answer: str
    sources: list[SourceCitation]
    chunks_retrieved: int
    query_time_seconds: float = Field(ge=0)
    error_message: str | None = None

class SourceCitation(BaseModel):
    """Citation to source document."""
    document_id: str
    page_numbers: list[int]
    relevance_score: float  # Cosine similarity score
    snippet: str  # Actual text from document

class RAGResult(BaseModel):
    """Result of document processing for RAG."""
    success: bool
    document_id: str
    chunks_created: int
    chunks_indexed: int
    processing_time_seconds: float
    error_message: str | None = None

class ChatMessage(BaseModel):
    """A message in the chat conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    sources: list[SourceCitation] = Field(default_factory=list)
```

**Vector Database (Qdrant):**
- **Collection**: `financial_docs` (configurable)
- **Vector Dimension**: 1536 (OpenAI `text-embedding-3-small`)
- **Distance Metric**: Cosine similarity
- **Payload Fields**:
  - `document_id`: Links to original document
  - `chunk_index`: Position in document
  - `page_numbers`: For source citations
  - `content`: Full chunk text
  - `char_start`, `char_end`: Character positions
  - `token_count`: For debugging/optimization

**No Separate Metadata Database**: All metadata is stored in Qdrant's payload field, eliminating the need for a separate database and keeping the architecture simple.

---

### **Configuration Changes**

**Extended Settings** (`src/config/settings.py`):

```python
class Settings(BaseSettings):
    # Existing settings...

    # === RAG SETTINGS ===

    # Document Chunking
    CHUNK_SIZE: int = 1000  # Target tokens per chunk
    CHUNK_OVERLAP: int = 200  # Overlap tokens for context preservation
    CHUNKING_SEPARATORS: list[str] = ["\n\n", "\n", ". ", " "]

    # Vector Database (Qdrant)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "financial_docs"

    # LLM & Embeddings (via LiteLM)
    OPENAI_API_KEY: str  # Required from .env
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    PRIMARY_LLM: str = "gpt-4-turbo-preview"
    FALLBACK_LLM: str = "gpt-3.5-turbo"  # Fallback if rate limited
    LLM_TEMPERATURE: float = 0.0  # Deterministic for consistency
    LLM_MAX_TOKENS: int = 2000

    # Query Processing
    TOP_K_CHUNKS: int = 5  # Number of chunks to retrieve
    MIN_RELEVANCE_SCORE: float = 0.7  # Minimum similarity threshold
```

**Environment Variables Required** (`.env`):
```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (has defaults)
QDRANT_HOST=localhost
QDRANT_PORT=6333
PRIMARY_LLM=gpt-4-turbo-preview
FALLBACK_LLM=gpt-3.5-turbo
```

---

### **Component Breakdown**

#### **1. DocumentChunker** (`src/rag/chunker.py`)

**Purpose**: Split documents into overlapping chunks while preserving context

**Implementation**:
- Uses LangChain's `RecursiveCharacterTextSplitter`
- Respects document structure (paragraphs, sentences, words)
- Tracks page numbers by mapping character positions to pages
- Creates `DocumentChunk` objects with full metadata

**Key Methods**:
```python
class DocumentChunker:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " "],
        )

    def chunk_document(self, document: ExtractedDocument) -> list[DocumentChunk]:
        """Split document into chunks with page tracking."""
        # 1. Split text into chunks
        # 2. Map chunks to page numbers
        # 3. Create DocumentChunk objects
        # 4. Return list of chunks
```

**Error Handling**:
- Raises `ChunkingError` if document is empty
- Handles edge cases (very short documents, single-page docs)

---

#### **2. EmbeddingGenerator** (`src/rag/embedder.py`)

**Purpose**: Generate vector embeddings for text chunks

**Implementation**:
- Uses OpenAI embeddings via LiteLM
- Batch processing (up to 100 chunks per API call for efficiency)
- Automatic retries with exponential backoff
- Returns 1536-dimensional vectors

**Key Methods**:
```python
class EmbeddingGenerator:
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model

    def embed_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """Generate embeddings for chunks (modifies in place)."""
        # 1. Extract text from chunks
        # 2. Batch into groups of 100
        # 3. Call embedding API via LiteLM
        # 4. Assign embeddings to chunks
        # 5. Return chunks with embeddings

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a single query."""
```

**Error Handling**:
- Raises `EmbeddingError` on API failures
- Implements retry logic (3 attempts with exponential backoff)
- Logs batch progress for large documents

---

#### **3. VectorStoreManager** (`src/rag/vector_store.py`)

**Purpose**: Manage Qdrant vector database operations

**Implementation**:
- Wraps Qdrant client for CRUD operations
- Creates collection on initialization if doesn't exist
- Upserts chunks with embeddings and metadata
- Performs semantic search with cosine similarity

**Key Methods**:
```python
class VectorStoreManager:
    def __init__(self, host: str, port: int, collection_name: str):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self._ensure_collection_exists()

    def upsert_chunks(self, chunks: list[DocumentChunk]) -> int:
        """Insert or update chunks in vector store."""
        # Convert chunks to Qdrant points
        # Batch upsert (100 at a time)
        # Return count of inserted chunks

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        min_score: float = 0.7,
    ) -> list[SearchResult]:
        """Search for relevant chunks."""
        # Perform similarity search
        # Filter by minimum score
        # Return results with scores and metadata

    def delete_document(self, document_id: str) -> bool:
        """Remove all chunks for a document."""
```

**Error Handling**:
- Raises `VectorStoreError` if Qdrant is not running
- Provides helpful error message with Docker command
- Graceful degradation if connection fails

---

#### **4. RAGQueryEngine** (`src/rag/query_engine.py`)

**Purpose**: Process queries and generate answers with citations

**Implementation**:
- Embeds user queries
- Retrieves relevant chunks from Qdrant
- Formats context with page numbers
- Calls LLM via LiteLM with structured prompt
- Extracts source citations

**Key Methods**:
```python
class RAGQueryEngine:
    def __init__(
        self,
        vector_store: VectorStoreManager,
        embedder: EmbeddingGenerator,
        llm_model: str,
        fallback_model: str,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.llm_model = llm_model
        self.fallback_model = fallback_model
        self.prompt_template = self._create_prompt_template()

    def query(self, question: str) -> QueryResult:
        """Process query and generate answer."""
        # 1. Embed query
        # 2. Search vector store
        # 3. Check if enough relevant chunks found
        # 4. Format context with citations
        # 5. Call LLM via LiteLM
        # 6. Extract sources
        # 7. Return QueryResult

    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Create system prompt with guardrails."""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a financial analyst assistant.
Answer questions based ONLY on the provided context from financial documents.

IMPORTANT RULES:
- Only use information from the context below
- Always cite sources using [Page X] notation
- If the context doesn't contain enough information, say:
  "I couldn't find relevant information about that in the uploaded documents."
- Do not use external knowledge or make assumptions"""),
            ("user", "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"),
        ])
```

**LiteLM Integration**:
```python
from litellm import completion

response = completion(
    model=self.llm_model,
    messages=[...],
    temperature=0.0,
    max_tokens=2000,
    fallbacks=[self.fallback_model],  # Automatic fallback
)
```

**Error Handling**:
- Raises `QueryError` on processing failures
- Handles "no results found" gracefully
- Implements LiteLM automatic fallbacks

---

#### **5. RAGService** (`src/rag/service.py`)

**Purpose**: Orchestrate the complete RAG pipeline (similar to `PDFProcessingService`)

**Implementation**:
- Coordinates chunking, embedding, and indexing
- Delegates query processing to `RAGQueryEngine`
- Provides cleanup operations for deleted documents
- Returns consistent result objects

**Key Methods**:
```python
class RAGService:
    """Orchestrates RAG pipeline: chunking, embedding, indexing, querying."""

    def __init__(
        self,
        chunker: DocumentChunker,
        embedder: EmbeddingGenerator,
        vector_store: VectorStoreManager,
        query_engine: RAGQueryEngine,
    ):
        self.chunker = chunker
        self.embedder = embedder
        self.vector_store = vector_store
        self.query_engine = query_engine

    def process_document(self, document: ExtractedDocument) -> RAGResult:
        """Process document through RAG pipeline."""
        logger.info(f"Processing document for RAG: {document.filename}")
        start_time = time.time()

        try:
            # Step 1: Chunk document
            chunks = self.chunker.chunk_document(document)
            logger.info(f"Created {len(chunks)} chunks")

            # Step 2: Generate embeddings
            chunks = self.embedder.embed_chunks(chunks)
            logger.info("Generated embeddings")

            # Step 3: Index in vector store
            indexed_count = self.vector_store.upsert_chunks(chunks)
            logger.info(f"Indexed {indexed_count} chunks")

            processing_time = time.time() - start_time

            return RAGResult(
                success=True,
                document_id=document.document_id,
                chunks_created=len(chunks),
                chunks_indexed=indexed_count,
                processing_time_seconds=processing_time,
            )

        except Exception as e:
            logger.error(f"RAG processing failed: {str(e)}", exc_info=True)
            return RAGResult(
                success=False,
                document_id=document.document_id,
                chunks_created=0,
                chunks_indexed=0,
                processing_time_seconds=time.time() - start_time,
                error_message=str(e),
            )

    def query(self, question: str) -> QueryResult:
        """Process a query and generate answer."""
        return self.query_engine.query(question)

    def delete_document(self, document_id: str) -> bool:
        """Remove document from vector store."""
        return self.vector_store.delete_document(document_id)
```

---

#### **6. ChatComponent** (`src/ui/components/chat.py`)

**Purpose**: Provide chat interface for user queries

**Implementation**:
- Uses Streamlit's `st.chat_message` and `st.chat_input`
- Stores conversation history in `st.session_state`
- Displays loading indicators during processing
- Shows sources in expandable sections

**Key Structure**:
```python
class ChatComponent:
    """Handles chat interface and query processing."""

    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service

    def render(self, document_id: str | None = None) -> None:
        """Render chat interface."""
        st.header("Ask Questions About Your Documents")

        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []
            self._show_example_questions()

        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if message.get("sources"):
                    with st.expander("📚 View Sources"):
                        self._display_sources(message["sources"])

        # Query input
        if question := st.chat_input("Ask a question..."):
            # Display user message
            st.chat_message("user").write(question)
            st.session_state.messages.append({"role": "user", "content": question})

            # Process query
            with st.chat_message("assistant"):
                with st.spinner("Searching documents..."):
                    result = self.rag_service.query(question)

                if result.success:
                    st.write(result.answer)
                    if result.sources:
                        with st.expander(f"📚 View {len(result.sources)} Sources"):
                            self._display_sources(result.sources)
                else:
                    st.error(result.error_message)

            # Save to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": result.answer,
                "sources": result.sources,
            })

    def _show_example_questions(self) -> None:
        """Display example questions to guide users."""
        st.info("**Try asking questions like:**")
        st.write("• What were the main revenue drivers this quarter?")
        st.write("• What are the top 3 risks mentioned in the document?")
        st.write("• How did operating expenses change compared to last year?")

    def _display_sources(self, sources: list[SourceCitation]) -> None:
        """Display source citations with page numbers."""
        for i, source in enumerate(sources, 1):
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**Source {i}**")
                    st.text(source.snippet[:200] + "...")
                with col2:
                    st.metric("Pages", ", ".join(map(str, source.page_numbers)))
                    st.metric("Relevance", f"{source.relevance_score:.0%}")
```

---

### **Integration with Existing System**

**Update `PDFUploadComponent`** (`src/ui/components/upload.py`):

```python
class PDFUploadComponent:
    def __init__(self, rag_service: RAGService | None = None):
        # Existing initialization...
        self.rag_service = rag_service

    def render(self) -> None:
        # Existing upload and validation logic...

        if result.success:
            # Existing success display...

            # NEW: Process document for RAG (optional)
            if self.rag_service:
                with st.spinner("Indexing document for queries..."):
                    rag_result = self.rag_service.process_document(result.document)

                if rag_result.success:
                    st.success(
                        f"✓ Document indexed: {rag_result.chunks_created} chunks created "
                        f"in {rag_result.processing_time_seconds:.2f}s. "
                        "You can now ask questions!"
                    )
                    # Store document_id in session state for chat
                    st.session_state.current_document_id = result.document.document_id
                else:
                    st.warning(
                        f"Document uploaded but indexing failed: {rag_result.error_message}"
                    )
```

**Update Main App** (`src/ui/app.py`):

```python
def main() -> None:
    # Initialize services
    upload_service = PDFProcessingService(...)

    # Initialize RAG service (optional - only if Qdrant is running)
    try:
        rag_service = RAGService(
            chunker=DocumentChunker(...),
            embedder=EmbeddingGenerator(...),
            vector_store=VectorStoreManager(...),
            query_engine=RAGQueryEngine(...),
        )
    except Exception as e:
        logger.warning(f"RAG service unavailable: {e}")
        rag_service = None

    # Create tabs
    tab1, tab2 = st.tabs(["📄 Upload Documents", "💬 Ask Questions"])

    with tab1:
        upload_component = PDFUploadComponent(rag_service=rag_service)
        upload_component.render()

    with tab2:
        if rag_service:
            chat_component = ChatComponent(rag_service=rag_service)
            chat_component.render()
        else:
            st.error("RAG service not available. Please start Qdrant.")
```

---

## 3. Impact and Risk Analysis

### **System Dependencies**

**Existing Systems Affected:**
- `PDFProcessingService`: Extended to optionally trigger RAG processing
- `PDFUploadComponent`: Enhanced to show RAG indexing status
- `src/config/settings.py`: Extended with RAG configuration
- `src/ui/app.py`: New tab for chat interface

**New External Dependencies:**
```toml
# Add to pyproject.toml dependencies
langchain = ">=0.1.0"
langchain-openai = ">=0.0.5"
qdrant-client = ">=1.7.0"
litellm = ">=1.17.0"
tiktoken = ">=0.5.0"  # Token counting
```

**Infrastructure Requirements:**
- **Qdrant**: Docker container running on port 6333
  ```bash
  docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
  ```
- **OpenAI API Key**: Required in `.env` file
- **Internet Connection**: For API calls to OpenAI (via LiteLM)

---

### **Potential Risks & Mitigations**

#### **Risk 1: OpenAI API Rate Limits or Unexpected Costs**
**Impact**: Query failures, budget overruns, slow development

**Mitigation**:
- ✅ **LiteLM automatic fallbacks**: Primary (`gpt-4`) → Fallback (`gpt-3.5-turbo`)
- ✅ **Exponential backoff retries**: Handle transient rate limits
- ✅ **Token limits in prompts**: `max_tokens=2000` to control costs
- ✅ **Development optimization**: Use `gpt-3.5-turbo` during development
- ✅ **Request caching**: Cache embeddings for repeated queries (Phase 2)
- ✅ **Batch API calls**: Embed up to 100 chunks per API request

#### **Risk 2: Qdrant Connection Failures**
**Impact**: Cannot index documents or answer queries

**Mitigation**:
- ✅ **Health check on startup**: Warn user if Qdrant not running
- ✅ **Graceful degradation**: Upload still works, RAG optional
- ✅ **Clear error messages**: "Vector database not available. Start with: docker run..."
- ✅ **Retry logic**: Attempt reconnection with delays
- ✅ **Persistent storage**: Use Docker volume to preserve data

#### **Risk 3: Poor Chunking Quality**
**Impact**: Chunks split mid-sentence, loss of context, poor retrieval

**Mitigation**:
- ✅ **Recursive splitting**: Respects paragraphs, sentences, then words
- ✅ **Chunk overlap**: 200 tokens to preserve context across boundaries
- ✅ **Configurable parameters**: Easy to tune `CHUNK_SIZE` and `CHUNK_OVERLAP`
- ✅ **Page number tracking**: Accurate citations help verify quality
- ✅ **Testing**: Validate with real financial documents during development

#### **Risk 4: Irrelevant Chunks Retrieved**
**Impact**: LLM generates "I don't know" too often or incorrect answers

**Mitigation**:
- ✅ **Tunable TOP_K**: Start with 5 chunks, adjust based on testing
- ✅ **Minimum relevance score**: Filter chunks below 0.7 similarity
- ✅ **Query reformulation**: Guide users to ask clearer questions
- ✅ **Embedding quality**: Use high-quality OpenAI embeddings
- ✅ **Future enhancement**: Add reranking in Phase 2

#### **Risk 5: LLM Hallucinations (Generating False Information)**
**Impact**: System provides incorrect answers users might trust

**Mitigation**:
- ✅ **Strong system prompt**: Explicit instructions to only use provided context
- ✅ **Temperature 0.0**: Deterministic, reduces creativity/hallucination
- ✅ **Document-only guardrails**: "Answer ONLY from context"
- ✅ **Clear refusal**: "I couldn't find information..." when uncertain
- ✅ **Source citations**: Users can verify every statement
- ✅ **No external knowledge**: Prompt explicitly forbids using general knowledge

#### **Risk 6: Chat History Lost on Page Refresh**
**Impact**: User loses conversation context

**Mitigation**:
- ✅ **Document limitation**: Clear in UI that history is session-only
- ✅ **Acceptable for demo**: Standard behavior for Streamlit apps
- ✅ **Future enhancement**: Persist to database in Phase 2
- ✅ **Good UX**: Auto-scroll to latest message

#### **Risk 7: Long Document Processing Times**
**Impact**: User waits too long after upload, poor UX

**Mitigation**:
- ✅ **Progress indicators**: Show "Indexing document..." spinner
- ✅ **Batch processing**: Embed 100 chunks at once (faster API calls)
- ✅ **Time tracking**: Log and display processing time
- ✅ **Realistic expectations**: Target <30 seconds for typical 10-K
- ✅ **Async processing**: Phase 2 enhancement for large documents
- ✅ **Chunking optimization**: Efficient recursive splitter

#### **Risk 8: Provider Lock-in (OpenAI-specific)**
**Impact**: Difficult to switch to other LLM providers

**Mitigation**:
- ✅ **LiteLM abstraction**: Provider-agnostic interface
- ✅ **Config-based switching**: Change provider via settings only
- ✅ **No OpenAI-specific code**: All calls through LiteLM
- ✅ **Easy migration**: Switch to Azure, Anthropic, AWS Bedrock via config
- ✅ **Multi-provider fallbacks**: Mix providers in fallback chain

---

## 4. Testing Strategy

### **Unit Tests**

**Document Chunking** (`tests/test_chunker.py`):
- ✅ Verify chunk size and overlap configuration
- ✅ Test page number tracking accuracy
- ✅ Ensure chunks don't split mid-word
- ✅ Handle empty documents gracefully
- ✅ Test with various document structures

**Embedding Generation** (`tests/test_embedder.py`):
- ✅ Verify correct embedding dimensions (1536)
- ✅ Test batch processing (1, 10, 100 chunks)
- ✅ Validate retry logic on API errors
- ✅ Test error handling for rate limits

**Vector Store Operations** (`tests/test_vector_store.py`):
- ✅ Test collection creation
- ✅ Verify chunk upsert operations
- ✅ Test semantic search retrieval
- ✅ Validate document deletion cleanup
- ✅ Test error handling when Qdrant unavailable

**Query Engine** (`tests/test_query_engine.py`):
- ✅ Test query embedding generation
- ✅ Verify context formatting with page citations
- ✅ Test LLM response parsing
- ✅ Validate guardrail behavior (no context → refusal)
- ✅ Test source citation extraction

**LiteLM Integration** (`tests/test_litellm.py`):
- ✅ Test primary model success
- ✅ Test automatic fallback on rate limit
- ✅ Verify error handling when all models fail
- ✅ Test provider switching via config

---

### **Integration Tests**

**End-to-End RAG Pipeline** (`tests/test_rag_service.py`):
- ✅ Full flow: Upload → Chunk → Embed → Index
- ✅ Full query: Question → Retrieve → Generate → Cite
- ✅ Test with real financial document (sample 10-K)
- ✅ Verify source citations match actual pages
- ✅ Test document deletion cleanup

**UI Integration** (`tests/test_chat_component.py`):
- ✅ Test chat message display
- ✅ Verify conversation history persistence in session
- ✅ Test source citation rendering
- ✅ Validate error message display

---

### **Manual Testing**

**Functional Testing with Real Documents**:
1. Use sample 10-K reports from `data/sample/`
2. Test various question types:
   - **Simple**: "What were the main revenue drivers?"
   - **Complex**: "What are the top 3 risks mentioned?"
   - **Multi-part**: "How did Q3 and Q4 revenue compare?"
   - **Out-of-scope**: "What is the stock price?" (should decline)
3. Verify citation accuracy (page numbers match)
4. Verify answer quality (factually correct from document)
5. Test follow-up questions with context

**Performance Testing**:
- ✅ Document indexing time < 30 seconds for typical 10-K
- ✅ Query response time < 30 seconds for typical questions
- ✅ Embedding batch performance (time vs. batch size)
- ✅ Qdrant search latency (<500ms)

**Error Scenario Testing**:
- ✅ Qdrant not running (clear error message)
- ✅ Invalid OpenAI API key (helpful error)
- ✅ Network failure during API call (retry works)
- ✅ Rate limit hit (fallback to GPT-3.5-turbo)
- ✅ No relevant chunks found (graceful message)

**UX Testing**:
- ✅ Chat interface is intuitive
- ✅ Example questions help first-time users
- ✅ Loading indicators appear appropriately
- ✅ Error messages are actionable
- ✅ Source citations are easy to read
- ✅ Conversation flows naturally

---

## 5. Implementation Phases

To manage complexity, we'll implement this feature in 5 slices:

**Slice 1: Core RAG Infrastructure**
- Set up Qdrant Docker container
- Implement `DocumentChunker` with page tracking
- Implement `EmbeddingGenerator` with LiteLM
- Implement `VectorStoreManager`
- Create all Pydantic models
- Add configuration settings

**Slice 2: Query Engine**
- Implement `RAGQueryEngine` with LiteLM
- Create system prompt with guardrails
- Add source citation extraction
- Implement error handling and retries
- Add logging throughout

**Slice 3: Service Integration**
- Create `RAGService` orchestration layer
- Integrate with `PDFProcessingService`
- Add document processing to upload flow
- Implement document deletion cleanup

**Slice 4: Chat Interface**
- Create `ChatComponent` with Streamlit chat UI
- Implement session-based message history
- Add source display in expandable sections
- Integrate with main app navigation
- Add example questions

**Slice 5: Testing & Polish**
- Write unit tests for all components
- Create integration tests
- Test with real financial documents
- Performance optimization
- Documentation updates

---

**Status**: This technical specification is ready for implementation. The architecture is sound, risks are mitigated, and we have a clear testing strategy. Proceed with `/awos:tasks` to break this into detailed implementation tasks.
