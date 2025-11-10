"""Integration tests for RAGService."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.pdf_processor.models import DocumentMetadata, ExtractedDocument
from src.rag.chunker import DocumentChunker
from src.rag.embedder import EmbeddingGenerator
from src.rag.models import QueryResult, RAGResult
from src.rag.query_engine import RAGQueryEngine
from src.rag.service import RAGService
from src.rag.vector_store import VectorStoreManager


class TestRAGService:
    """Integration test suite for RAGService.

    These tests verify RAGService works correctly with all its dependencies.
    They use real Qdrant and real components but mock LLM/embedding API calls.
    """

    @pytest.fixture
    def test_collection_name(self) -> str:
        """Generate unique collection name for test isolation."""
        return f"test_rag_service_{uuid4().hex[:8]}"

    @pytest.fixture
    def sample_document(self) -> ExtractedDocument:
        """Create a realistic sample extracted document for testing."""
        text = """Financial Analysis Report Q4 2023

Executive Summary

The company demonstrated strong performance in Q4 2023 with revenue reaching $10 million, representing a 25% year-over-year increase. Operating margins improved significantly due to cost optimization initiatives.

Revenue Analysis

Total revenue for Q4 2023 was $10 million, up from $8 million in Q4 2022. This growth was driven primarily by increased sales in the technology sector and expansion into new markets.

Operating Expenses

Operating expenses decreased by 15% compared to the previous quarter, reflecting the success of our efficiency improvement program. Key savings were achieved in marketing and administrative costs.

Profitability

Net profit margin improved from 12% to 18% year-over-year. The company generated $1.8 million in net profit, demonstrating strong operational efficiency and market positioning.

Cash Flow

Free cash flow remained positive at $2.5 million, providing ample resources for future investments and strategic initiatives. The company maintains a strong balance sheet with minimal debt.

Market Outlook

Looking ahead, we expect continued growth in 2024 driven by new product launches and market expansion. Management remains optimistic about long-term prospects despite short-term market volatility.

Risk Factors

Key risks include competitive pressures, regulatory changes, and macroeconomic conditions. The company has implemented comprehensive risk management strategies to mitigate these challenges."""

        metadata = DocumentMetadata(
            page_count=3,
            file_size_mb=0.5,
            text_length=len(text),
            extraction_date=datetime.now(),
        )

        return ExtractedDocument(
            filename="financial_report_q4_2023.pdf",
            file_path=Path("/data/uploads/financial_report_q4_2023.pdf"),
            extracted_text=text,
            metadata=metadata,
        )

    def _create_mock_embedding_response(self, num_embeddings: int) -> Mock:
        """Create mock embedding response from LiteLLM with specified number of embeddings.

        Args:
            num_embeddings: Number of embeddings to include in response

        Returns:
            Mock response object matching LiteLLM structure
        """
        mock_response = Mock()
        mock_response.data = []
        for _ in range(num_embeddings):
            mock_data_item = Mock()
            mock_data_item.embedding = [0.1] * 1536  # 1536-dimensional vector
            mock_response.data.append(mock_data_item)
        return mock_response

    def _mock_embedding_side_effect(self, model, input, api_key):
        """Side effect function for embedding mock that returns correct number of embeddings."""
        num_inputs = len(input) if isinstance(input, list) else 1
        return self._create_mock_embedding_response(num_inputs)

    @pytest.fixture
    def mock_completion_response(self) -> Mock:
        """Create mock completion response from LiteLLM."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = (
            "Based on the financial documents, the company reported revenue of $10 million "
            "in Q4 2023 [Page 1]. Operating expenses decreased by 15% [Page 2], resulting in "
            "improved profit margins from 12% to 18% year-over-year [Page 2]."
        )
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        return mock_response

    @pytest.fixture
    def rag_service(self, test_collection_name: str) -> RAGService:
        """Create RAGService with all dependencies and mocked LLM calls.

        This fixture:
        - Uses real DocumentChunker
        - Uses real VectorStoreManager (requires Qdrant running)
        - Uses EmbeddingGenerator but mocks the API calls
        - Uses RAGQueryEngine but mocks the LLM calls
        """
        # Create real components
        chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)

        # Create embedder with mocked API calls
        embedder = EmbeddingGenerator(
            embedding_model="text-embedding-3-small",
            api_key="test-api-key",
        )

        # Create real vector store (requires Qdrant running)
        vector_store = VectorStoreManager(
            host="localhost",
            port=6333,
            collection_name=test_collection_name,
        )

        # Create query engine
        query_engine = RAGQueryEngine(
            vector_store=vector_store,
            embedder=embedder,
            primary_llm="gpt-4-turbo-preview",
            fallback_llm="gpt-3.5-turbo",
            temperature=0.0,
            max_tokens=2000,
            top_k=5,
            min_score=0.7,
        )

        # Create service
        service = RAGService(
            chunker=chunker,
            embedder=embedder,
            vector_store=vector_store,
            query_engine=query_engine,
        )

        yield service

        # Cleanup: delete test collection
        try:
            vector_store.client.delete_collection(test_collection_name)
        except Exception:
            pass  # Collection might not exist if test failed early

    @patch("src.rag.embedder.embedding")
    def test_process_document_success(
        self,
        mock_embedding: Mock,
        rag_service: RAGService,
        sample_document: ExtractedDocument,
    ) -> None:
        """Test successful document processing through RAG pipeline."""
        # Mock embedding API to return correct number of embeddings
        mock_embedding.side_effect = self._mock_embedding_side_effect

        # Process document
        result = rag_service.process_document(sample_document)

        # Verify result structure
        assert isinstance(result, RAGResult)
        assert result.success is True
        assert result.document_id == sample_document.document_id
        assert result.chunks_created > 0
        assert result.chunks_indexed > 0
        assert result.chunks_created == result.chunks_indexed
        assert result.processing_time_seconds > 0
        assert result.error_message is None

        # Verify embeddings were called
        assert mock_embedding.call_count > 0

    @patch("src.rag.query_engine.completion")
    @patch("src.rag.embedder.embedding")
    def test_query_after_document_processing(
        self,
        mock_embedding: Mock,
        mock_completion: Mock,
        rag_service: RAGService,
        sample_document: ExtractedDocument,
        mock_completion_response: Mock,
    ) -> None:
        """Test querying the knowledge base after processing a document."""
        # Mock embedding API
        mock_embedding.side_effect = self._mock_embedding_side_effect

        # Process document first
        process_result = rag_service.process_document(sample_document)
        assert process_result.success is True

        # Mock completion API for query
        mock_completion.return_value = mock_completion_response

        # Query the knowledge base
        question = "What were the Q4 2023 financial results?"
        query_result = rag_service.query(question)

        # Verify query result
        assert isinstance(query_result, QueryResult)
        assert query_result.success is True
        assert query_result.answer is not None
        assert len(query_result.answer) > 0
        assert query_result.chunks_retrieved > 0
        assert len(query_result.sources) > 0
        assert query_result.query_time_seconds > 0
        assert query_result.error_message is None

        # Verify LLM was called
        mock_completion.assert_called_once()

    @patch("src.rag.embedder.embedding")
    def test_delete_document_success(
        self,
        mock_embedding: Mock,
        rag_service: RAGService,
        sample_document: ExtractedDocument,
    ) -> None:
        """Test successful deletion of document from vector store."""
        # Mock embedding API
        mock_embedding.side_effect = self._mock_embedding_side_effect

        # Process document first
        process_result = rag_service.process_document(sample_document)
        assert process_result.success is True

        # Delete the document
        delete_result = rag_service.delete_document(sample_document.document_id)
        assert delete_result is True

        # Verify chunks are removed by searching
        query_embedding = [0.1] * 1536
        search_results = rag_service.vector_store.search(
            query_embedding=query_embedding,
            top_k=10,
            min_score=0.0,
        )

        # Filter results to only those matching our document_id
        matching_results = [
            r for r in search_results if r["document_id"] == sample_document.document_id
        ]
        assert len(matching_results) == 0, "Chunks should be deleted from vector store"

    @patch("src.rag.embedder.embedding")
    def test_process_empty_document_fails(
        self,
        mock_embedding: Mock,
        rag_service: RAGService,
    ) -> None:
        """Test processing empty document returns error result."""
        # Create empty document
        metadata = DocumentMetadata(
            page_count=1,
            file_size_mb=0.001,
            text_length=0,
            extraction_date=datetime.now(),
        )

        empty_doc = ExtractedDocument(
            filename="empty.pdf",
            file_path=Path("/data/uploads/empty.pdf"),
            extracted_text="",
            metadata=metadata,
        )

        # Process empty document
        result = rag_service.process_document(empty_doc)

        # Verify failure
        assert isinstance(result, RAGResult)
        assert result.success is False
        assert result.document_id == empty_doc.document_id
        assert result.chunks_created == 0
        assert result.chunks_indexed == 0
        assert result.processing_time_seconds > 0
        assert result.error_message is not None
        assert "Chunking" in result.error_message or "empty" in result.error_message.lower()

    @patch("src.rag.embedder.embedding")
    def test_embedding_failure_returns_error(
        self,
        mock_embedding: Mock,
        rag_service: RAGService,
        sample_document: ExtractedDocument,
    ) -> None:
        """Test that embedding failure is caught and returns error result."""
        # Mock embedding to raise exception
        mock_embedding.side_effect = Exception("OpenAI API rate limit exceeded")

        # Process document
        result = rag_service.process_document(sample_document)

        # Verify failure
        assert isinstance(result, RAGResult)
        assert result.success is False
        assert result.document_id == sample_document.document_id
        assert result.chunks_created == 0  # Failed before indexing
        assert result.chunks_indexed == 0
        assert result.processing_time_seconds > 0
        assert result.error_message is not None
        assert "rate limit" in result.error_message.lower() or "failed" in result.error_message.lower()

    @patch("src.rag.embedder.embedding")
    def test_vector_store_failure_returns_error(
        self,
        mock_embedding: Mock,
        rag_service: RAGService,
        sample_document: ExtractedDocument,
    ) -> None:
        """Test that vector store failure is caught and returns error result."""
        # Mock embedding to succeed
        mock_embedding.side_effect = self._mock_embedding_side_effect

        # Mock vector store upsert to fail
        original_upsert = rag_service.vector_store.upsert_chunks
        rag_service.vector_store.upsert_chunks = Mock(
            side_effect=Exception("Qdrant connection timeout")
        )

        try:
            # Process document
            result = rag_service.process_document(sample_document)

            # Verify failure
            assert isinstance(result, RAGResult)
            assert result.success is False
            assert result.document_id == sample_document.document_id
            # Note: chunks_created will be 0 because the error happens during embedding/indexing
            # and the service doesn't separately track chunking success
            assert result.chunks_indexed == 0  # Indexing failed
            assert result.processing_time_seconds > 0
            assert result.error_message is not None
            assert "qdrant" in result.error_message.lower() or "timeout" in result.error_message.lower()
        finally:
            # Restore original method
            rag_service.vector_store.upsert_chunks = original_upsert

    @patch("src.rag.embedder.embedding")
    def test_process_document_statistics(
        self,
        mock_embedding: Mock,
        rag_service: RAGService,
        sample_document: ExtractedDocument,
    ) -> None:
        """Test that processing statistics are accurately tracked."""
        # Mock embedding API
        mock_embedding.side_effect = self._mock_embedding_side_effect

        # Process document
        result = rag_service.process_document(sample_document)

        # Verify statistics
        assert result.success is True
        assert result.chunks_created > 0
        assert result.chunks_indexed == result.chunks_created
        assert result.processing_time_seconds > 0
        assert result.processing_time_seconds < 30  # Should complete reasonably fast

        # Verify reasonable chunk count (document is ~1400 chars, chunks are ~500)
        assert 2 <= result.chunks_created <= 10, f"Expected 2-10 chunks, got {result.chunks_created}"

    @patch("src.rag.query_engine.completion")
    @patch("src.rag.embedder.embedding")
    def test_query_with_no_relevant_documents(
        self,
        mock_embedding: Mock,
        mock_completion: Mock,
        rag_service: RAGService,
    ) -> None:
        """Test querying when no relevant documents exist returns appropriate response."""
        # Mock embedding API
        mock_embedding.side_effect = self._mock_embedding_side_effect

        # Don't process any documents - query empty knowledge base
        question = "What is the weather today?"
        result = rag_service.query(question)

        # Verify result
        assert isinstance(result, QueryResult)
        assert result.success is True
        assert result.chunks_retrieved == 0
        assert len(result.sources) == 0
        assert "don't have enough information" in result.answer

        # Verify LLM was NOT called (no context to send)
        mock_completion.assert_not_called()

    @patch("src.rag.embedder.embedding")
    def test_multiple_document_processing(
        self,
        mock_embedding: Mock,
        rag_service: RAGService,
    ) -> None:
        """Test processing multiple documents in sequence."""
        # Mock embedding API
        mock_embedding.side_effect = self._mock_embedding_side_effect

        # Create multiple documents
        doc1_text = "First document about revenue growth in technology sector." * 50
        doc1_metadata = DocumentMetadata(
            page_count=1, file_size_mb=0.1, text_length=len(doc1_text)
        )
        doc1 = ExtractedDocument(
            filename="doc1.pdf",
            file_path=Path("/data/uploads/doc1.pdf"),
            extracted_text=doc1_text,
            metadata=doc1_metadata,
        )

        doc2_text = "Second document about operating expenses and cost reduction." * 50
        doc2_metadata = DocumentMetadata(
            page_count=1, file_size_mb=0.1, text_length=len(doc2_text)
        )
        doc2 = ExtractedDocument(
            filename="doc2.pdf",
            file_path=Path("/data/uploads/doc2.pdf"),
            extracted_text=doc2_text,
            metadata=doc2_metadata,
        )

        # Process both documents
        result1 = rag_service.process_document(doc1)
        result2 = rag_service.process_document(doc2)

        # Verify both succeeded
        assert result1.success is True
        assert result2.success is True
        assert result1.document_id != result2.document_id

        # Verify both documents are in vector store
        query_embedding = [0.1] * 1536
        search_results = rag_service.vector_store.search(
            query_embedding=query_embedding,
            top_k=20,
            min_score=0.0,
        )

        # Check we have chunks from both documents
        doc_ids = {r["document_id"] for r in search_results}
        assert doc1.document_id in doc_ids
        assert doc2.document_id in doc_ids

    @patch("src.rag.query_engine.completion")
    @patch("src.rag.embedder.embedding")
    def test_query_retrieves_relevant_chunks(
        self,
        mock_embedding: Mock,
        mock_completion: Mock,
        rag_service: RAGService,
        sample_document: ExtractedDocument,
        mock_completion_response: Mock,
    ) -> None:
        """Test that query retrieves relevant chunks from processed document."""
        # Mock embedding API
        mock_embedding.side_effect = self._mock_embedding_side_effect

        # Process document
        process_result = rag_service.process_document(sample_document)
        assert process_result.success is True

        # Mock completion API
        mock_completion.return_value = mock_completion_response

        # Query with relevant question
        question = "What were the operating expenses?"
        result = rag_service.query(question)

        # Verify chunks were retrieved
        assert result.success is True
        assert result.chunks_retrieved > 0
        assert len(result.sources) > 0

        # Verify sources have correct structure
        for source in result.sources:
            assert source.document_id == sample_document.document_id
            assert len(source.page_numbers) > 0
            assert 0.0 <= source.relevance_score <= 1.0
            assert len(source.snippet) > 0

    @patch("src.rag.embedder.embedding")
    def test_delete_nonexistent_document(
        self,
        mock_embedding: Mock,
        rag_service: RAGService,
    ) -> None:
        """Test deleting a document that doesn't exist returns True (no-op)."""
        # Delete non-existent document
        fake_doc_id = "nonexistent_doc_12345"
        result = rag_service.delete_document(fake_doc_id)

        # Qdrant delete returns success even if no documents matched
        assert result is True

    @patch("src.rag.embedder.embedding")
    def test_process_document_with_special_characters(
        self,
        mock_embedding: Mock,
        rag_service: RAGService,
    ) -> None:
        """Test processing document with special characters and formatting."""
        # Mock embedding API
        mock_embedding.side_effect = self._mock_embedding_side_effect

        # Create document with special characters
        text = """Financial Report: Q4'23 Results

Revenue: $10,000,000 (↑25% YoY)
Expenses: -$8,200,000 (↓15% QoQ)
Net Income: $1,800,000 (18% margin)

Key Metrics:
• ROI: 15.5%
• P/E Ratio: 12.3x
• EPS: $2.45/share
• Debt/Equity: 0.3:1

Special Notes:
1) Revenue includes one-time gains
2) Excluding non-recurring items
3) Forward-looking statements subject to risk

[See Appendix A for details]
""" * 5  # Make it longer

        metadata = DocumentMetadata(
            page_count=2, file_size_mb=0.1, text_length=len(text)
        )

        doc = ExtractedDocument(
            filename="special_chars.pdf",
            file_path=Path("/data/uploads/special_chars.pdf"),
            extracted_text=text,
            metadata=metadata,
        )

        # Process document
        result = rag_service.process_document(doc)

        # Verify success despite special characters
        assert result.success is True
        assert result.chunks_created > 0
        assert result.chunks_indexed > 0

    @patch("src.rag.embedder.embedding")
    def test_chunking_preserves_context(
        self,
        mock_embedding: Mock,
        rag_service: RAGService,
        sample_document: ExtractedDocument,
    ) -> None:
        """Test that chunking creates reasonable chunk sizes with overlap."""
        # Mock embedding API
        mock_embedding.side_effect = self._mock_embedding_side_effect

        # Process document
        result = rag_service.process_document(sample_document)
        assert result.success is True

        # Retrieve chunks from vector store to verify structure
        query_embedding = [0.1] * 1536
        search_results = rag_service.vector_store.search(
            query_embedding=query_embedding,
            top_k=100,
            min_score=0.0,
        )

        # Filter to our document
        doc_chunks = [
            r for r in search_results if r["document_id"] == sample_document.document_id
        ]

        # Verify chunk properties
        assert len(doc_chunks) > 0
        for chunk in doc_chunks:
            assert "content" in chunk
            assert "page_numbers" in chunk
            assert len(chunk["content"]) > 0
            assert len(chunk["page_numbers"]) > 0

    @patch("src.rag.embedder.embedding")
    def test_process_document_error_contains_traceback(
        self,
        mock_embedding: Mock,
        rag_service: RAGService,
        sample_document: ExtractedDocument,
    ) -> None:
        """Test that error messages contain helpful debugging information."""
        # Mock embedding to raise exception
        mock_embedding.side_effect = ValueError("Invalid embedding dimension")

        # Process document
        result = rag_service.process_document(sample_document)

        # Verify error message contains useful info
        assert result.success is False
        assert result.error_message is not None
        assert sample_document.document_id in result.error_message
        assert "Failed to process document" in result.error_message

    @patch("src.rag.embedder.embedding")
    def test_service_initialization(
        self,
        mock_embedding: Mock,
        test_collection_name: str,
    ) -> None:
        """Test that RAGService initializes correctly with all components."""
        # Create components
        chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)
        embedder = EmbeddingGenerator(
            embedding_model="text-embedding-3-small",
            api_key="test-key",
        )
        vector_store = VectorStoreManager(
            host="localhost",
            port=6333,
            collection_name=test_collection_name,
        )
        query_engine = RAGQueryEngine(
            vector_store=vector_store,
            embedder=embedder,
            primary_llm="gpt-4",
            fallback_llm="gpt-3.5-turbo",
        )

        # Initialize service
        service = RAGService(
            chunker=chunker,
            embedder=embedder,
            vector_store=vector_store,
            query_engine=query_engine,
        )

        # Verify components are set
        assert service.chunker == chunker
        assert service.embedder == embedder
        assert service.vector_store == vector_store
        assert service.query_engine == query_engine

        # Cleanup
        try:
            vector_store.client.delete_collection(test_collection_name)
        except Exception:
            pass

    @patch("src.rag.embedder.embedding")
    def test_concurrent_document_operations(
        self,
        mock_embedding: Mock,
        rag_service: RAGService,
        sample_document: ExtractedDocument,
    ) -> None:
        """Test processing and deleting documents in sequence."""
        # Mock embedding API
        mock_embedding.side_effect = self._mock_embedding_side_effect

        # Process document
        process_result = rag_service.process_document(sample_document)
        assert process_result.success is True
        first_doc_id = process_result.document_id

        # Immediately delete it
        delete_result = rag_service.delete_document(first_doc_id)
        assert delete_result is True

        # Create a slightly different document to get a different ID
        import time
        time.sleep(1.1)  # Wait 1 second to ensure different timestamp

        # Update the document's extraction_date to force a new document_id
        sample_document.metadata.extraction_date = datetime.now()

        # Try to process document again (should have different document_id due to new timestamp)
        process_result2 = rag_service.process_document(sample_document)
        assert process_result2.success is True

        # Verify it's treated as a different document
        assert process_result2.document_id != first_doc_id
