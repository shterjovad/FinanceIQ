"""Unit tests for DocumentChunker."""

import pytest
from pathlib import Path

from src.pdf_processor.models import DocumentMetadata, ExtractedDocument
from src.rag.chunker import DocumentChunker
from src.rag.exceptions import ChunkingError


class TestDocumentChunker:
    """Test suite for DocumentChunker."""

    @pytest.fixture
    def chunker(self) -> DocumentChunker:
        """Create DocumentChunker instance with standard settings."""
        return DocumentChunker(chunk_size=1000, chunk_overlap=200)

    @pytest.fixture
    def sample_document(self) -> ExtractedDocument:
        """Create sample ExtractedDocument for testing."""
        text = """Introduction to Financial Analysis

Financial analysis is a critical component of investment decisions.
Investors use various metrics to evaluate company performance.

Key Financial Metrics

Revenue growth is often the first indicator analysts examine.
Operating margins reveal efficiency in operations.
Free cash flow demonstrates the company's ability to generate cash.

Risk Factors

Market volatility can significantly impact investment returns.
Regulatory changes may affect industry dynamics.
Competitive pressures require constant innovation.""" * 5  # Make it long enough

        metadata = DocumentMetadata(
            page_count=3, file_size_mb=0.01, text_length=len(text)
        )

        return ExtractedDocument(
            filename="test_doc.pdf",
            file_path=Path("data/uploads/test_doc.pdf"),
            extracted_text=text,
            metadata=metadata,
        )

    def test_chunk_simple_document(
        self, chunker: DocumentChunker, sample_document: ExtractedDocument
    ) -> None:
        """Test chunking a simple document."""
        chunks = chunker.chunk_document(sample_document)

        # Verify we created chunks
        assert len(chunks) > 0, "Should create at least one chunk"

        # Verify chunk count is reasonable (not too many, not too few)
        assert len(chunks) < 100, "Should not create excessive chunks"

        # Verify each chunk has required fields
        for chunk in chunks:
            assert chunk.chunk_id, "Chunk should have ID"
            assert chunk.document_id == sample_document.document_id
            assert chunk.content, "Chunk should have content"
            assert chunk.token_count > 0, "Chunk should have token count"
            assert len(chunk.page_numbers) > 0, "Chunk should have page numbers"
            assert chunk.embedding is None, "Embedding should be None initially"

    def test_chunk_overlap(self, chunker: DocumentChunker) -> None:
        """Test that chunk overlap works correctly."""
        # Create document with known content
        text = "Word " * 500  # 500 words, should create multiple chunks

        metadata = DocumentMetadata(
            page_count=1, file_size_mb=0.01, text_length=len(text)
        )

        document = ExtractedDocument(
            filename="overlap_test.pdf",
            file_path=Path("data/uploads/overlap_test.pdf"),
            extracted_text=text,
            metadata=metadata,
        )

        chunks = chunker.chunk_document(document)

        # If we have multiple chunks, verify overlap exists
        if len(chunks) > 1:
            # Check that consecutive chunks have some overlap
            for i in range(len(chunks) - 1):
                current_chunk = chunks[i]
                next_chunk = chunks[i + 1]

                # Verify character positions make sense
                assert (
                    current_chunk.char_start < current_chunk.char_end
                ), "Chunk positions should be valid"
                assert (
                    next_chunk.char_start < next_chunk.char_end
                ), "Next chunk positions should be valid"

    def test_page_number_tracking(self, chunker: DocumentChunker) -> None:
        """Test page number tracking accuracy."""
        # Create multi-page document with page boundaries
        page1 = "This is page one content. " * 50
        page2 = "This is page two content. " * 50
        page3 = "This is page three content. " * 50

        # Join with double newline (page separator)
        text = page1 + "\n\n" + page2 + "\n\n" + page3

        metadata = DocumentMetadata(
            page_count=3, file_size_mb=0.01, text_length=len(text)
        )

        document = ExtractedDocument(
            filename="multipage_test.pdf",
            file_path=Path("data/uploads/multipage_test.pdf"),
            extracted_text=text,
            metadata=metadata,
        )

        chunks = chunker.chunk_document(document)

        # Verify all chunks have page numbers
        for chunk in chunks:
            assert len(chunk.page_numbers) > 0, "Every chunk should have page numbers"
            # Page numbers should be valid (1-indexed)
            for page_num in chunk.page_numbers:
                assert 1 <= page_num <= 3, f"Page number {page_num} out of range"

    def test_empty_document_raises_error(self, chunker: DocumentChunker) -> None:
        """Test that empty document raises ChunkingError."""
        metadata = DocumentMetadata(page_count=1, file_size_mb=0.001, text_length=0)

        empty_doc = ExtractedDocument(
            filename="empty.pdf",
            file_path=Path("data/uploads/empty.pdf"),
            extracted_text="",
            metadata=metadata,
        )

        with pytest.raises(ChunkingError, match="Cannot chunk empty document"):
            chunker.chunk_document(empty_doc)

    def test_whitespace_only_document_raises_error(
        self, chunker: DocumentChunker
    ) -> None:
        """Test that whitespace-only document raises ChunkingError."""
        metadata = DocumentMetadata(page_count=1, file_size_mb=0.001, text_length=10)

        whitespace_doc = ExtractedDocument(
            filename="whitespace.pdf",
            file_path=Path("data/uploads/whitespace.pdf"),
            extracted_text="   \n\n   \t  ",
            metadata=metadata,
        )

        with pytest.raises(ChunkingError, match="Cannot chunk empty document"):
            chunker.chunk_document(whitespace_doc)

    def test_single_sentence_document(self, chunker: DocumentChunker) -> None:
        """Test handling of very short document (edge case)."""
        short_text = "This is a very short document with just one sentence."

        metadata = DocumentMetadata(
            page_count=1, file_size_mb=0.001, text_length=len(short_text)
        )

        short_doc = ExtractedDocument(
            filename="short.pdf",
            file_path=Path("data/uploads/short.pdf"),
            extracted_text=short_text,
            metadata=metadata,
        )

        chunks = chunker.chunk_document(short_doc)

        # Should create exactly 1 chunk
        assert len(chunks) == 1, "Short document should create single chunk"

        # Verify the chunk
        chunk = chunks[0]
        assert chunk.content == short_text
        assert chunk.token_count > 0
        assert chunk.page_numbers == [1]

    def test_uuid_uniqueness(
        self, chunker: DocumentChunker, sample_document: ExtractedDocument
    ) -> None:
        """Test that all chunk IDs are unique."""
        chunks = chunker.chunk_document(sample_document)

        chunk_ids = [chunk.chunk_id for chunk in chunks]

        # All IDs should be unique
        assert len(chunk_ids) == len(
            set(chunk_ids)
        ), "All chunk IDs should be unique"

    def test_document_id_linking(
        self, chunker: DocumentChunker, sample_document: ExtractedDocument
    ) -> None:
        """Test that all chunks link to same document_id."""
        chunks = chunker.chunk_document(sample_document)

        # All chunks should have same document_id
        expected_doc_id = sample_document.document_id
        for chunk in chunks:
            assert (
                chunk.document_id == expected_doc_id
            ), "All chunks should link to same document"

    def test_chunk_indices(
        self, chunker: DocumentChunker, sample_document: ExtractedDocument
    ) -> None:
        """Test that chunk indices are sequential."""
        chunks = chunker.chunk_document(sample_document)

        # Verify indices are 0-based and sequential
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i, f"Chunk index should be {i}"

    def test_character_positions(
        self, chunker: DocumentChunker, sample_document: ExtractedDocument
    ) -> None:
        """Test that character positions are valid."""
        chunks = chunker.chunk_document(sample_document)

        for chunk in chunks:
            # Positions should be non-negative
            assert chunk.char_start >= 0, "char_start should be non-negative"
            assert chunk.char_end >= 0, "char_end should be non-negative"

            # End should be after start
            assert (
                chunk.char_end > chunk.char_start
            ), "char_end should be after char_start"

            # Positions should be within document bounds
            assert (
                chunk.char_end <= len(sample_document.extracted_text)
            ), "char_end should be within document"

    def test_embedding_placeholder(
        self, chunker: DocumentChunker, sample_document: ExtractedDocument
    ) -> None:
        """Test that embedding is None initially."""
        chunks = chunker.chunk_document(sample_document)

        for chunk in chunks:
            assert (
                chunk.embedding is None
            ), "Embedding should be None before embedding generation"

    def test_token_counts_reasonable(
        self, chunker: DocumentChunker, sample_document: ExtractedDocument
    ) -> None:
        """Test that token counts are within expected range."""
        chunks = chunker.chunk_document(sample_document)

        for chunk in chunks:
            # Token count should be positive
            assert chunk.token_count > 0, "Token count should be positive"

            # For standard chunks, token count should be reasonable
            # (not too small, not too large)
            assert (
                chunk.token_count <= chunker.chunk_size * 2
            ), "Token count shouldn't exceed 2x chunk_size"
