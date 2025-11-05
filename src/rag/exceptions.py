"""Custom exceptions for RAG operations."""


class RAGError(Exception):
    """Base exception for all RAG errors."""

    def __init__(self, message: str):
        """Initialize the exception with a message.

        Args:
            message: Error message describing what went wrong
        """
        self.message = message
        super().__init__(self.message)


class ChunkingError(RAGError):
    """Raised when errors occur during document chunking."""

    pass


class EmbeddingError(RAGError):
    """Raised when errors occur during embedding generation."""

    pass


class VectorStoreError(RAGError):
    """Raised when errors occur with Qdrant operations."""

    pass


class QueryError(RAGError):
    """Raised when errors occur during query processing."""

    pass
