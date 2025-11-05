"""RAG (Retrieval-Augmented Generation) module for document querying."""

from src.rag.exceptions import (
    ChunkingError,
    EmbeddingError,
    QueryError,
    RAGError,
    VectorStoreError,
)
from src.rag.models import (
    ChatMessage,
    DocumentChunk,
    QueryResult,
    RAGResult,
    SourceCitation,
)

__all__ = [
    # Exceptions
    "RAGError",
    "ChunkingError",
    "EmbeddingError",
    "VectorStoreError",
    "QueryError",
    # Models
    "DocumentChunk",
    "QueryResult",
    "SourceCitation",
    "RAGResult",
    "ChatMessage",
]
