"""RAG Query Engine for answering questions about documents."""

import logging
import time

from litellm import completion

from src.rag.embedder import EmbeddingGenerator
from src.rag.exceptions import QueryError
from src.rag.models import QueryResult, SourceCitation
from src.rag.vector_store import VectorStoreManager

logger = logging.getLogger(__name__)


class RAGQueryEngine:
    """Query engine for answering questions using RAG (Retrieval-Augmented Generation).

    This class implements a complete RAG pipeline that:
    1. Embeds user queries
    2. Retrieves relevant document chunks from vector store
    3. Generates answers using LLM with context
    4. Returns answers with source citations

    The engine uses LiteLLM for LLM calls with automatic fallback support,
    ensuring high availability by falling back to alternative models when
    the primary model is unavailable.

    Attributes:
        vector_store: VectorStoreManager for retrieving relevant chunks
        embedder: EmbeddingGenerator for converting queries to embeddings
        primary_llm: Primary LLM model to use (e.g., "gpt-4-turbo-preview")
        fallback_llm: Fallback LLM model (e.g., "gpt-3.5-turbo")
        temperature: LLM temperature for response generation (0.0 = deterministic)
        max_tokens: Maximum tokens in generated response
        top_k: Number of chunks to retrieve from vector store
        min_score: Minimum similarity score threshold for chunk relevance
    """

    def __init__(
        self,
        vector_store: VectorStoreManager,
        embedder: EmbeddingGenerator,
        primary_llm: str,
        fallback_llm: str,
        temperature: float = 0.0,
        max_tokens: int = 2000,
        top_k: int = 5,
        min_score: float = 0.7,
    ) -> None:
        """Initialize the RAG query engine with dependencies and configuration.

        Args:
            vector_store: Manager for vector database operations
            embedder: Generator for creating query embeddings
            primary_llm: Primary LLM model identifier (e.g., "gpt-4-turbo-preview")
            fallback_llm: Fallback LLM model identifier (e.g., "gpt-3.5-turbo")
            temperature: LLM sampling temperature (0.0-1.0, default: 0.0)
            max_tokens: Maximum tokens in generated response (default: 2000)
            top_k: Number of chunks to retrieve (default: 5)
            min_score: Minimum similarity score threshold (default: 0.7)

        Raises:
            ValueError: If any required parameter is invalid
        """
        if not primary_llm:
            raise ValueError("primary_llm cannot be empty")
        if not fallback_llm:
            raise ValueError("fallback_llm cannot be empty")
        if not 0.0 <= temperature <= 1.0:
            raise ValueError(f"temperature must be between 0.0 and 1.0, got {temperature}")
        if max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {max_tokens}")
        if top_k <= 0:
            raise ValueError(f"top_k must be positive, got {top_k}")
        if not 0.0 <= min_score <= 1.0:
            raise ValueError(f"min_score must be between 0.0 and 1.0, got {min_score}")

        self.vector_store = vector_store
        self.embedder = embedder
        self.primary_llm = primary_llm
        self.fallback_llm = fallback_llm
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_k = top_k
        self.min_score = min_score

        logger.info(
            f"Initialized RAGQueryEngine with primary_llm={primary_llm}, "
            f"fallback_llm={fallback_llm}, top_k={top_k}, min_score={min_score}"
        )

    def _create_prompt_template(self, context: str, question: str) -> str:
        """Create the prompt template with system instructions and guardrails.

        Constructs a prompt that instructs the LLM to answer questions based
        strictly on the provided context, with proper citation format and
        clear refusal when information is not available.

        Args:
            context: Formatted context from retrieved document chunks
            question: User's question to answer

        Returns:
            Complete prompt string ready for LLM input
        """
        prompt = f"""You are a financial document analysis assistant. Answer the question based ONLY on the provided context from financial documents.

RULES:
- Only use information from the context below
- Cite sources using [Page X] format in your answer
- If the context doesn't contain relevant information, say "I don't have enough information in the documents to answer that question."
- Be accurate and factual
- Do not make up or infer information that isn't explicitly stated in the context

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

        return prompt

    def query(
        self,
        question: str,
        session_id: str | None = None,
    ) -> QueryResult:
        """Execute a RAG query to answer a question about documents.

        Implements the complete RAG pipeline:
        1. Embed the user's question
        2. Retrieve relevant chunks from vector store
        3. Check relevance threshold
        4. Format context with citations
        5. Generate answer using LLM
        6. Extract source citations
        7. Return structured result

        Args:
            question: User's question about the documents
            session_id: Browser session ID for query isolation

        Returns:
            QueryResult containing answer, sources, and metadata

        Raises:
            QueryError: If any step of the query pipeline fails
            ValueError: If question is empty
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        start_time = time.time()

        try:
            logger.info(f"Processing query: {question[:100]}...")

            # Step 1: Embed the query
            logger.info("Step 1: Embedding query")
            try:
                query_embedding = self.embedder.embed_query(question)
            except Exception as e:
                error_msg = f"Failed to embed query: {str(e)}"
                logger.error(error_msg)
                raise QueryError(error_msg) from e

            # Step 2: Search vector store for relevant chunks
            session_info = f", session_id={session_id[:8]}..." if session_id else ""
            logger.info(
                f"Step 2: Searching vector store (top_k={self.top_k}, "
                f"min_score={self.min_score}{session_info})"
            )
            try:
                search_results = self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=self.top_k,
                    min_score=self.min_score,
                    session_id=session_id,
                )
            except Exception as e:
                error_msg = f"Failed to search vector store: {str(e)}"
                logger.error(error_msg)
                raise QueryError(error_msg) from e

            chunks_retrieved = len(search_results)
            logger.info(f"Retrieved {chunks_retrieved} relevant chunks")

            # Step 3: Check if minimum relevance threshold is met
            if not search_results:
                logger.info("No relevant chunks found, returning no-information message")
                query_time = time.time() - start_time
                return QueryResult(
                    success=True,
                    answer="I don't have enough information in the documents to answer that question.",
                    sources=[],
                    chunks_retrieved=0,
                    query_time_seconds=query_time,
                    error_message=None,
                )

            # Step 4: Format context with page citations
            logger.info("Step 4: Formatting context with citations")
            context_parts: list[str] = []
            for result in search_results:
                pages = result["page_numbers"]
                content = result["content"]
                # Format: [Page X]: content or [Page X-Y]: content for ranges
                if len(pages) == 1:
                    page_citation = f"[Page {pages[0]}]"
                else:
                    page_citation = f"[Page {min(pages)}-{max(pages)}]"
                context_parts.append(f"{page_citation}: {content}")

            context = "\n\n".join(context_parts)
            logger.info(f"Formatted context with {len(context_parts)} chunks")

            # Step 5: Call LLM with fallback configuration
            logger.info(
                f"Step 5: Calling LLM (primary={self.primary_llm}, fallback={self.fallback_llm})"
            )
            prompt = self._create_prompt_template(context=context, question=question)

            try:
                response = completion(
                    model=self.primary_llm,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    fallbacks=[{self.primary_llm: [self.fallback_llm]}],
                )

                # Extract answer from response
                if not hasattr(response, "choices") or not response.choices:
                    raise QueryError("Invalid LLM response: no choices returned")

                answer = response.choices[0].message.content
                if not answer:
                    raise QueryError("Invalid LLM response: empty answer")

                logger.info("Successfully generated answer from LLM")

            except Exception as e:
                error_msg = f"Failed to generate answer from LLM: {str(e)}"
                logger.error(error_msg)
                raise QueryError(error_msg) from e

            # Step 6: Extract sources from retrieved chunks
            logger.info("Step 6: Extracting source citations")
            sources: list[SourceCitation] = []
            for result in search_results:
                citation = SourceCitation(
                    document_id=result["document_id"],
                    page_numbers=result["page_numbers"],
                    relevance_score=result["score"],
                    snippet=result["content"][:200],  # First 200 chars as snippet
                )
                sources.append(citation)

            logger.info(f"Extracted {len(sources)} source citations")

            # Step 7: Return QueryResult
            query_time = time.time() - start_time
            logger.info(f"Query completed successfully in {query_time:.2f}s")

            return QueryResult(
                success=True,
                answer=answer,
                sources=sources,
                chunks_retrieved=chunks_retrieved,
                query_time_seconds=query_time,
                error_message=None,
            )

        except QueryError:
            # Re-raise QueryError as-is
            raise
        except Exception as e:
            # Wrap unexpected errors in QueryError
            error_msg = f"Unexpected error during query processing: {str(e)}"
            logger.error(error_msg)
            raise QueryError(error_msg) from e
