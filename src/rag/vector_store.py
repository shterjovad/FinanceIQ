"""Vector store manager for Qdrant operations."""

import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.rag.exceptions import VectorStoreError
from src.rag.models import DocumentChunk

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manages interactions with Qdrant vector database for document storage and retrieval.

    This class provides methods to:
    - Store document chunks with embeddings in Qdrant
    - Search for similar chunks using vector similarity
    - Delete documents and their associated chunks
    - Manage collection lifecycle

    Attributes:
        host: Qdrant server hostname
        port: Qdrant server port
        collection_name: Name of the Qdrant collection to use
        client: QdrantClient instance for database operations
    """

    def __init__(self, host: str, port: int, collection_name: str) -> None:
        """Initialize VectorStoreManager and connect to Qdrant.

        Validates connection to Qdrant and ensures the collection exists with
        proper configuration (1536 dimensions, cosine distance).

        Args:
            host: Qdrant server hostname (e.g., 'localhost')
            port: Qdrant server port (e.g., 6333)
            collection_name: Name of the collection to use

        Raises:
            VectorStoreError: If connection to Qdrant fails or collection cannot be created
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name

        try:
            self.client = QdrantClient(host=host, port=port)
            # Test connection
            self.client.get_collections()
            logger.info(f"Connected to Qdrant at {host}:{port}")
        except Exception as e:
            error_msg = (
                f"Failed to connect to Qdrant at {host}:{port}: {e}\n"
                f"Start Qdrant with: docker compose up -d"
            )
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e

        # Ensure collection exists
        self._ensure_collection_exists()

    def _ensure_collection_exists(self) -> None:
        """Create collection if it doesn't exist with proper configuration.

        Creates a collection configured for 1536-dimensional embeddings with
        cosine distance metric, suitable for OpenAI embeddings.

        Raises:
            VectorStoreError: If collection creation fails
        """
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # OpenAI embedding dimension
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection already exists: {self.collection_name}")

        except Exception as e:
            error_msg = f"Failed to ensure collection exists: {e}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e

    def upsert_chunks(self, chunks: list[DocumentChunk]) -> int:
        """Insert or update document chunks in the vector store.

        Converts DocumentChunk objects to Qdrant points and stores them with
        their embeddings and metadata. If chunks with the same IDs exist,
        they will be updated.

        Args:
            chunks: List of DocumentChunk objects to store. Each chunk must
                   have an embedding (embedding field must not be None).

        Returns:
            Number of chunks successfully inserted/updated

        Raises:
            VectorStoreError: If any chunk lacks an embedding or upsert operation fails
        """
        if not chunks:
            logger.info("No chunks to upsert")
            return 0

        # Validate all chunks have embeddings
        for chunk in chunks:
            if chunk.embedding is None:
                error_msg = f"Chunk {chunk.chunk_id} has no embedding"
                logger.error(error_msg)
                raise VectorStoreError(error_msg)

        try:
            # Convert chunks to Qdrant points
            points: list[PointStruct] = []
            for chunk in chunks:
                point = PointStruct(
                    id=chunk.chunk_id,
                    vector=chunk.embedding,  # type: ignore[arg-type]  # Already validated above
                    payload={
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index,
                        "page_numbers": chunk.page_numbers,
                        "content": chunk.content,
                        "token_count": chunk.token_count,
                    },
                )
                points.append(point)

            # Upsert points into collection
            self.client.upsert(collection_name=self.collection_name, points=points)

            logger.info(f"Upserted {len(points)} chunks to collection {self.collection_name}")
            return len(points)

        except VectorStoreError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            error_msg = f"Failed to upsert chunks: {e}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e

    def search(
        self, query_embedding: list[float], top_k: int = 5, min_score: float = 0.0
    ) -> list[dict[str, Any]]:
        """Search for similar document chunks using vector similarity.

        Performs a vector similarity search using cosine distance and returns
        the most similar chunks with their metadata and relevance scores.

        Args:
            query_embedding: 1536-dimensional query vector
            top_k: Maximum number of results to return (default: 5)
            min_score: Minimum similarity score threshold (default: 0.0)

        Returns:
            List of search results, each containing:
                - chunk_id: Unique identifier of the chunk
                - score: Cosine similarity score (0-1, higher is better)
                - document_id: ID of the source document
                - content: Text content of the chunk
                - page_numbers: List of page numbers the chunk spans

        Raises:
            VectorStoreError: If search operation fails
        """
        try:
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=min_score,
            )

            results: list[dict[str, Any]] = []
            for result in search_results:
                results.append(
                    {
                        "chunk_id": result.id,
                        "score": result.score,
                        "document_id": result.payload["document_id"],  # type: ignore[index]
                        "content": result.payload["content"],  # type: ignore[index]
                        "page_numbers": result.payload["page_numbers"],  # type: ignore[index]
                    }
                )

            logger.info(
                f"Search returned {len(results)} results (top_k={top_k}, min_score={min_score})"
            )
            return results

        except Exception as e:
            error_msg = f"Failed to search vector store: {e}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e

    def delete_document(self, document_id: str) -> bool:
        """Delete all chunks associated with a document.

        Removes all vector points that belong to the specified document from
        the collection. This is useful for document updates or deletions.

        Args:
            document_id: ID of the document whose chunks should be deleted

        Returns:
            True if deletion was successful, False otherwise

        Raises:
            VectorStoreError: If delete operation fails
        """
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            # Delete all points matching the document_id
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
            )

            logger.info(f"Deleted all chunks for document: {document_id}")
            return True

        except Exception as e:
            error_msg = f"Failed to delete document {document_id}: {e}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e
