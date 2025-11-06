"""Unit tests for EmbeddingGenerator."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.rag.embedder import EmbeddingGenerator
from src.rag.exceptions import EmbeddingError
from src.rag.models import DocumentChunk


class TestEmbeddingGenerator:
    """Test suite for EmbeddingGenerator."""

    @pytest.fixture
    def embedder(self) -> EmbeddingGenerator:
        """Create EmbeddingGenerator instance with test API key."""
        return EmbeddingGenerator(
            embedding_model="text-embedding-3-small", api_key="test-api-key"
        )

    @pytest.fixture
    def sample_chunk(self) -> DocumentChunk:
        """Create a single sample DocumentChunk for testing."""
        return DocumentChunk(
            content="Financial analysis is a critical component of investment decisions.",
            chunk_id=str(uuid4()),
            document_id=str(uuid4()),
            chunk_index=0,
            page_numbers=[1],
            char_start=0,
            char_end=67,
            token_count=12,
            embedding=None,
        )

    @pytest.fixture
    def sample_chunks(self) -> list[DocumentChunk]:
        """Create multiple sample DocumentChunks for batch testing."""
        doc_id = str(uuid4())
        texts = [
            "Financial analysis is a critical component of investment decisions.",
            "Revenue growth is often the first indicator analysts examine.",
            "Operating margins reveal efficiency in operations.",
            "Free cash flow demonstrates the company's ability to generate cash.",
            "Market volatility can significantly impact investment returns.",
            "Regulatory changes may affect industry dynamics.",
            "Competitive pressures require constant innovation.",
            "Strategic planning ensures long-term business sustainability.",
            "Customer satisfaction drives repeat business and loyalty.",
            "Digital transformation accelerates operational efficiency.",
        ]

        chunks = []
        for i, text in enumerate(texts):
            chunk = DocumentChunk(
                content=text,
                chunk_id=str(uuid4()),
                document_id=doc_id,
                chunk_index=i,
                page_numbers=[i // 3 + 1],  # Distribute across pages
                char_start=i * 100,
                char_end=i * 100 + len(text),
                token_count=len(text.split()),
                embedding=None,
            )
            chunks.append(chunk)

        return chunks

    @pytest.fixture
    def mock_embedding_response_single(self) -> Mock:
        """Create mock response for single embedding."""
        mock_response = Mock()
        mock_item = Mock()
        # OpenAI text-embedding-3-small returns 1536-dimensional vectors
        mock_item.embedding = [0.1] * 1536
        mock_response.data = [mock_item]
        return mock_response

    @pytest.fixture
    def mock_embedding_response_batch(self) -> Mock:
        """Create mock response for batch embeddings."""
        mock_response = Mock()
        mock_items = []
        for i in range(10):
            mock_item = Mock()
            # Each embedding is slightly different
            mock_item.embedding = [0.1 + i * 0.01] * 1536
            mock_items.append(mock_item)
        mock_response.data = mock_items
        return mock_response

    def test_initialization_success(self) -> None:
        """Test successful initialization with valid parameters."""
        embedder = EmbeddingGenerator(
            embedding_model="text-embedding-3-small", api_key="test-key"
        )

        assert embedder.embedding_model == "text-embedding-3-small"
        assert embedder.api_key == "test-key"
        assert embedder.batch_size == 100
        assert embedder.max_retries == 3

    def test_initialization_empty_model_raises_error(self) -> None:
        """Test that empty embedding_model raises ValueError."""
        with pytest.raises(ValueError, match="embedding_model cannot be empty"):
            EmbeddingGenerator(embedding_model="", api_key="test-key")

    def test_initialization_empty_api_key_raises_error(self) -> None:
        """Test that empty api_key raises ValueError."""
        with pytest.raises(ValueError, match="api_key cannot be empty"):
            EmbeddingGenerator(
                embedding_model="text-embedding-3-small", api_key=""
            )

    @patch("src.rag.embedder.embedding")
    def test_embed_single_chunk(
        self,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
        sample_chunk: DocumentChunk,
        mock_embedding_response_single: Mock,
    ) -> None:
        """Test embedding a single chunk with correct dimensions."""
        mock_embedding.return_value = mock_embedding_response_single

        chunks = embedder.embed_chunks([sample_chunk])

        # Verify embedding was called correctly
        mock_embedding.assert_called_once_with(
            model="text-embedding-3-small",
            input=[sample_chunk.content],
            api_key="test-api-key",
        )

        # Verify chunk was updated
        assert len(chunks) == 1
        assert chunks[0].embedding is not None
        assert len(chunks[0].embedding) == 1536, "Embedding should be 1536-dimensional"
        assert all(isinstance(x, float) for x in chunks[0].embedding)

    @patch("src.rag.embedder.embedding")
    def test_embed_batch_chunks(
        self,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
        sample_chunks: list[DocumentChunk],
        mock_embedding_response_batch: Mock,
    ) -> None:
        """Test batch embedding with 10 chunks."""
        mock_embedding.return_value = mock_embedding_response_batch

        chunks = embedder.embed_chunks(sample_chunks)

        # Verify embedding was called once (batch size = 100)
        mock_embedding.assert_called_once()

        # Verify all chunks were updated
        assert len(chunks) == 10
        for i, chunk in enumerate(chunks):
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 1536
            # Verify each chunk got the correct embedding
            assert chunk.embedding[0] == pytest.approx(0.1 + i * 0.01)

    @patch("src.rag.embedder.embedding")
    def test_embed_query(
        self,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
        mock_embedding_response_single: Mock,
    ) -> None:
        """Test embedding a single query string."""
        mock_embedding.return_value = mock_embedding_response_single

        query = "What are the key financial metrics for analysis?"
        embedding_vector = embedder.embed_query(query)

        # Verify embedding was called correctly
        mock_embedding.assert_called_once_with(
            model="text-embedding-3-small",
            input=[query],
            api_key="test-api-key",
        )

        # Verify embedding returned
        assert embedding_vector is not None
        assert len(embedding_vector) == 1536
        assert all(isinstance(x, float) for x in embedding_vector)

    def test_embed_empty_chunks_raises_error(
        self, embedder: EmbeddingGenerator
    ) -> None:
        """Test that empty chunks list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot embed empty list of chunks"):
            embedder.embed_chunks([])

    def test_embed_empty_query_raises_error(
        self, embedder: EmbeddingGenerator
    ) -> None:
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            embedder.embed_query("")

    def test_embed_whitespace_query_raises_error(
        self, embedder: EmbeddingGenerator
    ) -> None:
        """Test that whitespace-only query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            embedder.embed_query("   \n\t  ")

    @patch("src.rag.embedder.embedding")
    @patch("src.rag.embedder.time.sleep")  # Mock sleep to speed up tests
    def test_retry_logic_success_on_second_attempt(
        self,
        mock_sleep: Mock,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
        sample_chunk: DocumentChunk,
        mock_embedding_response_single: Mock,
    ) -> None:
        """Test retry logic succeeds on second attempt."""
        # First call fails, second succeeds
        mock_embedding.side_effect = [
            Exception("API Error: Rate limit exceeded"),
            mock_embedding_response_single,
        ]

        chunks = embedder.embed_chunks([sample_chunk])

        # Verify embedding was called twice
        assert mock_embedding.call_count == 2

        # Verify sleep was called once (with 1 second delay)
        mock_sleep.assert_called_once_with(1)

        # Verify chunk was successfully embedded
        assert chunks[0].embedding is not None
        assert len(chunks[0].embedding) == 1536

    @patch("src.rag.embedder.embedding")
    @patch("src.rag.embedder.time.sleep")
    def test_retry_logic_exhausted_raises_error(
        self,
        mock_sleep: Mock,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
        sample_chunk: DocumentChunk,
    ) -> None:
        """Test that retry logic raises EmbeddingError after max retries."""
        # All attempts fail
        mock_embedding.side_effect = Exception("API Error: Service unavailable")

        with pytest.raises(
            EmbeddingError, match="Failed to generate embeddings after 3 attempts"
        ):
            embedder.embed_chunks([sample_chunk])

        # Verify embedding was called 3 times (max_retries)
        assert mock_embedding.call_count == 3

        # Verify sleep was called 2 times (between attempts)
        assert mock_sleep.call_count == 2
        # Verify exponential backoff: 1s, 2s
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    @patch("src.rag.embedder.embedding")
    def test_api_error_raises_embedding_error(
        self,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
        sample_chunk: DocumentChunk,
    ) -> None:
        """Test that API errors are properly wrapped in EmbeddingError."""
        mock_embedding.side_effect = Exception("API authentication failed")

        with pytest.raises(EmbeddingError):
            embedder.embed_chunks([sample_chunk])

    @patch("src.rag.embedder.embedding")
    def test_invalid_response_missing_data_field(
        self,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
        sample_chunk: DocumentChunk,
    ) -> None:
        """Test handling of invalid response without data field."""
        mock_response = Mock(spec=[])  # Mock without 'data' attribute
        mock_embedding.return_value = mock_response

        with pytest.raises(EmbeddingError, match="missing 'data' field"):
            embedder.embed_chunks([sample_chunk])

    @patch("src.rag.embedder.embedding")
    def test_invalid_response_missing_embedding_field(
        self,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
        sample_chunk: DocumentChunk,
    ) -> None:
        """Test handling of invalid response without embedding field."""
        mock_response = Mock()
        mock_item = Mock(spec=[])  # Mock without 'embedding' attribute
        mock_response.data = [mock_item]
        mock_embedding.return_value = mock_response

        with pytest.raises(EmbeddingError, match="missing 'embedding' field"):
            embedder.embed_chunks([sample_chunk])

    @patch("src.rag.embedder.embedding")
    def test_invalid_response_empty_data(
        self,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
        sample_chunk: DocumentChunk,
    ) -> None:
        """Test handling of response with empty data list."""
        mock_response = Mock()
        mock_response.data = []  # Empty list
        mock_embedding.return_value = mock_response

        with pytest.raises(EmbeddingError, match="No embeddings returned from API"):
            embedder.embed_chunks([sample_chunk])

    @patch("src.rag.embedder.embedding")
    def test_batch_processing_large_dataset(
        self,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
    ) -> None:
        """Test batch processing splits large datasets correctly."""
        # Create 150 chunks (should split into 2 batches)
        doc_id = str(uuid4())
        chunks = []
        for i in range(150):
            chunk = DocumentChunk(
                content=f"Chunk {i} content",
                chunk_id=str(uuid4()),
                document_id=doc_id,
                chunk_index=i,
                page_numbers=[1],
                char_start=i * 20,
                char_end=i * 20 + 15,
                token_count=3,
                embedding=None,
            )
            chunks.append(chunk)

        # Create mock responses for 2 batches
        def create_batch_response(size: int) -> Mock:
            mock_response = Mock()
            mock_items = []
            for i in range(size):
                mock_item = Mock()
                mock_item.embedding = [0.2] * 1536
                mock_items.append(mock_item)
            mock_response.data = mock_items
            return mock_response

        # First batch: 100 chunks, second batch: 50 chunks
        mock_embedding.side_effect = [
            create_batch_response(100),
            create_batch_response(50),
        ]

        result = embedder.embed_chunks(chunks)

        # Verify embedding was called twice (2 batches)
        assert mock_embedding.call_count == 2

        # Verify first call had 100 inputs
        first_call_args = mock_embedding.call_args_list[0]
        assert len(first_call_args.kwargs["input"]) == 100

        # Verify second call had 50 inputs
        second_call_args = mock_embedding.call_args_list[1]
        assert len(second_call_args.kwargs["input"]) == 50

        # Verify all chunks were embedded
        assert len(result) == 150
        assert all(chunk.embedding is not None for chunk in result)

    @patch("src.rag.embedder.embedding")
    def test_embed_chunks_preserves_chunk_order(
        self,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
        sample_chunks: list[DocumentChunk],
        mock_embedding_response_batch: Mock,
    ) -> None:
        """Test that chunk order is preserved after embedding."""
        mock_embedding.return_value = mock_embedding_response_batch

        original_ids = [chunk.chunk_id for chunk in sample_chunks]
        original_indices = [chunk.chunk_index for chunk in sample_chunks]

        result = embedder.embed_chunks(sample_chunks)

        result_ids = [chunk.chunk_id for chunk in result]
        result_indices = [chunk.chunk_index for chunk in result]

        assert result_ids == original_ids, "Chunk order should be preserved"
        assert result_indices == original_indices, "Chunk indices should be preserved"

    @patch("src.rag.embedder.embedding")
    def test_embed_chunks_returns_same_list(
        self,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
        sample_chunks: list[DocumentChunk],
        mock_embedding_response_batch: Mock,
    ) -> None:
        """Test that embed_chunks modifies and returns the same list."""
        mock_embedding.return_value = mock_embedding_response_batch

        # Store original object references
        original_chunk_objects = [id(chunk) for chunk in sample_chunks]

        result = embedder.embed_chunks(sample_chunks)

        # Verify same objects were returned (modified in place)
        result_chunk_objects = [id(chunk) for chunk in result]
        assert original_chunk_objects == result_chunk_objects

        # Verify same list object
        assert id(result) == id(sample_chunks)

    @patch("src.rag.embedder.embedding")
    def test_query_embedding_error_handling(
        self,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
    ) -> None:
        """Test error handling in query embedding."""
        mock_embedding.side_effect = Exception("Network timeout")

        with pytest.raises(EmbeddingError):
            embedder.embed_query("What is financial analysis?")

    @patch("src.rag.embedder.embedding")
    def test_custom_batch_size_configuration(
        self,
        mock_embedding: Mock,
    ) -> None:
        """Test that batch size can be customized."""
        embedder = EmbeddingGenerator(
            embedding_model="text-embedding-3-small", api_key="test-key"
        )
        embedder.batch_size = 5  # Set small batch size

        # Create 12 chunks (should split into 3 batches: 5, 5, 2)
        doc_id = str(uuid4())
        chunks = []
        for i in range(12):
            chunk = DocumentChunk(
                content=f"Content {i}",
                chunk_id=str(uuid4()),
                document_id=doc_id,
                chunk_index=i,
                page_numbers=[1],
                char_start=i * 10,
                char_end=i * 10 + 9,
                token_count=2,
                embedding=None,
            )
            chunks.append(chunk)

        # Create mock responses
        def create_batch_response(size: int) -> Mock:
            mock_response = Mock()
            mock_items = []
            for i in range(size):
                mock_item = Mock()
                mock_item.embedding = [0.3] * 1536
                mock_items.append(mock_item)
            mock_response.data = mock_items
            return mock_response

        mock_embedding.side_effect = [
            create_batch_response(5),
            create_batch_response(5),
            create_batch_response(2),
        ]

        result = embedder.embed_chunks(chunks)

        # Verify embedding was called 3 times
        assert mock_embedding.call_count == 3

        # Verify all chunks were embedded
        assert len(result) == 12
        assert all(chunk.embedding is not None for chunk in result)

    @patch("src.rag.embedder.embedding")
    def test_embedding_dimensions_validation(
        self,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
        sample_chunk: DocumentChunk,
    ) -> None:
        """Test that embeddings have correct dimensions (1536)."""
        mock_response = Mock()
        mock_item = Mock()
        mock_item.embedding = [0.1] * 1536
        mock_response.data = [mock_item]
        mock_embedding.return_value = mock_response

        chunks = embedder.embed_chunks([sample_chunk])

        assert len(chunks[0].embedding) == 1536

    @patch("src.rag.embedder.embedding")
    def test_embed_query_with_special_characters(
        self,
        mock_embedding: Mock,
        embedder: EmbeddingGenerator,
        mock_embedding_response_single: Mock,
    ) -> None:
        """Test embedding query with special characters."""
        mock_embedding.return_value = mock_embedding_response_single

        query = "What's the ROI? How does it compare to P/E ratios?"
        embedding = embedder.embed_query(query)

        # Verify embedding was created
        assert embedding is not None
        assert len(embedding) == 1536

        # Verify the query was passed correctly
        call_args = mock_embedding.call_args
        assert call_args.kwargs["input"] == [query]
