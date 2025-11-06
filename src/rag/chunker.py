"""Document chunking for RAG processing."""

import logging
import uuid

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.pdf_processor.models import ExtractedDocument
from src.rag import ChunkingError, DocumentChunk

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Chunks documents into overlapping segments for vector embedding.

    Uses LangChain's RecursiveCharacterTextSplitter to split documents
    while preserving semantic structure (paragraphs → sentences → words).
    Tracks page numbers for source citation.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int):
        """Initialize the document chunker.

        Args:
            chunk_size: Target number of tokens per chunk
            chunk_overlap: Number of overlapping tokens between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize RecursiveCharacterTextSplitter
        # Hierarchical splitting: paragraphs → sentences → words
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " "],
            length_function=len,  # Character-based for initial split
        )

        # Initialize tiktoken encoder for accurate token counting
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        logger.debug(
            f"DocumentChunker initialized: chunk_size={chunk_size}, chunk_overlap={chunk_overlap}"
        )

    def chunk_document(self, document: ExtractedDocument) -> list[DocumentChunk]:
        """Split document into chunks with metadata.

        Args:
            document: The extracted document to chunk

        Returns:
            List of DocumentChunk objects with embeddings placeholder

        Raises:
            ChunkingError: If document is empty or has no valid text
        """
        logger.info(f"Creating chunks for document {document.filename}")

        # Validate document has text content
        if not document.extracted_text or len(document.extracted_text.strip()) == 0:
            raise ChunkingError("Cannot chunk empty document")

        # Log warning for very short documents
        if len(document.extracted_text) < self.chunk_size:
            logger.warning(
                f"Document {document.filename} is shorter than chunk_size "
                f"({len(document.extracted_text)} < {self.chunk_size} chars)"
            )

        # Split text into chunks using RecursiveCharacterTextSplitter
        text_chunks = self.splitter.split_text(document.extracted_text)

        # Build page mapping for character positions
        page_char_map = self._build_page_char_map(
            document.extracted_text, document.metadata.page_count
        )

        # Create DocumentChunk objects with metadata
        chunks: list[DocumentChunk] = []
        current_position = 0

        for chunk_index, chunk_text in enumerate(text_chunks):
            # Find chunk position in original text
            char_start = document.extracted_text.find(chunk_text, current_position)
            if char_start == -1:
                # Fallback: if exact match not found, use current position
                logger.warning(
                    f"Chunk {chunk_index} not found in original text, using position approximation"
                )
                char_start = current_position

            char_end = char_start + len(chunk_text)

            # Map character positions to page numbers
            page_numbers = self._get_page_numbers(char_start, char_end, page_char_map)

            # Count tokens using tiktoken
            token_count = len(self.tokenizer.encode(chunk_text))

            # Create chunk object
            chunk = DocumentChunk(
                content=chunk_text,
                chunk_id=str(uuid.uuid4()),
                document_id=document.document_id,
                chunk_index=chunk_index,
                page_numbers=page_numbers,
                char_start=char_start,
                char_end=char_end,
                token_count=token_count,
                embedding=None,  # Will be populated by EmbeddingGenerator
            )

            chunks.append(chunk)

            # Update position for next chunk search
            current_position = char_start + 1

        logger.info(
            f"Created {len(chunks)} chunks from {document.filename} "
            f"(avg {sum(c.token_count for c in chunks) / len(chunks):.0f} tokens/chunk)"
        )

        return chunks

    def _build_page_char_map(self, text: str, page_count: int) -> list[tuple[int, int]]:
        """Build mapping of character positions to page numbers.

        The PDF extractor concatenates pages with '\n\n', so we need to
        reconstruct page boundaries from the combined text.

        Args:
            text: Full document text
            page_count: Number of pages in document

        Returns:
            List of (start_char, end_char) tuples for each page
        """
        # Split by page separator to reconstruct pages
        page_separator = "\n\n"
        pages = text.split(page_separator)

        # If we don't have the expected number of pages, create equal distribution
        if len(pages) != page_count:
            logger.warning(
                f"Page split mismatch: found {len(pages)} segments, "
                f"expected {page_count} pages. Using estimation."
            )
            # Fall back to equal distribution
            chars_per_page = len(text) // page_count if page_count > 0 else len(text)
            return [
                (i * chars_per_page, min((i + 1) * chars_per_page, len(text)))
                for i in range(page_count)
            ]

        # Build character position map for each page
        page_char_map: list[tuple[int, int]] = []
        current_pos = 0

        for page_text in pages:
            start_char = current_pos
            end_char = start_char + len(page_text)
            page_char_map.append((start_char, end_char))

            # Add separator length for next page (except last page)
            current_pos = end_char + len(page_separator)

        return page_char_map

    def _get_page_numbers(
        self, char_start: int, char_end: int, page_char_map: list[tuple[int, int]]
    ) -> list[int]:
        """Determine which pages a chunk spans.

        Args:
            char_start: Starting character position
            char_end: Ending character position
            page_char_map: List of (start, end) tuples for each page

        Returns:
            List of page numbers (1-indexed) that this chunk spans
        """
        page_numbers: list[int] = []

        for page_num, (page_start, page_end) in enumerate(page_char_map, start=1):
            # Check if chunk overlaps with this page
            if char_start < page_end and char_end > page_start:
                page_numbers.append(page_num)

        # Ensure we always have at least one page
        if not page_numbers:
            logger.warning(
                f"Chunk at position {char_start}-{char_end} mapped to no pages, "
                "defaulting to page 1"
            )
            page_numbers = [1]

        return page_numbers
