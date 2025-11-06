"""Unit tests for VectorStoreManager."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.rag.exceptions import VectorStoreError
from src.rag.models import DocumentChunk
from src.rag.vector_store import VectorStoreManager


class TestVectorStoreManager:
    """Test suite for VectorStoreManager."""

    @pytest.fixture
    def mock_qdrant_client(self) -> Mock:
        """Create a mocked QdrantClient."""
        mock_client = Mock()

        # Mock get_collections to return empty list by default
        mock_collections_response = Mock()
        mock_collections_response.collections = []
        mock_client.get_collections.return_value = mock_collections_response

        # Mock create_collection to succeed by default
        mock_client.create_collection.return_value = None

        # Mock upsert to succeed by default
        mock_client.upsert.return_value = None

        # Mock search to return empty list by default
        mock_client.search.return_value = []

        # Mock delete to succeed by default
        mock_client.delete.return_value = None

        return mock_client

    @pytest.fixture
    def vector_store_manager(self, mock_qdrant_client: Mock) -> VectorStoreManager:
        """Create VectorStoreManager with mocked QdrantClient."""
        with patch("src.rag.vector_store.QdrantClient") as mock_qdrant_class:
            mock_qdrant_class.return_value = mock_qdrant_client
            manager = VectorStoreManager(
                host="localhost",
                port=6333,
                collection_name="test_collection"
            )
            return manager

    @pytest.fixture
    def sample_chunks_with_embeddings(self) -> list[DocumentChunk]:
        """Create sample DocumentChunks with embeddings for testing."""
        doc_id = str(uuid4())
        chunks = []

        for i in range(5):
            chunk = DocumentChunk(
                content=f"This is test content for chunk {i}.",
                chunk_id=str(uuid4()),
                document_id=doc_id,
                chunk_index=i,
                page_numbers=[i // 2 + 1],
                char_start=i * 50,
                char_end=(i + 1) * 50,
                token_count=10,
                embedding=[0.1 + i * 0.01] * 1536  # 1536-dimensional embeddings
            )
            chunks.append(chunk)

        return chunks

    @pytest.fixture
    def sample_chunk_no_embedding(self) -> DocumentChunk:
        """Create a sample DocumentChunk without embedding."""
        return DocumentChunk(
            content="This is test content without embedding.",
            chunk_id=str(uuid4()),
            document_id=str(uuid4()),
            chunk_index=0,
            page_numbers=[1],
            char_start=0,
            char_end=40,
            token_count=7,
            embedding=None
        )

    def test_initialization_success(self, mock_qdrant_client: Mock) -> None:
        """Test successful initialization and connection."""
        with patch("src.rag.vector_store.QdrantClient") as mock_qdrant_class:
            mock_qdrant_class.return_value = mock_qdrant_client

            manager = VectorStoreManager(
                host="localhost",
                port=6333,
                collection_name="test_collection"
            )

            # Verify attributes
            assert manager.host == "localhost"
            assert manager.port == 6333
            assert manager.collection_name == "test_collection"
            assert manager.client == mock_qdrant_client

            # Verify connection test was performed
            mock_qdrant_client.get_collections.assert_called()

    def test_initialization_connection_failure(self) -> None:
        """Test initialization failure when Qdrant is unavailable."""
        with patch("src.rag.vector_store.QdrantClient") as mock_qdrant_class:
            mock_client = Mock()
            mock_client.get_collections.side_effect = Exception("Connection refused")
            mock_qdrant_class.return_value = mock_client

            with pytest.raises(VectorStoreError, match="Failed to connect to Qdrant"):
                VectorStoreManager(
                    host="localhost",
                    port=6333,
                    collection_name="test_collection"
                )

    def test_ensure_collection_exists_creates_new(self, mock_qdrant_client: Mock) -> None:
        """Test that collection is created if it doesn't exist."""
        # Mock get_collections to return empty list (no existing collections)
        mock_collections_response = Mock()
        mock_collections_response.collections = []
        mock_qdrant_client.get_collections.return_value = mock_collections_response

        with patch("src.rag.vector_store.QdrantClient") as mock_qdrant_class:
            mock_qdrant_class.return_value = mock_qdrant_client

            VectorStoreManager(
                host="localhost",
                port=6333,
                collection_name="test_collection"
            )

            # Verify create_collection was called
            mock_qdrant_client.create_collection.assert_called_once()
            call_args = mock_qdrant_client.create_collection.call_args
            assert call_args.kwargs["collection_name"] == "test_collection"

    def test_ensure_collection_exists_already_exists(self, mock_qdrant_client: Mock) -> None:
        """Test that collection is not created if it already exists."""
        # Mock get_collections to return existing collection
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_collections_response = Mock()
        mock_collections_response.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections_response

        with patch("src.rag.vector_store.QdrantClient") as mock_qdrant_class:
            mock_qdrant_class.return_value = mock_qdrant_client

            VectorStoreManager(
                host="localhost",
                port=6333,
                collection_name="test_collection"
            )

            # Verify create_collection was NOT called
            mock_qdrant_client.create_collection.assert_not_called()

    def test_ensure_collection_creation_failure(self, mock_qdrant_client: Mock) -> None:
        """Test error handling when collection creation fails."""
        mock_qdrant_client.create_collection.side_effect = Exception("Permission denied")

        with patch("src.rag.vector_store.QdrantClient") as mock_qdrant_class:
            mock_qdrant_class.return_value = mock_qdrant_client

            with pytest.raises(VectorStoreError, match="Failed to ensure collection exists"):
                VectorStoreManager(
                    host="localhost",
                    port=6333,
                    collection_name="test_collection"
                )

    def test_upsert_chunks_success(
        self,
        vector_store_manager: VectorStoreManager,
        sample_chunks_with_embeddings: list[DocumentChunk]
    ) -> None:
        """Test successful upserting of chunks."""
        count = vector_store_manager.upsert_chunks(sample_chunks_with_embeddings)

        # Verify return count
        assert count == 5

        # Verify upsert was called
        vector_store_manager.client.upsert.assert_called_once()

        # Verify points were created correctly
        call_args = vector_store_manager.client.upsert.call_args
        assert call_args.kwargs["collection_name"] == "test_collection"
        points = call_args.kwargs["points"]
        assert len(points) == 5

        # Verify first point structure
        first_point = points[0]
        assert first_point.id == sample_chunks_with_embeddings[0].chunk_id
        assert first_point.vector == sample_chunks_with_embeddings[0].embedding
        assert first_point.payload["document_id"] == sample_chunks_with_embeddings[0].document_id
        assert first_point.payload["content"] == sample_chunks_with_embeddings[0].content
        assert first_point.payload["chunk_index"] == 0
        assert first_point.payload["page_numbers"] == [1]
        assert first_point.payload["token_count"] == 10

    def test_upsert_empty_chunks_list(
        self,
        vector_store_manager: VectorStoreManager
    ) -> None:
        """Test upserting empty list returns 0."""
        count = vector_store_manager.upsert_chunks([])

        # Should return 0 without calling upsert
        assert count == 0
        vector_store_manager.client.upsert.assert_not_called()

    def test_upsert_chunks_without_embeddings_raises_error(
        self,
        vector_store_manager: VectorStoreManager,
        sample_chunk_no_embedding: DocumentChunk
    ) -> None:
        """Test that upserting chunks without embeddings raises error."""
        with pytest.raises(VectorStoreError, match="has no embedding"):
            vector_store_manager.upsert_chunks([sample_chunk_no_embedding])

    def test_upsert_chunks_mixed_embeddings_raises_error(
        self,
        vector_store_manager: VectorStoreManager,
        sample_chunks_with_embeddings: list[DocumentChunk],
        sample_chunk_no_embedding: DocumentChunk
    ) -> None:
        """Test that upserting mix of chunks with/without embeddings raises error."""
        # Add chunk without embedding to the list
        chunks = sample_chunks_with_embeddings + [sample_chunk_no_embedding]

        with pytest.raises(VectorStoreError, match="has no embedding"):
            vector_store_manager.upsert_chunks(chunks)

    def test_upsert_chunks_qdrant_failure(
        self,
        vector_store_manager: VectorStoreManager,
        sample_chunks_with_embeddings: list[DocumentChunk]
    ) -> None:
        """Test error handling when Qdrant upsert fails."""
        vector_store_manager.client.upsert.side_effect = Exception("Network timeout")

        with pytest.raises(VectorStoreError, match="Failed to upsert chunks"):
            vector_store_manager.upsert_chunks(sample_chunks_with_embeddings)

    def test_search_success(
        self,
        vector_store_manager: VectorStoreManager
    ) -> None:
        """Test successful search operation."""
        # Create mock search results
        mock_result_1 = Mock()
        mock_result_1.id = "chunk_id_1"
        mock_result_1.score = 0.95
        mock_result_1.payload = {
            "document_id": "doc_1",
            "content": "This is the first matching chunk.",
            "page_numbers": [1, 2]
        }

        mock_result_2 = Mock()
        mock_result_2.id = "chunk_id_2"
        mock_result_2.score = 0.85
        mock_result_2.payload = {
            "document_id": "doc_1",
            "content": "This is the second matching chunk.",
            "page_numbers": [3]
        }

        vector_store_manager.client.search.return_value = [mock_result_1, mock_result_2]

        # Perform search
        query_embedding = [0.2] * 1536
        results = vector_store_manager.search(query_embedding, top_k=5, min_score=0.7)

        # Verify search was called correctly
        vector_store_manager.client.search.assert_called_once()
        call_args = vector_store_manager.client.search.call_args
        assert call_args.kwargs["collection_name"] == "test_collection"
        assert call_args.kwargs["query_vector"] == query_embedding
        assert call_args.kwargs["limit"] == 5
        assert call_args.kwargs["score_threshold"] == 0.7

        # Verify results
        assert len(results) == 2
        assert results[0]["chunk_id"] == "chunk_id_1"
        assert results[0]["score"] == 0.95
        assert results[0]["document_id"] == "doc_1"
        assert results[0]["content"] == "This is the first matching chunk."
        assert results[0]["page_numbers"] == [1, 2]

        assert results[1]["chunk_id"] == "chunk_id_2"
        assert results[1]["score"] == 0.85

    def test_search_no_results(
        self,
        vector_store_manager: VectorStoreManager
    ) -> None:
        """Test search returning no results."""
        vector_store_manager.client.search.return_value = []

        query_embedding = [0.3] * 1536
        results = vector_store_manager.search(query_embedding, top_k=5)

        # Should return empty list
        assert results == []

    def test_search_with_min_score_filtering(
        self,
        vector_store_manager: VectorStoreManager
    ) -> None:
        """Test search with min_score parameter."""
        # Create mock result with high score
        mock_result = Mock()
        mock_result.id = "chunk_id_1"
        mock_result.score = 0.95
        mock_result.payload = {
            "document_id": "doc_1",
            "content": "High scoring chunk.",
            "page_numbers": [1]
        }

        vector_store_manager.client.search.return_value = [mock_result]

        # Search with min_score filter
        query_embedding = [0.4] * 1536
        results = vector_store_manager.search(query_embedding, top_k=10, min_score=0.9)

        # Verify min_score was passed to Qdrant
        call_args = vector_store_manager.client.search.call_args
        assert call_args.kwargs["score_threshold"] == 0.9

        # Should return high-scoring result
        assert len(results) == 1
        assert results[0]["score"] == 0.95

    def test_search_qdrant_failure(
        self,
        vector_store_manager: VectorStoreManager
    ) -> None:
        """Test error handling when Qdrant search fails."""
        vector_store_manager.client.search.side_effect = Exception("Index not ready")

        query_embedding = [0.5] * 1536

        with pytest.raises(VectorStoreError, match="Failed to search vector store"):
            vector_store_manager.search(query_embedding)

    def test_search_default_parameters(
        self,
        vector_store_manager: VectorStoreManager
    ) -> None:
        """Test search with default parameters."""
        vector_store_manager.client.search.return_value = []

        query_embedding = [0.6] * 1536
        vector_store_manager.search(query_embedding)

        # Verify default parameters
        call_args = vector_store_manager.client.search.call_args
        assert call_args.kwargs["limit"] == 5  # default top_k
        assert call_args.kwargs["score_threshold"] == 0.0  # default min_score

    def test_delete_document_success(
        self,
        vector_store_manager: VectorStoreManager
    ) -> None:
        """Test successful document deletion."""
        document_id = str(uuid4())
        result = vector_store_manager.delete_document(document_id)

        # Should return True
        assert result is True

        # Verify delete was called
        vector_store_manager.client.delete.assert_called_once()
        call_args = vector_store_manager.client.delete.call_args
        assert call_args.kwargs["collection_name"] == "test_collection"

    def test_delete_document_qdrant_failure(
        self,
        vector_store_manager: VectorStoreManager
    ) -> None:
        """Test error handling when Qdrant delete fails."""
        vector_store_manager.client.delete.side_effect = Exception("Delete failed")

        document_id = str(uuid4())

        with pytest.raises(VectorStoreError, match="Failed to delete document"):
            vector_store_manager.delete_document(document_id)

    def test_integration_upsert_and_search(
        self,
        vector_store_manager: VectorStoreManager,
        sample_chunks_with_embeddings: list[DocumentChunk]
    ) -> None:
        """Test integration of upsert followed by search."""
        # First, upsert chunks
        count = vector_store_manager.upsert_chunks(sample_chunks_with_embeddings)
        assert count == 5

        # Create mock search results using the upserted chunks
        mock_result = Mock()
        mock_result.id = sample_chunks_with_embeddings[0].chunk_id
        mock_result.score = 0.92
        mock_result.payload = {
            "document_id": sample_chunks_with_embeddings[0].document_id,
            "content": sample_chunks_with_embeddings[0].content,
            "page_numbers": sample_chunks_with_embeddings[0].page_numbers
        }

        vector_store_manager.client.search.return_value = [mock_result]

        # Search for similar chunks
        query_embedding = [0.1] * 1536
        results = vector_store_manager.search(query_embedding, top_k=1)

        # Verify we got results
        assert len(results) == 1
        assert results[0]["chunk_id"] == sample_chunks_with_embeddings[0].chunk_id
        assert results[0]["score"] == 0.92

    def test_integration_upsert_and_delete(
        self,
        vector_store_manager: VectorStoreManager,
        sample_chunks_with_embeddings: list[DocumentChunk]
    ) -> None:
        """Test integration of upsert followed by delete."""
        # First, upsert chunks
        count = vector_store_manager.upsert_chunks(sample_chunks_with_embeddings)
        assert count == 5

        # Delete the document
        document_id = sample_chunks_with_embeddings[0].document_id
        result = vector_store_manager.delete_document(document_id)
        assert result is True

        # Verify both operations were called
        vector_store_manager.client.upsert.assert_called_once()
        vector_store_manager.client.delete.assert_called_once()

    def test_upsert_preserves_chunk_order(
        self,
        vector_store_manager: VectorStoreManager,
        sample_chunks_with_embeddings: list[DocumentChunk]
    ) -> None:
        """Test that upsert maintains chunk order."""
        original_ids = [chunk.chunk_id for chunk in sample_chunks_with_embeddings]
        original_indices = [chunk.chunk_index for chunk in sample_chunks_with_embeddings]

        vector_store_manager.upsert_chunks(sample_chunks_with_embeddings)

        # Verify points were created in same order
        call_args = vector_store_manager.client.upsert.call_args
        points = call_args.kwargs["points"]

        point_ids = [point.id for point in points]
        point_indices = [point.payload["chunk_index"] for point in points]

        assert point_ids == original_ids
        assert point_indices == original_indices

    def test_search_result_structure(
        self,
        vector_store_manager: VectorStoreManager
    ) -> None:
        """Test that search results have correct structure."""
        mock_result = Mock()
        mock_result.id = "test_id"
        mock_result.score = 0.88
        mock_result.payload = {
            "document_id": "doc_123",
            "content": "Test content",
            "page_numbers": [1, 2, 3]
        }

        vector_store_manager.client.search.return_value = [mock_result]

        query_embedding = [0.7] * 1536
        results = vector_store_manager.search(query_embedding)

        # Verify result structure
        assert len(results) == 1
        result = results[0]

        # Check all required fields
        assert "chunk_id" in result
        assert "score" in result
        assert "document_id" in result
        assert "content" in result
        assert "page_numbers" in result

        # Verify values
        assert result["chunk_id"] == "test_id"
        assert result["score"] == 0.88
        assert result["document_id"] == "doc_123"
        assert result["content"] == "Test content"
        assert result["page_numbers"] == [1, 2, 3]

    def test_upsert_large_batch(
        self,
        vector_store_manager: VectorStoreManager
    ) -> None:
        """Test upserting a large batch of chunks."""
        # Create 100 chunks
        doc_id = str(uuid4())
        chunks = []

        for i in range(100):
            chunk = DocumentChunk(
                content=f"Content {i}",
                chunk_id=str(uuid4()),
                document_id=doc_id,
                chunk_index=i,
                page_numbers=[i // 10 + 1],
                char_start=i * 20,
                char_end=(i + 1) * 20,
                token_count=5,
                embedding=[0.1] * 1536
            )
            chunks.append(chunk)

        count = vector_store_manager.upsert_chunks(chunks)

        # Verify all chunks were upserted
        assert count == 100

        # Verify upsert was called with all points
        call_args = vector_store_manager.client.upsert.call_args
        points = call_args.kwargs["points"]
        assert len(points) == 100

    def test_embedding_dimensions_validation(
        self,
        vector_store_manager: VectorStoreManager
    ) -> None:
        """Test that embeddings are 1536-dimensional."""
        # Create chunk with correct embedding size
        chunk = DocumentChunk(
            content="Test content",
            chunk_id=str(uuid4()),
            document_id=str(uuid4()),
            chunk_index=0,
            page_numbers=[1],
            char_start=0,
            char_end=12,
            token_count=2,
            embedding=[0.1] * 1536
        )

        count = vector_store_manager.upsert_chunks([chunk])
        assert count == 1

        # Verify the embedding was passed correctly
        call_args = vector_store_manager.client.upsert.call_args
        points = call_args.kwargs["points"]
        assert len(points[0].vector) == 1536

    def test_multiple_documents_same_collection(
        self,
        vector_store_manager: VectorStoreManager
    ) -> None:
        """Test storing chunks from multiple documents in same collection."""
        doc_id_1 = str(uuid4())
        doc_id_2 = str(uuid4())

        # Create chunks for first document
        chunks_1 = []
        for i in range(3):
            chunk = DocumentChunk(
                content=f"Doc 1 content {i}",
                chunk_id=str(uuid4()),
                document_id=doc_id_1,
                chunk_index=i,
                page_numbers=[1],
                char_start=i * 20,
                char_end=(i + 1) * 20,
                token_count=4,
                embedding=[0.1] * 1536
            )
            chunks_1.append(chunk)

        # Create chunks for second document
        chunks_2 = []
        for i in range(2):
            chunk = DocumentChunk(
                content=f"Doc 2 content {i}",
                chunk_id=str(uuid4()),
                document_id=doc_id_2,
                chunk_index=i,
                page_numbers=[1],
                char_start=i * 20,
                char_end=(i + 1) * 20,
                token_count=4,
                embedding=[0.2] * 1536
            )
            chunks_2.append(chunk)

        # Upsert both sets
        count_1 = vector_store_manager.upsert_chunks(chunks_1)
        count_2 = vector_store_manager.upsert_chunks(chunks_2)

        assert count_1 == 3
        assert count_2 == 2

        # Verify both upserts used same collection
        assert vector_store_manager.client.upsert.call_count == 2
        for call in vector_store_manager.client.upsert.call_args_list:
            assert call.kwargs["collection_name"] == "test_collection"
