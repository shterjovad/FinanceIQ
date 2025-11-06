"""Embedding generation using LiteLLM for OpenAI embeddings."""

import logging
import time
from typing import Any

from litellm import embedding

from src.rag.exceptions import EmbeddingError
from src.rag.models import DocumentChunk

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings for document chunks and queries using LiteLLM.

    This class handles batch processing of document chunks and single query
    embeddings using OpenAI's embedding models via the LiteLLM library.
    Implements retry logic with exponential backoff for API resilience.

    Attributes:
        embedding_model: Name of the OpenAI embedding model (e.g., "text-embedding-3-small")
        api_key: OpenAI API key for authentication
        batch_size: Maximum number of chunks to process per API call (default: 100)
        max_retries: Number of retry attempts for failed API calls (default: 3)
    """

    def __init__(self, embedding_model: str, api_key: str) -> None:
        """Initialize the embedding generator with model configuration.

        Args:
            embedding_model: Name of the OpenAI embedding model to use
            api_key: OpenAI API key for authentication

        Raises:
            ValueError: If embedding_model or api_key is empty
        """
        if not embedding_model:
            raise ValueError("embedding_model cannot be empty")
        if not api_key:
            raise ValueError("api_key cannot be empty")

        self.embedding_model = embedding_model
        self.api_key = api_key
        self.batch_size = 100
        self.max_retries = 3

        logger.info(
            f"Initialized EmbeddingGenerator with model={embedding_model}, batch_size={self.batch_size}"
        )

    def embed_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """Generate embeddings for a list of document chunks with batch processing.

        Processes chunks in batches of up to 100 items to optimize API usage.
        Updates each chunk's embedding field in-place and returns the modified chunks.

        Args:
            chunks: List of DocumentChunk objects to embed

        Returns:
            The same list of chunks with updated embedding fields

        Raises:
            EmbeddingError: If embedding generation fails after all retries
            ValueError: If chunks list is empty
        """
        if not chunks:
            raise ValueError("Cannot embed empty list of chunks")

        total_chunks = len(chunks)
        logger.info(f"Starting embedding generation for {total_chunks} chunks")

        # Process chunks in batches
        for batch_start in range(0, total_chunks, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_chunks)
            batch = chunks[batch_start:batch_end]
            batch_num = (batch_start // self.batch_size) + 1
            total_batches = (total_chunks + self.batch_size - 1) // self.batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")

            # Extract text content for embedding
            texts = [chunk.content for chunk in batch]

            # Generate embeddings with retry logic
            embeddings = self._generate_embeddings_with_retry(texts)

            # Update chunk embeddings
            for chunk, emb in zip(batch, embeddings, strict=True):
                chunk.embedding = emb

        logger.info(f"Successfully embedded all {total_chunks} chunks")
        return chunks

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a single query string.

        Args:
            query: Query text to embed

        Returns:
            Embedding vector as a list of floats (dimension: 1536)

        Raises:
            EmbeddingError: If embedding generation fails after all retries
            ValueError: If query is empty
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        logger.info(f"Generating embedding for query: {query[:100]}...")

        # Generate embedding with retry logic
        embeddings = self._generate_embeddings_with_retry([query])

        logger.info("Successfully generated query embedding")
        return embeddings[0]

    def _generate_embeddings_with_retry(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings with exponential backoff retry logic.

        Attempts to generate embeddings up to max_retries times, with exponential
        backoff between attempts (1s, 2s, 4s).

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors, one per input text

        Raises:
            EmbeddingError: If all retry attempts fail
        """
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                # Call LiteLLM embedding function
                response = embedding(
                    model=self.embedding_model,
                    input=texts,
                    api_key=self.api_key,
                )

                # Extract embeddings from response
                embeddings = self._extract_embeddings_from_response(response)

                if attempt > 1:
                    logger.info(
                        f"Successfully generated embeddings on attempt {attempt}/{self.max_retries}"
                    )

                return embeddings

            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = 2 ** (attempt - 1)  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Embedding attempt {attempt}/{self.max_retries} failed: {str(e)}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries} embedding attempts failed. Last error: {str(e)}"
                    )

        # All retries exhausted
        error_msg = f"Failed to generate embeddings after {self.max_retries} attempts"
        if last_error:
            error_msg += f": {str(last_error)}"

        raise EmbeddingError(error_msg)

    def _extract_embeddings_from_response(self, response: Any) -> list[list[float]]:
        """Extract embedding vectors from LiteLLM API response.

        Args:
            response: Response object from LiteLLM embedding() call

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If response format is invalid or embeddings cannot be extracted
        """
        try:
            # LiteLLM returns a response object with a 'data' field
            # Each item in data has an 'embedding' field
            if not hasattr(response, "data"):
                raise EmbeddingError("Invalid response format: missing 'data' field")

            embeddings = []
            for item in response.data:
                if not hasattr(item, "embedding"):
                    raise EmbeddingError(
                        "Invalid response format: missing 'embedding' field in data item"
                    )
                embeddings.append(item.embedding)

            if not embeddings:
                raise EmbeddingError("No embeddings returned from API")

            return embeddings

        except EmbeddingError:
            raise
        except Exception as e:
            raise EmbeddingError(f"Failed to extract embeddings from response: {str(e)}") from e
