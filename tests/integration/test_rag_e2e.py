"""End-to-end integration tests for RAG system with real documents."""

import logging
import os
from collections.abc import Generator
from pathlib import Path

import pytest

from src.pdf_processor.extractors import PDFTextExtractor
from src.pdf_processor.models import ExtractedDocument, UploadedFile
from src.rag.chunker import DocumentChunker
from src.rag.embedder import EmbeddingGenerator
from src.rag.models import QueryResult, RAGResult
from src.rag.query_engine import RAGQueryEngine
from src.rag.service import RAGService
from src.rag.vector_store import VectorStoreManager

logger = logging.getLogger(__name__)

# Check if API key is available
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SKIP_IF_NO_API_KEY = pytest.mark.skipif(
    not OPENAI_API_KEY,
    reason="OPENAI_API_KEY not set in environment",
)

# Path to test document
TEST_PDF_PATH = Path("/home/dona/projects/IBMProject/data/sample/aapl-20250927.pdf")
SKIP_IF_NO_PDF = pytest.mark.skipif(
    not TEST_PDF_PATH.exists(),
    reason=f"Test PDF not found at {TEST_PDF_PATH}",
)


@pytest.fixture(scope="module")
def test_collection_name() -> str:
    """Unique collection name for E2E tests."""
    return "test_e2e_rag_collection"


@pytest.fixture(scope="module")
def pdf_extractor() -> PDFTextExtractor:
    """Create PDF text extractor for loading test document."""
    return PDFTextExtractor(min_text_length=100)


@pytest.fixture(scope="module")
def rag_service(test_collection_name: str) -> Generator[RAGService, None, None]:
    """Create RAGService with real components and real API calls.

    This fixture initializes the complete RAG stack with:
    - Real DocumentChunker
    - Real EmbeddingGenerator (with actual OpenAI API calls)
    - Real VectorStoreManager (requires Qdrant running on localhost:6333)
    - Real RAGQueryEngine (with actual LLM API calls)

    The service uses module scope so document is indexed once for all tests.
    After all tests complete, the test collection is cleaned up from Qdrant.

    Yields:
        RAGService configured for E2E testing

    Note:
        Requires OPENAI_API_KEY in environment and Qdrant running locally.
    """
    logger.info(f"Initializing RAG service with test collection: {test_collection_name}")

    # Create real components
    chunker = DocumentChunker(chunk_size=1000, chunk_overlap=200)

    embedder = EmbeddingGenerator(
        embedding_model="text-embedding-3-small",
        api_key=OPENAI_API_KEY,
    )

    vector_store = VectorStoreManager(
        host="localhost",
        port=6333,
        collection_name=test_collection_name,
    )

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

    service = RAGService(
        chunker=chunker,
        embedder=embedder,
        vector_store=vector_store,
        query_engine=query_engine,
    )

    logger.info("RAG service initialized successfully")

    yield service

    # Cleanup: delete test collection from Qdrant
    logger.info(f"Cleaning up test collection: {test_collection_name}")
    try:
        vector_store.client.delete_collection(test_collection_name)
        logger.info("Test collection deleted successfully")
    except Exception as e:
        logger.warning(f"Failed to delete test collection: {e}")


@pytest.fixture(scope="module")
def indexed_document(
    rag_service: RAGService,
    pdf_extractor: PDFTextExtractor,
) -> ExtractedDocument:
    """Load and index Apple 10-K document for all tests.

    This fixture:
    1. Loads the Apple 10-K PDF from data/sample/
    2. Extracts text using PDFTextExtractor
    3. Indexes the document using RAGService
    4. Returns the ExtractedDocument for verification

    The document is indexed once (module scope) and reused across all tests
    for efficiency, as indexing a large document is time-consuming.

    Returns:
        ExtractedDocument with Apple 10-K data

    Raises:
        FileNotFoundError: If test PDF is not found
        Exception: If extraction or indexing fails
    """
    logger.info(f"Loading test PDF: {TEST_PDF_PATH}")

    # Load PDF file
    if not TEST_PDF_PATH.exists():
        raise FileNotFoundError(f"Test PDF not found: {TEST_PDF_PATH}")

    with open(TEST_PDF_PATH, "rb") as f:
        pdf_content = f.read()

    # Create UploadedFile model
    uploaded_file = UploadedFile(
        name=TEST_PDF_PATH.name,
        content=pdf_content,
        size=len(pdf_content),
        mime_type="application/pdf",
    )

    logger.info(f"PDF loaded: {uploaded_file.size_mb}MB, {uploaded_file.name}")

    # Extract text
    logger.info("Extracting text from PDF...")
    extracted_text = pdf_extractor.extract_text(uploaded_file)
    logger.info(f"Text extracted: {len(extracted_text)} characters")

    # Extract metadata
    metadata = pdf_extractor.extract_metadata(uploaded_file, extracted_text)
    logger.info(f"Metadata: {metadata.page_count} pages")

    # Create ExtractedDocument
    document = ExtractedDocument(
        filename=uploaded_file.name,
        file_path=TEST_PDF_PATH,
        extracted_text=extracted_text,
        metadata=metadata,
    )

    logger.info(f"Document ID: {document.document_id}")

    # Index document with RAG service
    logger.info("Indexing document with RAG service...")
    result = rag_service.process_document(document)

    # Verify indexing succeeded
    if not result.success:
        raise Exception(f"Failed to index document: {result.error_message}")

    logger.info(
        f"Document indexed successfully: "
        f"{result.chunks_created} chunks created, "
        f"{result.chunks_indexed} chunks indexed in {result.processing_time_seconds:.2f}s"
    )

    return document


@SKIP_IF_NO_API_KEY
@SKIP_IF_NO_PDF
class TestRAGEndToEnd:
    """End-to-end integration tests for RAG system with real Apple 10-K document.

    These tests validate the complete RAG pipeline using:
    - Real Apple 10-K PDF (aapl-20250927.pdf, ~2.4MB)
    - Real OpenAI API calls for embeddings and completions
    - Real Qdrant vector database
    - No mocking - full integration testing

    The document is indexed once (module-scoped fixture) and reused across
    all query tests for efficiency.
    """

    def test_e2e_document_upload_and_indexing(
        self,
        rag_service: RAGService,
        indexed_document: ExtractedDocument,
    ) -> None:
        """Test complete document upload and indexing pipeline.

        This test validates that:
        1. Apple 10-K PDF loads correctly from data/sample/
        2. Text extraction succeeds with reasonable text length
        3. Document indexes successfully with RAGService
        4. Appropriate number of chunks are created and indexed
        5. Processing completes within reasonable time

        The indexed_document fixture handles the actual processing,
        so this test verifies the results.
        """
        logger.info("TEST: Document upload and indexing")

        # Verify document was loaded
        assert indexed_document is not None
        assert indexed_document.filename == "aapl-20250927.pdf"
        assert len(indexed_document.extracted_text) > 10000, (
            "Apple 10-K should have substantial text content"
        )
        assert indexed_document.metadata.page_count > 50, (
            "Apple 10-K typically has 100+ pages"
        )

        # Verify document is in vector store by searching
        query_embedding = rag_service.embedder.embed_query("Apple financial results")
        search_results = rag_service.vector_store.search(
            query_embedding=query_embedding,
            top_k=10,
            min_score=0.0,
        )

        # Should find chunks from our document
        matching_chunks = [
            r for r in search_results
            if r["document_id"] == indexed_document.document_id
        ]

        assert len(matching_chunks) > 0, "Document chunks should be in vector store"

        logger.info(f"✓ Document indexed successfully with {len(matching_chunks)} searchable chunks")

    def test_e2e_simple_query(
        self,
        rag_service: RAGService,
        indexed_document: ExtractedDocument,
    ) -> None:
        """Test simple factual query about revenue.

        Validates:
        - Query returns successful result
        - Answer mentions revenue/sales figures
        - Sources include relevant pages
        - Page numbers are within document range
        """
        logger.info("TEST: Simple query - revenue")

        question = "What were Apple's total net sales in 2025?"

        result = rag_service.query(question)

        # Verify query succeeded
        assert isinstance(result, QueryResult)
        assert result.success is True
        assert result.error_message is None

        # Verify answer content
        assert len(result.answer) > 50, "Answer should be substantive"
        assert any(
            keyword in result.answer.lower()
            for keyword in ["revenue", "sales", "billion", "million", "$"]
        ), "Answer should mention financial figures"

        # Verify sources
        assert len(result.sources) > 0, "Should have source citations"
        assert result.chunks_retrieved > 0

        # Verify page numbers are reasonable
        for source in result.sources:
            assert source.document_id == indexed_document.document_id
            assert len(source.page_numbers) > 0
            assert all(1 <= page <= 200 for page in source.page_numbers), (
                f"Page numbers should be reasonable: {source.page_numbers}"
            )
            assert 0.0 <= source.relevance_score <= 1.0
            assert len(source.snippet) > 0

        logger.info(
            f"✓ Simple query succeeded: {len(result.answer)} char answer, "
            f"{len(result.sources)} sources, {result.query_time_seconds:.2f}s"
        )
        logger.info(f"Answer preview: {result.answer[:200]}...")

    def test_e2e_complex_query(
        self,
        rag_service: RAGService,
        indexed_document: ExtractedDocument,
    ) -> None:
        """Test complex query requiring synthesis from multiple sections.

        Validates:
        - Query handles multi-faceted questions
        - Answer synthesizes information from multiple chunks
        - Risk factors are identified and summarized
        - Multiple sources are cited
        """
        logger.info("TEST: Complex query - risk factors")

        question = "What are the main risk factors mentioned in Apple's 10-K?"

        result = rag_service.query(question)

        # Verify query succeeded
        assert result.success is True
        assert result.error_message is None

        # Verify answer discusses risks
        assert len(result.answer) > 100, "Complex answer should be detailed"

        # Answer should mention risk-related concepts
        risk_keywords = [
            "risk", "competition", "regulatory", "market", "economic",
            "supply", "demand", "legal", "technology", "uncertainty"
        ]
        assert any(
            keyword in result.answer.lower() for keyword in risk_keywords
        ), "Answer should discuss risk factors"

        # Should retrieve multiple relevant chunks
        assert result.chunks_retrieved >= 3, (
            "Complex query should retrieve multiple chunks"
        )
        assert len(result.sources) >= 2, (
            "Should cite multiple sources for comprehensive answer"
        )

        # Verify sources
        for source in result.sources:
            assert source.document_id == indexed_document.document_id
            assert len(source.page_numbers) > 0
            assert 0.0 <= source.relevance_score <= 1.0

        logger.info(
            f"✓ Complex query succeeded: {result.chunks_retrieved} chunks retrieved, "
            f"{len(result.sources)} sources cited"
        )
        logger.info(f"Answer preview: {result.answer[:250]}...")

    def test_e2e_multi_part_query(
        self,
        rag_service: RAGService,
        indexed_document: ExtractedDocument,
    ) -> None:
        """Test query requiring comparison across time periods.

        Validates:
        - Query handles comparative questions
        - Answer compares multiple periods/metrics
        - Sources span relevant sections
        """
        logger.info("TEST: Multi-part query - product comparison")

        question = "How did iPhone sales compare between 2024 and 2025?"

        result = rag_service.query(question)

        # Verify query succeeded
        assert result.success is True
        assert result.error_message is None

        # Verify answer addresses comparison
        assert len(result.answer) > 50
        assert any(
            keyword in result.answer.lower()
            for keyword in ["iphone", "product", "segment", "sales", "revenue"]
        ), "Answer should discuss iPhone sales"

        # Comparative answers often need multiple sources
        assert result.chunks_retrieved > 0
        assert len(result.sources) > 0

        # Verify sources
        for source in result.sources:
            assert source.document_id == indexed_document.document_id
            assert len(source.page_numbers) > 0
            assert all(1 <= page <= 200 for page in source.page_numbers)

        logger.info(
            f"✓ Multi-part query succeeded: {len(result.sources)} sources, "
            f"{result.query_time_seconds:.2f}s"
        )
        logger.info(f"Answer preview: {result.answer[:200]}...")

    def test_e2e_out_of_scope_query(
        self,
        rag_service: RAGService,
        indexed_document: ExtractedDocument,
    ) -> None:
        """Test query asking for information not in the document.

        Validates:
        - System gracefully handles out-of-scope questions
        - Answer politely declines with explanation
        - No hallucinated information
        - Mentions lack of relevant information
        """
        logger.info("TEST: Out-of-scope query")

        question = "What is Apple's current stock price?"

        result = rag_service.query(question)

        # Query should technically succeed but indicate no information
        assert result.success is True

        # Answer should indicate information is not available
        decline_indicators = [
            "don't have",
            "not found",
            "not available",
            "cannot find",
            "no information",
            "not mentioned",
            "doesn't contain",
        ]

        answer_lower = result.answer.lower()
        assert any(
            indicator in answer_lower for indicator in decline_indicators
        ), f"Answer should politely decline: {result.answer}"

        # Either no chunks retrieved or low relevance
        if result.chunks_retrieved > 0:
            # If chunks were retrieved, relevance should be low
            assert all(
                source.relevance_score < 0.85 for source in result.sources
            ), "Out-of-scope queries should have low relevance scores"

        logger.info(f"✓ Out-of-scope query handled gracefully")
        logger.info(f"Answer: {result.answer}")

    def test_e2e_source_citation_accuracy(
        self,
        rag_service: RAGService,
        indexed_document: ExtractedDocument,
    ) -> None:
        """Test accuracy and completeness of source citations.

        Validates:
        - All citations have required fields
        - Page numbers are within valid range
        - Relevance scores are properly normalized
        - Snippets contain actual text content
        - Citations link back to correct document
        """
        logger.info("TEST: Source citation accuracy")

        question = "What is Apple's business model and primary products?"

        result = rag_service.query(question)

        # Verify query succeeded
        assert result.success is True
        assert len(result.sources) > 0, "Query should return sources"

        # Test each source citation
        for idx, source in enumerate(result.sources):
            logger.info(f"Verifying source citation {idx + 1}/{len(result.sources)}")

            # Required fields present
            assert source.document_id == indexed_document.document_id, (
                "Source should link to our test document"
            )

            assert len(source.page_numbers) > 0, (
                "Source must include page numbers"
            )

            # Page numbers in valid range
            assert all(isinstance(page, int) for page in source.page_numbers), (
                "Page numbers must be integers"
            )

            assert all(1 <= page <= 200 for page in source.page_numbers), (
                f"Page numbers should be reasonable for 10-K: {source.page_numbers}"
            )

            # Relevance score properly normalized
            assert 0.0 <= source.relevance_score <= 1.0, (
                f"Relevance score must be in [0, 1]: {source.relevance_score}"
            )

            # For this query, should have good relevance
            assert source.relevance_score >= 0.7, (
                "Top sources should have high relevance for clear query"
            )

            # Snippet should contain actual text
            assert len(source.snippet) > 20, (
                "Snippet should contain meaningful text"
            )

            assert source.snippet.strip() != "", (
                "Snippet should not be empty or whitespace"
            )

            # Snippet should contain some letters (not just numbers/symbols)
            assert any(c.isalpha() for c in source.snippet), (
                "Snippet should contain readable text"
            )

            logger.info(
                f"  ✓ Source {idx + 1}: pages {source.page_numbers}, "
                f"score {source.relevance_score:.3f}, "
                f"snippet {len(source.snippet)} chars"
            )

        logger.info(f"✓ All {len(result.sources)} source citations are accurate and complete")

    def test_e2e_query_performance(
        self,
        rag_service: RAGService,
        indexed_document: ExtractedDocument,
    ) -> None:
        """Test query performance with real API calls.

        Validates:
        - Queries complete within reasonable time
        - Performance is logged for monitoring
        - System handles multiple sequential queries
        """
        logger.info("TEST: Query performance")

        questions = [
            "What were Apple's total revenues?",
            "What products does Apple sell?",
            "What are Apple's main business segments?",
        ]

        query_times = []

        for question in questions:
            result = rag_service.query(question)

            assert result.success is True
            assert result.query_time_seconds > 0

            query_times.append(result.query_time_seconds)

            logger.info(
                f"Query: '{question[:50]}...' - {result.query_time_seconds:.2f}s"
            )

        # Verify reasonable performance
        avg_time = sum(query_times) / len(query_times)
        max_time = max(query_times)

        logger.info(
            f"✓ Performance metrics: avg={avg_time:.2f}s, max={max_time:.2f}s"
        )

        # These are real API calls, so allow reasonable time
        assert avg_time < 30.0, (
            f"Average query time should be under 30s, got {avg_time:.2f}s"
        )
        assert max_time < 45.0, (
            f"Max query time should be under 45s, got {max_time:.2f}s"
        )

    def test_e2e_document_cleanup(
        self,
        rag_service: RAGService,
        indexed_document: ExtractedDocument,
    ) -> None:
        """Test document deletion and cleanup.

        Validates:
        - Documents can be deleted from vector store
        - All chunks are removed
        - Deletion succeeds without errors

        Note: This test runs last (alphabetically) to avoid affecting other tests.
        After deletion, the indexed_document fixture is no longer valid for queries.
        """
        logger.info("TEST: Document cleanup")

        document_id = indexed_document.document_id

        # Verify document exists before deletion
        query_embedding = rag_service.embedder.embed_query("test")
        results_before = rag_service.vector_store.search(
            query_embedding=query_embedding,
            top_k=100,
            min_score=0.0,
        )

        matching_before = [
            r for r in results_before if r["document_id"] == document_id
        ]

        assert len(matching_before) > 0, (
            "Document chunks should exist before deletion"
        )

        logger.info(f"Found {len(matching_before)} chunks before deletion")

        # Delete the document
        delete_result = rag_service.delete_document(document_id)

        assert delete_result is True, "Deletion should succeed"

        # Verify chunks are removed
        results_after = rag_service.vector_store.search(
            query_embedding=query_embedding,
            top_k=100,
            min_score=0.0,
        )

        matching_after = [
            r for r in results_after if r["document_id"] == document_id
        ]

        assert len(matching_after) == 0, (
            "All document chunks should be deleted from vector store"
        )

        logger.info(f"✓ Document {document_id} successfully deleted from vector store")


@pytest.mark.integration
@SKIP_IF_NO_API_KEY
@SKIP_IF_NO_PDF
def test_e2e_full_pipeline_isolated() -> None:
    """Isolated end-to-end test of the complete pipeline from scratch.

    This test creates its own components and runs the full pipeline independently:
    1. Load PDF
    2. Extract text
    3. Initialize RAG components
    4. Index document
    5. Query knowledge base
    6. Clean up

    This validates the entire system can be initialized and used from scratch
    without relying on module-scoped fixtures.
    """
    logger.info("TEST: Full isolated E2E pipeline")

    # Use unique collection to avoid conflicts
    collection_name = "test_e2e_isolated"

    try:
        # Step 1: Load PDF
        logger.info("Step 1: Loading PDF")
        with open(TEST_PDF_PATH, "rb") as f:
            pdf_content = f.read()

        uploaded_file = UploadedFile(
            name=TEST_PDF_PATH.name,
            content=pdf_content,
            size=len(pdf_content),
            mime_type="application/pdf",
        )

        logger.info(f"PDF loaded: {uploaded_file.size_mb}MB")

        # Step 2: Extract text
        logger.info("Step 2: Extracting text")
        extractor = PDFTextExtractor(min_text_length=100)
        extracted_text = extractor.extract_text(uploaded_file)
        metadata = extractor.extract_metadata(uploaded_file, extracted_text)

        document = ExtractedDocument(
            filename=uploaded_file.name,
            file_path=TEST_PDF_PATH,
            extracted_text=extracted_text,
            metadata=metadata,
        )

        logger.info(f"Text extracted: {len(extracted_text)} chars, {metadata.page_count} pages")

        # Step 3: Initialize RAG components
        logger.info("Step 3: Initializing RAG components")
        chunker = DocumentChunker(chunk_size=1000, chunk_overlap=200)
        embedder = EmbeddingGenerator(
            embedding_model="text-embedding-3-small",
            api_key=OPENAI_API_KEY,
        )
        vector_store = VectorStoreManager(
            host="localhost",
            port=6333,
            collection_name=collection_name,
        )
        query_engine = RAGQueryEngine(
            vector_store=vector_store,
            embedder=embedder,
            primary_llm="gpt-4-turbo-preview",
            fallback_llm="gpt-3.5-turbo",
        )
        rag_service = RAGService(
            chunker=chunker,
            embedder=embedder,
            vector_store=vector_store,
            query_engine=query_engine,
        )

        logger.info("RAG components initialized")

        # Step 4: Index document
        logger.info("Step 4: Indexing document")
        index_result = rag_service.process_document(document)

        assert index_result.success is True, f"Indexing failed: {index_result.error_message}"
        assert index_result.chunks_created > 0
        assert index_result.chunks_indexed > 0

        logger.info(
            f"Document indexed: {index_result.chunks_created} chunks in "
            f"{index_result.processing_time_seconds:.2f}s"
        )

        # Step 5: Query knowledge base
        logger.info("Step 5: Querying knowledge base")
        question = "What is Apple's primary business?"
        query_result = rag_service.query(question)

        assert query_result.success is True, f"Query failed: {query_result.error_message}"
        assert len(query_result.answer) > 0
        assert len(query_result.sources) > 0

        logger.info(
            f"Query succeeded: {len(query_result.answer)} char answer, "
            f"{len(query_result.sources)} sources"
        )

        # Step 6: Clean up
        logger.info("Step 6: Cleaning up")
        vector_store.client.delete_collection(collection_name)

        logger.info("✓ Full isolated E2E pipeline completed successfully")

    except Exception as e:
        # Ensure cleanup even on failure
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(host="localhost", port=6333)
            client.delete_collection(collection_name)
        except Exception:
            pass

        raise e
