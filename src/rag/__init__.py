"""RAG (Retrieval-Augmented Generation) module for document querying."""

from src.rag.embedder import EmbeddingGenerator
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
from src.rag.service import RAGService

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
    # Components
    "EmbeddingGenerator",
    "RAGService",
]
