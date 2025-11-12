# Phase 3: Multi-Document Comparison - Technical Specification

## Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Document    │  │  Collection  │  │  Multi-Doc   │ │
│  │  Manager     │  │  Manager     │  │  Chat        │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              RAGService (Enhanced)                       │
│  • Multi-document query routing                         │
│  • Document metadata management                         │
│  • Collection-based querying                            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│          Enhanced Agent Workflow (LangGraph)            │
│  ┌───────────────┐  ┌──────────────────────────────┐  │
│  │ Document      │→ │ Multi-Document Query         │  │
│  │ Router Agent  │  │ Executor (parallel/sequential)│  │
│  └───────────────┘  └──────────────────────────────┘  │
│           ↓                     ↓                       │
│  ┌───────────────────────────────────────────────┐    │
│  │ Comparison Synthesizer Agent                   │    │
│  │ • Cross-document synthesis                     │    │
│  │ • Structured comparisons (tables, timelines)   │    │
│  └───────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Qdrant Vector Store                         │
│  • Per-document collections or namespaces               │
│  • Document metadata filtering                          │
│  • Cross-collection search                              │
└─────────────────────────────────────────────────────────┘
```

## Data Models

### DocumentMetadata
```python
from pydantic import BaseModel
from datetime import datetime

class DocumentMetadata(BaseModel):
    """Extended document metadata for multi-doc support."""
    document_id: str
    filename: str
    company_name: str | None = None  # Extracted or manual
    year: int | None = None
    quarter: str | None = None  # Q1, Q2, Q3, Q4
    document_type: str | None = None  # 10-K, 10-Q, earnings, etc.
    upload_date: datetime
    page_count: int
    file_size_mb: float
    tags: list[str] = []
    collection_ids: list[str] = []  # Which collections this doc belongs to
```

### Collection
```python
class Collection(BaseModel):
    """Document collection for grouping related documents."""
    collection_id: str
    name: str
    description: str | None = None
    document_ids: list[str]
    created_date: datetime
    modified_date: datetime
    is_system: bool = False  # True for "All Documents", "Recent", etc.
```

### MultiDocumentQuery
```python
class MultiDocumentQuery(BaseModel):
    """Query targeting multiple documents."""
    question: str
    document_ids: list[str] | None = None  # Specific documents
    collection_id: str | None = None  # Or entire collection
    query_type: str  # "comparison", "time_series", "aggregation", "ranking"
```

### ComparativeResult
```python
class DocumentResult(BaseModel):
    """Result from a single document."""
    document_id: str
    company_name: str | None
    year: int | None
    answer: str
    sources: list[SourceCitation]
    chunks_retrieved: int

class ComparativeResult(BaseModel):
    """Result combining multiple document results."""
    success: bool
    question: str
    document_results: list[DocumentResult]  # Results per document
    synthesized_answer: str  # Comparative synthesis
    comparison_type: str  # "table", "timeline", "ranking", "narrative"
    comparison_data: dict[str, Any] | None  # Structured data for viz
    total_documents_searched: int
    documents_with_results: int
    query_time_seconds: float
```

## Component Design

### 1. Document Management Service

**Location**: `src/document_manager/service.py`

```python
class DocumentManager:
    """Manages document metadata and collections."""

    def add_document(
        self,
        document: ExtractedDocument,
        metadata: DocumentMetadata
    ) -> bool:
        """Add document with metadata to system."""

    def get_document_metadata(self, document_id: str) -> DocumentMetadata:
        """Retrieve document metadata."""

    def update_metadata(
        self,
        document_id: str,
        updates: dict
    ) -> bool:
        """Update document metadata fields."""

    def list_documents(
        self,
        filters: dict | None = None
    ) -> list[DocumentMetadata]:
        """List documents with optional filtering."""

    def delete_documents(self, document_ids: list[str]) -> bool:
        """Delete multiple documents."""
```

### 2. Collection Manager

**Location**: `src/document_manager/collections.py`

```python
class CollectionManager:
    """Manages document collections."""

    def create_collection(
        self,
        name: str,
        description: str | None = None
    ) -> Collection:
        """Create a new collection."""

    def add_documents_to_collection(
        self,
        collection_id: str,
        document_ids: list[str]
    ) -> bool:
        """Add documents to collection."""

    def remove_documents_from_collection(
        self,
        collection_id: str,
        document_ids: list[str]
    ) -> bool:
        """Remove documents from collection."""

    def get_collection(self, collection_id: str) -> Collection:
        """Get collection details."""

    def list_collections(self) -> list[Collection]:
        """List all collections."""

    def get_documents_in_collection(
        self,
        collection_id: str
    ) -> list[DocumentMetadata]:
        """Get all documents in a collection."""
```

### 3. Enhanced Vector Store

**Location**: `src/rag/vector_store.py` (enhanced)

```python
class VectorStoreManager:
    """Enhanced with multi-document support."""

    def search_multiple_documents(
        self,
        query_vector: list[float],
        document_ids: list[str],
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> dict[str, list[SearchResult]]:
        """Search across multiple documents.

        Returns:
            Dictionary mapping document_id to search results
        """

    def search_collection(
        self,
        query_vector: list[float],
        collection_id: str,
        top_k: int = 5,
    ) -> dict[str, list[SearchResult]]:
        """Search all documents in a collection."""
```

### 4. New Agent: Document Router Agent

**Location**: `src/agents/document_router.py`

```python
def document_router_agent(state: AgentState) -> AgentState:
    """Routes query to appropriate documents based on query content.

    Analyzes the query to determine:
    - Which documents are relevant
    - Query type (comparison, time-series, aggregation, ranking)
    - Optimal execution strategy

    Updates state with:
    - target_document_ids: list[str]
    - query_type: "comparison" | "time_series" | "aggregation" | "ranking"
    - execution_strategy: "parallel" | "sequential"
    """
```

**Example Routing Logic:**
- "Compare Apple and Microsoft" → Both Apple and Microsoft documents
- "How has Apple changed from 2021 to 2024?" → All Apple documents 2021-2024
- "What do all companies mention?" → All documents in collection

### 5. Enhanced Executor Agent

**Location**: `src/agents/executor.py` (enhanced)

```python
def multi_document_executor(
    state: AgentState,
    query_engine: RAGQueryEngine
) -> AgentState:
    """Execute queries across multiple documents.

    For each target document:
    1. Execute sub-query with document filter
    2. Track which document produced which result
    3. Maintain document attribution

    Updates state with:
    - document_results: dict[document_id, QueryResult]
    """
```

### 6. New Agent: Comparison Synthesizer

**Location**: `src/agents/comparison_synthesizer.py`

```python
def comparison_synthesis_agent(state: AgentState) -> AgentState:
    """Synthesizes comparative answers from multi-document results.

    Based on query_type:
    - "comparison": Side-by-side comparison
    - "time_series": Timeline/trend analysis
    - "aggregation": Summary statistics
    - "ranking": Ordered list with criteria

    Creates structured output:
    - Narrative synthesis
    - Structured comparison data (for tables/charts)
    - Per-document source attribution
    """
```

**Synthesis Strategies:**

**Comparison:**
```python
{
    "type": "comparison",
    "metric": "revenue_growth",
    "companies": [
        {"name": "Apple", "value": "8.7%", "source": "aapl-10k-2024.pdf:42"},
        {"name": "Microsoft", "value": "12.3%", "source": "msft-10k-2024.pdf:45"}
    ]
}
```

**Time-Series:**
```python
{
    "type": "time_series",
    "metric": "revenue",
    "company": "Apple",
    "data_points": [
        {"year": 2021, "value": "$365B", "source": "aapl-10k-2021.pdf:38"},
        {"year": 2022, "value": "$394B", "source": "aapl-10k-2022.pdf:40"},
        {"year": 2023, "value": "$383B", "source": "aapl-10k-2023.pdf:41"},
        {"year": 2024, "value": "$391B", "source": "aapl-10k-2024.pdf:42"}
    ]
}
```

## Storage Layer

### Document Metadata Storage

**Option 1: SQLite (Simple, Good for MVP)**
```sql
CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    company_name TEXT,
    year INTEGER,
    quarter TEXT,
    document_type TEXT,
    upload_date TIMESTAMP,
    page_count INTEGER,
    file_size_mb REAL,
    tags JSON
);

CREATE TABLE collections (
    collection_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_date TIMESTAMP,
    modified_date TIMESTAMP,
    is_system BOOLEAN
);

CREATE TABLE collection_documents (
    collection_id TEXT,
    document_id TEXT,
    added_date TIMESTAMP,
    PRIMARY KEY (collection_id, document_id),
    FOREIGN KEY (collection_id) REFERENCES collections(collection_id),
    FOREIGN KEY (document_id) REFERENCES documents(document_id)
);
```

**Location**: `data/metadata/documents.db`

### Vector Store Organization

**Qdrant Collections Strategy:**

**Option A: Single Collection with Metadata Filtering (Recommended)**
```python
# Store all documents in one collection
# Use payload filtering for multi-doc queries
{
    "collection": "financial_docs",
    "payload": {
        "document_id": "aapl-10k-2024",
        "company_name": "Apple",
        "year": 2024,
        "document_type": "10-K",
        "chunk_id": "chunk_123",
        "page_numbers": [42]
    }
}

# Query with filters
client.search(
    collection_name="financial_docs",
    query_vector=vector,
    query_filter={
        "must": [
            {"key": "document_id", "match": {"any": ["aapl-10k-2024", "msft-10k-2024"]}}
        ]
    }
)
```

**Pros**: Simple, efficient, easy to query across documents
**Cons**: All docs in one namespace

**Option B: Per-Document Collections**
```python
# Separate collection per document
collections = [
    "aapl-10k-2024",
    "msft-10k-2024",
    "googl-10k-2024"
]

# Query each collection separately
for collection in target_collections:
    results[collection] = client.search(
        collection_name=collection,
        query_vector=vector
    )
```

**Pros**: Isolation, easier to delete entire document
**Cons**: More complex queries, collection proliferation

**Recommendation**: Use Option A (single collection with metadata filtering)

## Enhanced Agent Workflow

### Updated LangGraph Flow

```python
def create_multi_doc_workflow(query_engine: RAGQueryEngine) -> CompiledStateGraph:
    """Create workflow with multi-document support."""

    workflow = StateGraph(AgentState)

    # Step 1: Classify query complexity
    workflow.add_node("router", query_router_agent)

    # Step 2: NEW - Route to appropriate documents
    workflow.add_node("document_router", document_router_agent)

    # Step 3: Decompose if complex
    workflow.add_node("decomposer", query_decomposer_agent)

    # Step 4: Execute across documents (enhanced)
    workflow.add_node("multi_doc_executor",
                     partial(multi_document_executor, query_engine=query_engine))

    # Step 5: Synthesize with comparison logic (new)
    workflow.add_node("comparison_synthesizer", comparison_synthesis_agent)

    # Routing logic
    workflow.add_conditional_edges(
        "router",
        route_query,
        {
            "simple_path": "document_router",  # Even simple queries need doc routing
            "complex_path": "document_router"
        }
    )

    workflow.add_conditional_edges(
        "document_router",
        route_by_complexity,
        {
            "simple": "multi_doc_executor",
            "complex": "decomposer"
        }
    )

    workflow.add_edge("decomposer", "multi_doc_executor")
    workflow.add_edge("multi_doc_executor", "comparison_synthesizer")
    workflow.add_edge("comparison_synthesizer", END)

    return workflow.compile()
```

## UI Components

### 1. Document Manager Component

**Location**: `src/ui/components/document_manager.py`

```python
class DocumentManagerComponent:
    """UI for managing documents and collections."""

    def render(self):
        """Render document management interface."""
        # Document list with metadata
        # Bulk operations (upload, delete)
        # Metadata editing
        # Collection management
```

### 2. Enhanced Chat Component

**Location**: `src/ui/components/chat.py` (enhanced)

```python
class ChatComponent:
    """Enhanced with multi-document support."""

    def render(self):
        # Collection selector
        # Document count indicator
        # Per-document source attribution in answers
        # Comparison visualizations (tables, timelines)
```

## Implementation Slices

### Slice 1: Document Metadata & Storage (Foundation)
**Estimated effort**: 2-3 days
- Document metadata model
- SQLite database schema
- DocumentManager service
- Basic CRUD operations
- Tests

**Deliverable**: Can store and retrieve document metadata

### Slice 2: Collections Management
**Estimated effort**: 2-3 days
- Collection model
- CollectionManager service
- System collections ("All Documents", "Recent")
- Collection CRUD operations
- Tests

**Deliverable**: Can create and manage collections

### Slice 3: Enhanced Vector Store & Multi-Doc Search
**Estimated effort**: 2-3 days
- Enhanced Qdrant payload with document metadata
- search_multiple_documents() method
- search_collection() method
- Document filtering logic
- Tests

**Deliverable**: Can search across multiple documents

### Slice 4: Document Router Agent
**Estimated effort**: 2-3 days
- Document router agent implementation
- Query-to-document mapping logic
- Query type classification (comparison, time-series, etc.)
- Integration with workflow
- Tests

**Deliverable**: Queries routed to appropriate documents

### Slice 5: Multi-Document Executor
**Estimated effort**: 2-3 days
- Enhanced executor for multi-doc queries
- Per-document result tracking
- Document attribution
- Tests

**Deliverable**: Can execute queries across multiple documents

### Slice 6: Comparison Synthesizer Agent
**Estimated effort**: 3-4 days
- Comparison synthesis agent
- Multiple synthesis strategies (comparison, time-series, ranking)
- Structured output generation
- Tests

**Deliverable**: Comparative answers with structured data

### Slice 7: UI - Document Manager
**Estimated effort**: 2-3 days
- Document list view
- Metadata display/editing
- Bulk operations
- Document filtering

**Deliverable**: UI for managing documents

### Slice 8: UI - Collections Manager
**Estimated effort**: 2-3 days
- Collection creation/editing
- Add/remove documents from collections
- Collection selector

**Deliverable**: UI for managing collections

### Slice 9: UI - Multi-Doc Chat Interface
**Estimated effort**: 2-3 days
- Collection selector in chat
- Document scope indicator
- Per-document source attribution
- Comparison visualizations (tables)

**Deliverable**: Complete multi-doc query experience

### Slice 10: Polish & Testing
**Estimated effort**: 2-3 days
- Integration tests for full workflow
- Performance optimization
- Error handling improvements
- Documentation

**Deliverable**: Production-ready Phase 3

## Testing Strategy

### Unit Tests
- Document metadata CRUD
- Collection management
- Multi-document search
- Document router agent
- Comparison synthesizer

### Integration Tests
- Full multi-doc query workflow
- Collection-based queries
- Cross-document comparison
- Time-series analysis

### Performance Tests
- Query 5 documents: <30s
- Query 20 documents: <60s
- Collection queries with 50+ documents

## Migration Strategy

### Phase 3.0 → Phase 3.1 (Backward Compatible)
1. Add document metadata to existing documents
2. Create "All Documents" system collection with existing docs
3. Enhance Qdrant payloads with metadata (re-index)
4. Deploy new UI components

**No Breaking Changes**: Existing single-doc queries continue to work

## Configuration

### New Settings

```python
# src/config/settings.py

# Multi-Document Settings
MAX_DOCUMENTS_PER_QUERY: int = 20
MAX_COLLECTION_SIZE: int = 100
ENABLE_AUTO_METADATA_EXTRACTION: bool = True

# Database
METADATA_DB_PATH: str = "data/metadata/documents.db"

# Performance
MULTI_DOC_QUERY_TIMEOUT: int = 60  # seconds
```

## Success Metrics

### Functional
- ✅ Can query across 5+ documents
- ✅ Comparison results clearly attribute sources
- ✅ Collections support 50+ documents
- ✅ Metadata extraction works for 80%+ of documents

### Performance
- ✅ 5-document query: <30s
- ✅ 20-document query: <60s
- ✅ Document upload with metadata: <5s per document

### Quality
- ✅ 95%+ test coverage for new components
- ✅ All linters passing (ruff, mypy)
- ✅ No performance regression on single-doc queries
