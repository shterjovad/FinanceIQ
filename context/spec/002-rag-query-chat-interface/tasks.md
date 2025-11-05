# Task List: RAG Query System & Chat Interface

**Specification**: `context/spec/002-rag-query-chat-interface/`
**Target**: Implement conversational Q&A system for financial documents
**Status**: Ready for Implementation

---

## Vertical Slicing Strategy

Each slice builds on the previous and leaves the application **runnable and testable**. We avoid horizontal splits (e.g., "all database work") and instead create **end-to-end increments** of user-visible value.

---

## Tasks

### Slice 1: Infrastructure Setup & Basic Models
**Goal**: Set up all infrastructure so the app runs without errors and has the foundation for RAG features.

- [x] **Slice 1.1: Qdrant Docker Setup**
  - [x] Create `docker-compose.yml` in project root for Qdrant service
  - [x] Add Qdrant service configuration (port 6333, persistent volume)
  - [x] Test Qdrant starts successfully: `docker compose up -d`
  - [x] Verify Qdrant health endpoint: `http://localhost:6333/health`

- [ ] **Slice 1.2: Add RAG Dependencies**
  - [ ] Add to `pyproject.toml`: `langchain`, `langchain-openai`, `qdrant-client`, `litellm`, `tiktoken`
  - [ ] Run `poetry lock && poetry install` to install dependencies
  - [ ] Verify all packages import correctly in Python REPL

- [ ] **Slice 1.3: Configuration Settings**
  - [ ] Extend `src/config/settings.py` with RAG settings section
  - [ ] Add chunking settings: `CHUNK_SIZE`, `CHUNK_OVERLAP`, `CHUNKING_SEPARATORS`
  - [ ] Add Qdrant settings: `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_COLLECTION`
  - [ ] Add LLM settings: `OPENAI_API_KEY`, `EMBEDDING_MODEL`, `PRIMARY_LLM`, `FALLBACK_LLM`
  - [ ] Add query settings: `TOP_K_CHUNKS`, `MIN_RELEVANCE_SCORE`
  - [ ] Update `.env.example` with new required variables
  - [ ] Add `OPENAI_API_KEY` to local `.env` file
  - [ ] Test settings load correctly when app starts

- [ ] **Slice 1.4: Create RAG Module Structure**
  - [ ] Create `src/rag/__init__.py` with module exports
  - [ ] Create `src/rag/models.py` with Pydantic models: `DocumentChunk`, `QueryResult`, `SourceCitation`, `RAGResult`, `ChatMessage`
  - [ ] Create `src/rag/exceptions.py` with custom exceptions: `RAGError`, `ChunkingError`, `EmbeddingError`, `VectorStoreError`, `QueryError`
  - [ ] Verify imports work: `from src.rag.models import DocumentChunk`

- [ ] **Slice 1.5: Add Placeholder Chat Tab**
  - [ ] Update `src/ui/app.py` to add "💬 Ask Questions" tab alongside "📄 Upload Documents"
  - [ ] Create placeholder content: "RAG Query System - Coming Soon!"
  - [ ] Display Qdrant connection status (green if connected, red if not)
  - [ ] Run app and verify new tab appears, no errors

**Runnable Outcome**: App starts successfully with new tab, Qdrant runs, all infrastructure ready, no errors.

---

### Slice 2: Document Chunking with Preview
**Goal**: Implement document chunking and show chunk preview in UI so users can see their document is being processed.

- [ ] **Slice 2.1: Implement DocumentChunker**
  - [ ] Create `src/rag/chunker.py` with `DocumentChunker` class
  - [ ] Implement `__init__` with LangChain `RecursiveCharacterTextSplitter`
  - [ ] Implement `chunk_document(document: ExtractedDocument) -> list[DocumentChunk]`
  - [ ] Add page number tracking by mapping character positions to pages
  - [ ] Generate unique `chunk_id` (UUID) for each chunk
  - [ ] Calculate `token_count` using tiktoken
  - [ ] Add error handling for empty documents (raise `ChunkingError`)
  - [ ] Add logging for chunk creation

- [ ] **Slice 2.2: Unit Tests for Chunking**
  - [ ] Create `tests/rag/test_chunker.py`
  - [ ] Test chunking a simple document (verify chunk count, overlap)
  - [ ] Test page number tracking accuracy
  - [ ] Test empty document handling (should raise `ChunkingError`)
  - [ ] Test single-sentence document (edge case)
  - [ ] Run tests: `pytest tests/rag/test_chunker.py -v`

- [ ] **Slice 2.3: Add Chunk Preview to Upload UI**
  - [ ] Update `PDFUploadComponent` to optionally show chunk preview
  - [ ] After successful upload, call `DocumentChunker.chunk_document()`
  - [ ] Display expandable section: "📑 Document Chunks (first 3)"
  - [ ] Show chunk content, page numbers, token count for first 3 chunks
  - [ ] Add total chunk count summary
  - [ ] Test with real 10-K document, verify chunks make sense

**Runnable Outcome**: Upload PDF → See chunk preview with page numbers and token counts → Verify chunking works correctly.

---

### Slice 3: Embeddings & Vector Storage
**Goal**: Generate embeddings and store chunks in Qdrant so documents are indexed for search.

- [ ] **Slice 3.1: Implement EmbeddingGenerator**
  - [ ] Create `src/rag/embedder.py` with `EmbeddingGenerator` class
  - [ ] Implement `__init__` with embedding model configuration
  - [ ] Implement `embed_chunks(chunks: list[DocumentChunk]) -> list[DocumentChunk]` (batch processing, max 100 per call)
  - [ ] Implement `embed_query(query: str) -> list[float]` for single query embedding
  - [ ] Use OpenAI embeddings via LiteLLM: `from litellm import embedding`
  - [ ] Add retry logic with exponential backoff (3 attempts)
  - [ ] Add error handling (raise `EmbeddingError` on failures)
  - [ ] Log batch progress for large documents

- [ ] **Slice 3.2: Unit Tests for Embeddings**
  - [ ] Create `tests/rag/test_embedder.py`
  - [ ] Test embedding single chunk (verify 1536 dimensions)
  - [ ] Test batch embedding (10 chunks)
  - [ ] Test query embedding
  - [ ] Mock OpenAI API to test retry logic
  - [ ] Run tests: `pytest tests/rag/test_embedder.py -v`

- [ ] **Slice 3.3: Implement VectorStoreManager**
  - [ ] Create `src/rag/vector_store.py` with `VectorStoreManager` class
  - [ ] Implement `__init__` to connect to Qdrant and ensure collection exists
  - [ ] Implement `_ensure_collection_exists()` to create collection if needed (1536 dimensions, cosine distance)
  - [ ] Implement `upsert_chunks(chunks: list[DocumentChunk]) -> int` to insert chunks with metadata
  - [ ] Implement `search(query_embedding: list[float], top_k: int, min_score: float) -> list[SearchResult]`
  - [ ] Implement `delete_document(document_id: str) -> bool` to remove all chunks for a document
  - [ ] Add error handling (raise `VectorStoreError` if Qdrant unavailable)
  - [ ] Add helpful error message: "Start Qdrant with: docker compose up -d"

- [ ] **Slice 3.4: Unit Tests for Vector Store**
  - [ ] Create `tests/rag/test_vector_store.py`
  - [ ] Test collection creation
  - [ ] Test upserting chunks (insert and verify count)
  - [ ] Test search functionality (create test embedding, search, verify results)
  - [ ] Test document deletion (insert, delete, verify gone)
  - [ ] Test error when Qdrant unavailable (mock connection failure)
  - [ ] Run tests: `pytest tests/rag/test_vector_store.py -v`

- [ ] **Slice 3.5: Add Indexing Progress to Upload UI**
  - [ ] Update `PDFUploadComponent` to show indexing progress
  - [ ] After chunking, add spinner: "Generating embeddings..."
  - [ ] Call `EmbeddingGenerator.embed_chunks()`
  - [ ] Add spinner: "Storing in vector database..."
  - [ ] Call `VectorStoreManager.upsert_chunks()`
  - [ ] Show success message: "✓ Indexed 45 chunks in 3.2s. Ready for questions!"
  - [ ] Handle errors gracefully: "⚠️ Indexing failed: [error message]"
  - [ ] Test with real 10-K, verify chunks stored in Qdrant

**Runnable Outcome**: Upload PDF → Document chunked → Embeddings generated → Stored in Qdrant → See success confirmation with chunk count.

---

### Slice 4: Basic Query Engine (Single Question)
**Goal**: Implement query processing to answer one question at a time (not chat yet) with source citations.

- [ ] **Slice 4.1: Implement RAGQueryEngine**
  - [ ] Create `src/rag/query_engine.py` with `RAGQueryEngine` class
  - [ ] Implement `__init__` with dependencies (vector_store, embedder, llm_model, fallback_model)
  - [ ] Implement `_create_prompt_template()` with system prompt including guardrails
  - [ ] System prompt rules: answer only from context, cite sources with [Page X], refuse if no context
  - [ ] Implement `query(question: str) -> QueryResult`
  - [ ] Step 1: Embed query using `embedder.embed_query()`
  - [ ] Step 2: Search vector store for top-K chunks
  - [ ] Step 3: Check if minimum relevance score met, else return "no information found"
  - [ ] Step 4: Format context with page citations: `[Page X]: {chunk.content}`
  - [ ] Step 5: Call LLM via LiteLLM with `completion()` and fallback configuration
  - [ ] Step 6: Extract sources from retrieved chunks into `SourceCitation` objects
  - [ ] Step 7: Return `QueryResult` with answer and sources
  - [ ] Add error handling (raise `QueryError` on failures)
  - [ ] Add logging throughout

- [ ] **Slice 4.2: Test LiteLLM Integration**
  - [ ] Create small test script to verify LiteLLM works with OpenAI
  - [ ] Test primary model call (`gpt-4-turbo-preview`)
  - [ ] Test fallback mechanism (simulate rate limit, verify fallback to `gpt-3.5-turbo`)
  - [ ] Test error handling when both models fail
  - [ ] Verify `OPENAI_API_KEY` is loaded correctly

- [ ] **Slice 4.3: Unit Tests for Query Engine**
  - [ ] Create `tests/rag/test_query_engine.py`
  - [ ] Test successful query with relevant chunks (mock vector store results)
  - [ ] Test query with no relevant chunks (verify refusal message)
  - [ ] Test source citation extraction
  - [ ] Test LLM fallback mechanism (mock primary failure)
  - [ ] Test guardrails (verify system prompt used correctly)
  - [ ] Run tests: `pytest tests/rag/test_query_engine.py -v`

- [ ] **Slice 4.4: Add Simple Query UI**
  - [ ] Update "Ask Questions" tab to show text input: `st.text_input("Ask a question...")`
  - [ ] Add submit button
  - [ ] When submitted, show spinner: "Searching documents..."
  - [ ] Initialize `RAGQueryEngine` with dependencies
  - [ ] Call `query_engine.query(question)`
  - [ ] Display answer in styled container
  - [ ] Display sources below answer: show page numbers, snippet preview, relevance score
  - [ ] Handle errors: display error message if query fails
  - [ ] Test with real question: "What were the main revenue drivers?"

**Runnable Outcome**: Ask single question → Get answer with page citations → Verify answer accuracy against source document.

---

### Slice 5: Full Chat Interface with History
**Goal**: Replace single-question input with full conversational chat interface.

- [ ] **Slice 5.1: Create ChatComponent**
  - [ ] Create `src/ui/components/chat.py` with `ChatComponent` class
  - [ ] Implement `__init__(rag_service)` constructor
  - [ ] Implement `render(document_id: str | None = None)`
  - [ ] Initialize chat history in `st.session_state.messages` if not exists
  - [ ] Display chat header: "Ask Questions About Your Documents"
  - [ ] Show example questions on first load using `_show_example_questions()`
  - [ ] Iterate through `st.session_state.messages` and display each with `st.chat_message()`
  - [ ] For assistant messages, show sources in expandable `st.expander("📚 View Sources")`
  - [ ] Add chat input: `st.chat_input("Ask a question...")`
  - [ ] When user sends message, display immediately and add to history
  - [ ] Process query with spinner: "Searching documents..."
  - [ ] Display assistant response and add to history
  - [ ] Auto-scroll to latest message (Streamlit does this automatically)

- [ ] **Slice 5.2: Implement Example Questions**
  - [ ] Implement `_show_example_questions()` method
  - [ ] Display 3-4 example questions in `st.info()` box:
    - "What were the main revenue drivers?"
    - "What are the top 3 risks mentioned?"
    - "How did operating expenses change?"
  - [ ] Make examples clickable (use `st.button()` in columns) to auto-fill question
  - [ ] Test clicking example question → input auto-filled → question submitted

- [ ] **Slice 5.3: Implement Source Citation Display**
  - [ ] Implement `_display_sources(sources: list[SourceCitation])` method
  - [ ] For each source, create container with:
    - Source number (1, 2, 3...)
    - Page numbers as metric: `st.metric("Pages", "5, 6")`
    - Relevance score as metric: `st.metric("Relevance", "87%")`
    - Snippet preview (first 200 characters)
  - [ ] Add visual separators between sources
  - [ ] Test with multi-source answer, verify sources display correctly

- [ ] **Slice 5.4: Replace Single Input with Chat UI**
  - [ ] Update "Ask Questions" tab to use `ChatComponent.render()`
  - [ ] Remove old single-question UI code
  - [ ] Verify conversation history persists within session
  - [ ] Test follow-up questions: "Tell me more about that" → verify context from previous messages
  - [ ] Test page refresh → verify history resets (expected behavior)

**Runnable Outcome**: Full conversational interface → Ask multiple questions → See history → View expandable sources → Verify follow-up questions work.

---

### Slice 6: RAG Service Orchestration
**Goal**: Create clean service layer to orchestrate all RAG components and integrate with existing PDF upload flow.

- [ ] **Slice 6.1: Implement RAGService**
  - [ ] Create `src/rag/service.py` with `RAGService` class
  - [ ] Implement `__init__` with dependency injection (chunker, embedder, vector_store, query_engine)
  - [ ] Implement `process_document(document: ExtractedDocument) -> RAGResult`
    - Step 1: Chunk document
    - Step 2: Generate embeddings
    - Step 3: Upsert to vector store
    - Step 4: Return `RAGResult` with success, chunk counts, processing time
    - Add try/except for error handling, return `RAGResult` with error message on failure
  - [ ] Implement `query(question: str) -> QueryResult` (delegates to `query_engine.query()`)
  - [ ] Implement `delete_document(document_id: str) -> bool` (delegates to `vector_store.delete_document()`)
  - [ ] Add comprehensive logging throughout

- [ ] **Slice 6.2: Integration Tests for RAGService**
  - [ ] Create `tests/rag/test_rag_service.py`
  - [ ] Test end-to-end document processing with real `ExtractedDocument`
  - [ ] Test query processing with real question
  - [ ] Test document deletion
  - [ ] Test error handling (Qdrant unavailable, API key missing)
  - [ ] Run tests: `pytest tests/rag/test_rag_service.py -v`

- [ ] **Slice 6.3: Integrate with PDFProcessingService**
  - [ ] Update `src/ui/components/upload.py` to accept `rag_service: RAGService | None` in constructor
  - [ ] After successful PDF processing, check if `rag_service` is available
  - [ ] If available, call `rag_service.process_document(result.document)` with spinner
  - [ ] Display indexing result: "✓ Indexed 45 chunks in 3.2s. You can now ask questions!"
  - [ ] Store `document_id` in `st.session_state.current_document_id` for chat reference
  - [ ] Handle indexing failures gracefully: "Document uploaded but indexing failed: [error]"

- [ ] **Slice 6.4: Initialize RAG Service in Main App**
  - [ ] Update `src/ui/app.py` to initialize `RAGService` with all dependencies
  - [ ] Wrap initialization in try/except to handle Qdrant unavailable scenario
  - [ ] If Qdrant unavailable, set `rag_service = None` and log warning
  - [ ] Pass `rag_service` to `PDFUploadComponent` and `ChatComponent`
  - [ ] In chat tab, show error if `rag_service is None`: "RAG service unavailable. Start Qdrant: docker compose up -d"
  - [ ] Test graceful degradation: stop Qdrant, verify app still works for uploads

- [ ] **Slice 6.5: Document Cleanup on Deletion**
  - [ ] Add document deletion feature to UI (optional for this phase)
  - [ ] When document deleted, call `rag_service.delete_document(document_id)`
  - [ ] Verify chunks removed from Qdrant
  - [ ] Test: upload document → delete → verify Qdrant no longer has chunks

**Runnable Outcome**: Clean service architecture → Upload flow integrated with RAG → Graceful degradation if Qdrant down → Document cleanup works.

---

### Slice 7: Testing, Quality & Documentation
**Goal**: Comprehensive testing, quality checks, performance validation, and documentation.

- [ ] **Slice 7.1: Complete Unit Test Coverage**
  - [ ] Ensure all components have unit tests (chunker, embedder, vector_store, query_engine, service)
  - [ ] Run full test suite: `pytest tests/rag/ -v --cov=src/rag`
  - [ ] Verify >90% code coverage for RAG module
  - [ ] Fix any failing tests

- [ ] **Slice 7.2: End-to-End Integration Test**
  - [ ] Create `tests/integration/test_rag_e2e.py`
  - [ ] Test full flow: upload real 10-K → chunk → embed → index → query → verify answer accuracy
  - [ ] Use sample document from `data/sample/`
  - [ ] Ask 3-5 real questions and verify answers against document
  - [ ] Verify source citations match actual pages
  - [ ] Test follow-up question with conversation context
  - [ ] Run test: `pytest tests/integration/test_rag_e2e.py -v`

- [ ] **Slice 7.3: Manual Testing with Real Documents**
  - [ ] Use Amazon 10-K from `data/sample/`
  - [ ] Test question types:
    - Simple: "What were the main revenue drivers?"
    - Complex: "What are the top 3 risks?"
    - Multi-part: "How did Q3 and Q4 revenue compare?"
    - Out-of-scope: "What is the current stock price?" (should decline gracefully)
  - [ ] Verify all citations match actual pages in source PDF
  - [ ] Verify answers are factually correct from document
  - [ ] Test with 2-3 different 10-K documents
  - [ ] Document results in test log

- [ ] **Slice 7.4: Performance Benchmarking**
  - [ ] Measure document indexing time (target: <30s for typical 10-K)
  - [ ] Measure query response time (target: <30s for typical questions)
  - [ ] Measure Qdrant search latency (target: <500ms)
  - [ ] Test embedding batch sizes (100 chunks at a time)
  - [ ] Log performance metrics
  - [ ] Optimize if any targets not met

- [ ] **Slice 7.5: Code Quality Checks**
  - [ ] Run ruff linter: `ruff check src/rag/` (0 issues expected)
  - [ ] Run mypy type checker: `mypy src/rag/ --strict` (0 errors expected)
  - [ ] Fix any type errors or linting issues
  - [ ] Verify 100% type hint coverage in RAG module
  - [ ] Run full test suite one more time: `pytest tests/ -v`

- [ ] **Slice 7.6: Documentation Updates**
  - [ ] Update `README.md` with RAG setup instructions:
    - Docker Compose setup for Qdrant
    - OpenAI API key configuration
    - Usage examples
  - [ ] Create `docs/RAG_ARCHITECTURE.md` explaining the RAG system design
  - [ ] Add docstrings to all public methods (if missing)
  - [ ] Update architecture diagram to include RAG components

- [ ] **Slice 7.7: Create Test Results Document**
  - [ ] Create `context/spec/002-rag-query-chat-interface/TEST_RESULTS.md`
  - [ ] Document all test results (unit, integration, manual)
  - [ ] Include performance benchmarks
  - [ ] Add screenshots of chat interface
  - [ ] List any known issues or limitations
  - [ ] Sign off on feature completion

**Runnable Outcome**: Fully tested, validated, documented, production-ready RAG Query System & Chat Interface.

---

## Summary

**Total Slices**: 7
**Total Sub-tasks**: 54

Each slice is designed to be **independently runnable and testable**. After completing any slice, the application can be started without errors and the new functionality is visible/testable.

**Key Principles Applied**:
- ✅ Vertical slicing (end-to-end increments)
- ✅ Runnable after each slice
- ✅ User-visible progress
- ✅ Incremental complexity
- ✅ Test as you go
- ✅ Clean architecture

**Estimated Effort**: ~15-20 hours total development time

---

## Next Steps

Execute tasks incrementally using `/awos:implement` when ready to begin implementation.
