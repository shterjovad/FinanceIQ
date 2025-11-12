# Phase 4: Session-Based Isolation - Technical Specification
## Browser-Session-Only Implementation

## Architecture Overview

### Simplified Design (No Database!)

```
┌─────────────────────────────────────────────────────────┐
│              Streamlit UI (Browser)                      │
│  ┌──────────────────────────────────────────────────┐  │
│  │  st.session_state                                 │  │
│  │  • session_id: UUID (generated on first load)    │  │
│  │  • document_count: int                           │  │
│  │  • messages: list (chat history)                 │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│           RAGService (Enhanced with session_id)          │
│  • All methods accept session_id parameter              │
│  • Auto-filters by session                             │
└─────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────┬──────────────────────────────────────┐
│  Qdrant          │  File System                         │
│  (session filter)│  (session directories)               │
└──────────────────┴──────────────────────────────────────┘
```

**Key Simplifications:**
- ❌ No SQLite database
- ❌ No SessionService class
- ❌ No cleanup jobs/workers
- ❌ No expiration tracking
- ✅ Just UUID in st.session_state
- ✅ Session auto-cleared when tab closes

## Data Models

### Minimal Session Tracking

```python
# Session data lives entirely in st.session_state
# No database, no persistence, no cleanup needed!

# In Streamlit app:
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.document_count = 0

# That's it! Browser manages lifetime.
```

### Enhanced Vector Store Payload

```python
# Only change: Add session_id to Qdrant payloads

{
    "session_id": "abc123-def456-...",  # ← NEW: Isolation key
    "document_id": "abc123_aapl-10k.pdf",
    "text": "Apple Inc. reported...",
    "page_numbers": [42],
    "chunk_index": 5,
    "start_char": 1000,
    "end_char": 2000,
    # ... rest unchanged
}
```

## Component Changes

### 1. Streamlit App (app.py)

**Changes:**
- Add session initialization
- Pass session_id to all RAG operations
- Display session status

```python
# src/ui/app.py

import streamlit as st
from uuid import uuid4

def initialize_session():
    """Initialize session ID if not exists."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid4())
        st.session_state.document_count = 0
        logger.info(f"New session created: {st.session_state.session_id[:8]}...")

def render_session_status():
    """Display session info in sidebar."""
    with st.sidebar:
        st.divider()
        st.subheader("🔒 Your Session")
        st.caption(f"Status: Active")
        st.caption(f"Documents: {st.session_state.document_count}")
        st.caption(f"Type: Browser session")

        with st.expander("Privacy Notice", expanded=False):
            st.caption(
                "• Isolated to this browser tab\n"
                "• Not visible to other users\n"
                "• Cleared when you close tab"
            )

def main():
    st.set_page_config(
        page_title="FinanceIQ",
        page_icon="📊",
        layout="wide",
    )

    # Initialize session
    initialize_session()

    # Header with session info
    st.title("FinanceIQ - Financial Document Analysis")
    st.caption(
        f"🔒 Private Session | "
        f"{st.session_state.document_count} docs | "
        f"Tab-only"
    )

    # Initialize RAG service
    rag_service = initialize_rag_service()

    # Render session status
    render_session_status()

    # Create tabs
    tab1, tab2 = st.tabs(["📄 Upload Documents", "💬 Ask Questions"])

    with tab1:
        upload_component = PDFUploadComponent(
            rag_service=rag_service,
            session_id=st.session_state.session_id  # ← Pass session
        )
        upload_component.render()

    with tab2:
        chat_component = ChatComponent(
            rag_service=rag_service,
            session_id=st.session_state.session_id  # ← Pass session
        )
        chat_component.render()
```

### 2. Enhanced RAG Service

**Location**: `src/rag/service.py`

**Changes:**
- Add `session_id` parameter to `process_document()`
- Add `session_id` parameter to `query()`
- Pass session_id through to query engine

```python
class RAGService:
    """RAG service with session isolation support."""

    def process_document(
        self,
        document: ExtractedDocument,
        session_id: str  # ← NEW parameter
    ) -> RAGResult:
        """Process document with session isolation.

        Args:
            document: Extracted PDF document
            session_id: Browser session ID for isolation

        Returns:
            RAGResult with processing status
        """
        start_time = time.time()

        # Prefix document_id with session for uniqueness
        original_doc_id = document.document_id
        document.document_id = f"{session_id}_{document.document_id}"

        logger.info(
            f"Processing document {document.filename} "
            f"for session {session_id[:8]}..."
        )

        try:
            # Step 1: Chunk document
            chunks = self.chunker.chunk_document(document)

            # Step 2: Generate embeddings
            chunks_with_embeddings = self.embedder.embed_chunks(chunks)

            # Step 3: Add session_id to all chunks
            for chunk in chunks_with_embeddings:
                chunk.session_id = session_id  # ← Tag with session

            # Step 4: Upsert to vector store
            chunks_indexed = self.vector_store.upsert_chunks(
                chunks_with_embeddings,
                session_id=session_id  # ← Pass session
            )

            processing_time = time.time() - start_time

            logger.info(
                f"Document {document.filename} processed successfully "
                f"for session {session_id[:8]}... in {processing_time:.2f}s"
            )

            return RAGResult(
                success=True,
                document_id=original_doc_id,
                chunks_created=len(chunks),
                chunks_indexed=chunks_indexed,
                processing_time_seconds=processing_time,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Failed to process document: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return RAGResult(
                success=False,
                document_id=original_doc_id,
                chunks_created=0,
                chunks_indexed=0,
                processing_time_seconds=processing_time,
                error_message=error_msg,
            )

    def query(
        self,
        question: str,
        session_id: str  # ← NEW parameter
    ) -> QueryResult:
        """Query with automatic session filtering.

        Args:
            question: User's natural language question
            session_id: Browser session ID for isolation

        Returns:
            QueryResult with answer and sources
        """
        logger.info(
            f"RAGService received query for session {session_id[:8]}...: "
            f"{question[:100]}..."
        )

        try:
            # Use agent workflow if enabled
            if self.use_agents and self.agent_workflow:
                result = self._query_with_agents(question, session_id)
            else:
                result = self._query_direct(question, session_id)

            logger.info(
                f"Query completed for session {session_id[:8]}... "
                f"in {result.query_time_seconds:.2f}s"
            )
            return result

        except Exception as e:
            logger.error(f"Query failed: {str(e)}", exc_info=True)
            raise

    def _query_direct(self, question: str, session_id: str) -> QueryResult:
        """Execute query directly through standard query engine."""
        logger.info(f"Using standard query processing for session {session_id[:8]}...")
        return self.query_engine.query(question, session_id=session_id)

    def _query_with_agents(self, question: str, session_id: str) -> QueryResult:
        """Execute query through multi-agent workflow."""
        logger.info(f"Using agent-based query processing for session {session_id[:8]}...")

        from src.agents.models import AgentState

        # Create initial agent state
        initial_state: AgentState = {
            "original_question": question,
            "session_id": session_id,  # ← Pass session to agents
            "agent_calls": [],
            "reasoning_steps": [],
        }

        # Execute agent workflow
        start_time = time.time()
        agent_result: AgentState = self.agent_workflow.invoke(initial_state)
        agent_time = time.time() - start_time

        # Store agent state for UI access
        self.last_agent_state = agent_result

        # ... rest of agent handling logic (unchanged)
```

### 3. Enhanced Vector Store

**Location**: `src/rag/vector_store.py`

**Changes:**
- Add session_id to chunk payloads
- Add session filtering to search

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

class VectorStoreManager:
    """Vector store with session isolation."""

    def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        session_id: str  # ← NEW parameter
    ) -> int:
        """Upsert chunks with session metadata.

        Args:
            chunks: List of document chunks with embeddings
            session_id: Browser session ID for isolation

        Returns:
            Number of chunks upserted
        """
        from qdrant_client.models import PointStruct

        points = []
        for chunk in chunks:
            points.append(
                PointStruct(
                    id=chunk.chunk_id,
                    vector=chunk.embedding,
                    payload={
                        "session_id": session_id,  # ← Add session
                        "document_id": chunk.document_id,
                        "text": chunk.text,
                        "page_numbers": chunk.page_numbers,
                        "chunk_index": chunk.chunk_index,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                    }
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        logger.info(
            f"Upserted {len(points)} chunks for session {session_id[:8]}..."
        )

        return len(points)

    def search(
        self,
        query_vector: list[float],
        session_id: str,  # ← NEW parameter
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> list[SearchResult]:
        """Search with automatic session filtering.

        Args:
            query_vector: Query embedding vector
            session_id: Browser session ID for isolation
            top_k: Number of results to return
            min_score: Minimum relevance score threshold

        Returns:
            List of search results from current session only
        """
        logger.debug(
            f"Searching for session {session_id[:8]}... "
            f"(top_k={top_k}, min_score={min_score})"
        )

        # Search with session filter
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=min_score,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="session_id",
                        match=MatchValue(value=session_id)  # ← Filter by session
                    )
                ]
            )
        )

        results = [self._convert_to_search_result(hit) for hit in search_results]

        logger.debug(
            f"Found {len(results)} results for session {session_id[:8]}..."
        )

        return results
```

### 4. Enhanced Query Engine

**Location**: `src/rag/query_engine.py`

**Changes:**
- Add session_id parameter to query()
- Pass session_id to vector store search

```python
class RAGQueryEngine:
    """Query engine with session support."""

    def query(
        self,
        question: str,
        session_id: str  # ← NEW parameter
    ) -> QueryResult:
        """Execute query with automatic session filtering.

        Args:
            question: User's natural language question
            session_id: Browser session ID for isolation

        Returns:
            QueryResult with answer and sources
        """
        start_time = time.time()

        logger.info(f"Query: {question[:100]}... (session: {session_id[:8]}...)")

        # Validate input
        if not question or not question.strip():
            raise ValueError("Query cannot be empty")

        # Step 1: Generate query embedding
        query_embedding = self.embedder.embed_query(question)

        # Step 2: Search vector store with session filter
        search_results = self.vector_store.search(
            query_vector=query_embedding,
            session_id=session_id,  # ← Pass session
            top_k=self.top_k,
            min_score=self.min_score
        )

        # Step 3: Handle no results
        if not search_results:
            return QueryResult(
                success=True,
                answer="I don't have enough information in the documents to answer that question.",
                sources=[],
                chunks_retrieved=0,
                query_time_seconds=time.time() - start_time,
            )

        # ... rest of query logic (unchanged)
```

### 5. Enhanced Upload Component

**Location**: `src/ui/components/upload.py`

**Changes:**
- Accept session_id parameter
- Pass to RAG service
- Update document count in session state

```python
class PDFUploadComponent:
    """PDF upload component with session isolation."""

    def __init__(
        self,
        rag_service: RAGService | None,
        session_id: str  # ← NEW parameter
    ):
        self.rag_service = rag_service
        self.session_id = session_id

    def render(self):
        st.header("Upload Documents")

        if self.rag_service is None:
            st.warning("RAG system unavailable. Please check configuration.")
            return

        # Session warning
        st.info(
            "🔒 **Private Session**\n\n"
            "• Documents uploaded to your isolated session\n"
            "• Not visible to other users\n"
            "• Cleared when you close this tab"
        )

        uploaded_files = st.file_uploader(
            "Upload PDF documents",
            type=["pdf"],
            accept_multiple_files=True,
            help="Upload financial documents (10-Ks, earnings reports, etc.)"
        )

        if uploaded_files:
            for uploaded_file in uploaded_files:
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    # Extract document
                    extractor = PDFTextExtractor()
                    document = extractor.extract_text(uploaded_file)

                    # Process with session isolation
                    result = self.rag_service.process_document(
                        document=document,
                        session_id=self.session_id  # ← Pass session
                    )

                    if result.success:
                        st.success(
                            f"✅ **{uploaded_file.name}** uploaded successfully\n\n"
                            f"• {result.chunks_created} chunks created\n"
                            f"• Stored in your private session\n"
                            f"• Processing time: {result.processing_time_seconds:.2f}s"
                        )

                        # Update session document count
                        st.session_state.document_count += 1

                    else:
                        st.error(f"❌ Failed to process {uploaded_file.name}: {result.error_message}")
```

### 6. Enhanced Chat Component

**Location**: `src/ui/components/chat.py`

**Changes:**
- Accept session_id parameter
- Pass to RAG service queries
- Display session scope

```python
class ChatComponent:
    """Chat component with session isolation."""

    def __init__(
        self,
        rag_service: RAGService | None,
        session_id: str  # ← NEW parameter
    ):
        self.rag_service = rag_service
        self.session_id = session_id

    def render(self):
        st.header("Chat with Your Documents")

        if self.rag_service is None:
            st.warning("RAG system unavailable.")
            return

        # Session scope indicator
        doc_count = st.session_state.get("document_count", 0)
        if doc_count > 0:
            st.info(
                f"🔍 **Query Scope:** {doc_count} document(s) in your session"
            )
        else:
            st.warning(
                "No documents uploaded yet. Go to the 'Upload Documents' tab first."
            )
            return

        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []
            self._show_example_questions()

        # Display existing chat history
        for message in st.session_state.messages:
            self._render_message(message)

        # Chat input
        if prompt := st.chat_input("Ask a question about your documents..."):
            self._handle_user_input(prompt)

    def _process_query(self, user_message: str):
        """Process query with session isolation."""
        try:
            # Query with session filter
            result = self.rag_service.query(
                question=user_message,
                session_id=self.session_id  # ← Pass session
            )

            # Extract agent metadata if agents were used
            reasoning_steps = None
            query_type = None

            if st.session_state.get("use_agents", False) and self.rag_service.agent_workflow:
                reasoning_steps, query_type = self.rag_service.get_last_reasoning_steps()

            # Add assistant response
            assistant_msg: ChatMessage = {
                "role": "assistant",
                "content": result.answer,
                "sources": result.sources,
                "reasoning_steps": reasoning_steps,
                "query_type": query_type,
            }
            st.session_state.messages.append(assistant_msg)

        except Exception as e:
            logger.error(f"Query failed: {str(e)}", exc_info=True)
            error_msg: ChatMessage = {
                "role": "assistant",
                "content": f"❌ Sorry, I encountered an error: {str(e)}",
                "sources": None,
                "reasoning_steps": None,
                "query_type": None,
            }
            st.session_state.messages.append(error_msg)
```

## Storage Strategy

### File System Structure

```
data/uploads/sessions/
├── abc123-def456.../          # Session directory (UUID)
│   ├── aapl-10k-2024.pdf
│   └── msft-10k-2024.pdf
├── xyz789-abc123.../          # Another session
│   └── googl-10k-2024.pdf
└── ...                        # More sessions

# Note: Files accumulate until manual cleanup
# This is fine for demo - storage is cheap
# Optional: Run cleanup script weekly/monthly
```

### Qdrant Collection Structure

```python
# Single collection with session-based payloads

Collection: "financial_docs"
├── Point 1:
│   vector: [0.1, 0.2, ...]
│   payload: {
│       "session_id": "abc123...",  # ← Isolation key
│       "document_id": "abc123_aapl-10k",
│       "text": "...",
│       ...
│   }
├── Point 2:
│   vector: [0.3, 0.4, ...]
│   payload: {
│       "session_id": "def456...",  # ← Different session
│       "document_id": "def456_googl-10k",
│       ...
│   }
```

## Optional: Simple Cleanup Script

**Location**: `scripts/cleanup_old_sessions.py`

```python
"""Optional cleanup script for orphaned session data.

Run weekly/monthly to clean up files from closed sessions.
Not critical - just housekeeping to save storage.
"""

import shutil
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def cleanup_old_sessions(days_old: int = 7):
    """Delete session files older than N days.

    Args:
        days_old: Delete sessions older than this many days
    """
    upload_dir = Path("data/uploads/sessions")
    cutoff = datetime.now() - timedelta(days=days_old)

    deleted_count = 0
    deleted_size_mb = 0

    for session_dir in upload_dir.iterdir():
        if not session_dir.is_dir():
            continue

        # Check if directory is older than cutoff
        mod_time = datetime.fromtimestamp(session_dir.stat().st_mtime)

        if mod_time < cutoff:
            # Calculate size
            size_mb = sum(f.stat().st_size for f in session_dir.rglob("*")) / (1024 * 1024)

            # Delete directory
            shutil.rmtree(session_dir)

            deleted_count += 1
            deleted_size_mb += size_mb

            logger.info(f"Deleted session {session_dir.name[:8]}... ({size_mb:.2f}MB)")

    logger.info(
        f"Cleanup complete: {deleted_count} sessions, {deleted_size_mb:.2f}MB freed"
    )

    return {"sessions_deleted": deleted_count, "size_mb_freed": deleted_size_mb}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = cleanup_old_sessions(days_old=7)
    print(f"Cleanup result: {result}")
```

## Testing Strategy

### Unit Tests

```python
# tests/session/test_session_isolation.py

def test_session_id_in_streamlit_state(client):
    """Test session ID is created and stored."""
    # Simulate page load
    response = client.get("/")

    # Check session_id was created
    assert "session_id" in st.session_state
    assert len(st.session_state.session_id) == 36  # UUID length

def test_document_tagged_with_session():
    """Test documents are tagged with session ID."""
    session_id = "test-session-123"

    result = rag_service.process_document(
        document=test_doc,
        session_id=session_id
    )

    # Verify document ID includes session
    assert result.document_id.startswith(session_id)

def test_query_filtered_by_session():
    """Test queries are automatically filtered by session."""
    # Upload doc in session A
    rag_service.process_document(apple_doc, session_id="session_a")

    # Query from session B should not see doc
    result = rag_service.query(
        question="What was Apple's revenue?",
        session_id="session_b"
    )

    assert "don't have information" in result.answer.lower()
```

### Integration Tests

```python
# tests/integration/test_multi_tab_isolation.py

@pytest.mark.integration
def test_multi_tab_isolation():
    """Test complete isolation between browser tabs."""

    # Simulate Tab 1
    session_a = str(uuid4())
    rag_service.process_document(apple_doc, session_id=session_a)

    # Simulate Tab 2
    session_b = str(uuid4())
    rag_service.process_document(google_doc, session_id=session_b)

    # Tab 1 queries for Apple (should work)
    result_a = rag_service.query("What was Apple's revenue?", session_id=session_a)
    assert "Apple" in result_a.answer
    assert result_a.success

    # Tab 1 queries for Google (should fail - not in session)
    result_a_google = rag_service.query("What was Google's revenue?", session_id=session_a)
    assert "don't have" in result_a_google.answer.lower()

    # Tab 2 queries for Google (should work)
    result_b = rag_service.query("What was Google's revenue?", session_id=session_b)
    assert "Google" in result_b.answer
    assert result_b.success

    # Tab 2 queries for Apple (should fail - not in session)
    result_b_apple = rag_service.query("What was Apple's revenue?", session_id=session_b)
    assert "don't have" in result_b_apple.answer.lower()

@pytest.mark.integration
def test_session_persists_across_refresh():
    """Test session persists when page is refreshed."""
    # Simulate first page load
    session_id = str(uuid4())
    st.session_state.session_id = session_id

    # Upload document
    rag_service.process_document(apple_doc, session_id=session_id)

    # Simulate page refresh (session_id still in st.session_state)
    # Query should still work
    result = rag_service.query("What was revenue?", session_id=session_id)
    assert result.success
    assert len(result.sources) > 0
```

## Implementation Slices

### Slice 1: Session ID in Streamlit (Day 1 - Morning)
**Estimated: 2-3 hours**

- Add session_id to st.session_state
- Display session info in UI
- Basic testing

**Files Changed:**
- `src/ui/app.py`

**Deliverable:** Session ID created and displayed

### Slice 2: RAG Service Session Parameters (Day 1 - Afternoon)
**Estimated: 2-3 hours**

- Add session_id parameter to RAGService methods
- Add session_id parameter to QueryEngine
- Update method signatures
- Unit tests

**Files Changed:**
- `src/rag/service.py`
- `src/rag/query_engine.py`

**Deliverable:** RAG methods accept session_id

### Slice 3: Vector Store Session Filtering (Day 2 - Morning)
**Estimated: 3-4 hours**

- Add session_id to chunk payloads
- Add session filtering to search
- Update upsert method
- Tests

**Files Changed:**
- `src/rag/vector_store.py`

**Deliverable:** Qdrant queries filtered by session

### Slice 4: UI Component Integration (Day 2 - Afternoon)
**Estimated: 2-3 hours**

- Update UploadComponent to pass session_id
- Update ChatComponent to pass session_id
- Update document count tracking
- Tests

**Files Changed:**
- `src/ui/components/upload.py`
- `src/ui/components/chat.py`

**Deliverable:** Full UI integration with sessions

### Slice 5: Multi-Tab Isolation Testing (Day 3 - Morning)
**Estimated: 2-3 hours**

- Integration tests for isolation
- Manual testing with multiple tabs
- Fix any issues
- Performance testing

**Deliverable:** Verified isolation between tabs

### Slice 6: Polish & Documentation (Day 3 - Afternoon)
**Estimated: 2-3 hours**

- Privacy notices in UI
- Error handling
- Session status display
- Documentation updates
- Optional cleanup script

**Deliverable:** Production-ready Phase 4

**Total: 2-3 days**

## Configuration

### Settings (No Changes Needed!)

```python
# src/config/settings.py

# No new settings required!
# Session isolation uses existing infrastructure
# Just UUID generation and Qdrant filtering
```

## Deployment

### Streamlit Cloud

```toml
# .streamlit/config.toml

[server]
maxUploadSize = 100  # MB per session
enableXsrfProtection = true

[browser]
gatherUsageStats = false
```

### Environment Variables

```bash
# .env

# No changes needed for Phase 4!
# Existing settings work fine
OPENAI_API_KEY=sk-...
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## Success Metrics

- ✅ Session ID created on first page load
- ✅ Documents tagged with session_id
- ✅ Queries filtered by session_id (100% isolation)
- ✅ Session persists across page refreshes
- ✅ Multiple tabs completely isolated
- ✅ Zero data leakage between sessions
- ✅ Performance overhead <5%
- ✅ Ready for public deployment

## Security Checklist

- [ ] Session IDs are cryptographically random (UUID4)
- [ ] No session ID leakage in logs
- [ ] Qdrant filters properly enforce isolation
- [ ] File system directories isolated per session
- [ ] Cannot guess or enumerate session IDs
- [ ] Privacy notices displayed prominently
- [ ] Multi-tab isolation tested thoroughly
- [ ] Error messages don't leak session information

## Comparison: Before vs. After

### Before Phase 4
```python
# All documents mixed together
rag_service.process_document(apple_doc)
rag_service.process_document(google_doc)

# User A queries - sees BOTH Apple and Google
result = rag_service.query("revenue")
# ❌ Data leakage!
```

### After Phase 4
```python
# Tab 1 (User A)
rag_service.process_document(apple_doc, session_id="abc123")
result = rag_service.query("revenue", session_id="abc123")
# ✅ Sees only Apple

# Tab 2 (User B)
rag_service.process_document(google_doc, session_id="def456")
result = rag_service.query("revenue", session_id="def456")
# ✅ Sees only Google

# Perfect isolation! ✅
```

## Next Steps After Phase 4

With session isolation complete, you can:

1. **Deploy immediately** - Safe for public use
2. **Add to resume/portfolio** - Live demo link
3. **Phase 5** - Multi-document comparison (optional enhancement)
4. **Get feedback** - From users trying the demo

**Phase 4 makes everything safe. Phase 5 makes it powerful.** ✅
