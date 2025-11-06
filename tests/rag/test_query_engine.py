"""Unit tests for RAGQueryEngine."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.rag.embedder import EmbeddingGenerator
from src.rag.exceptions import QueryError
from src.rag.models import QueryResult, SourceCitation
from src.rag.query_engine import RAGQueryEngine
from src.rag.vector_store import VectorStoreManager


class TestRAGQueryEngine:
    """Test suite for RAGQueryEngine."""

    @pytest.fixture
    def mock_vector_store(self) -> Mock:
        """Create a mocked VectorStoreManager."""
        mock_store = Mock(spec=VectorStoreManager)
        mock_store.search.return_value = []
        return mock_store

    @pytest.fixture
    def mock_embedder(self) -> Mock:
        """Create a mocked EmbeddingGenerator."""
        mock_embedder = Mock(spec=EmbeddingGenerator)
        mock_embedder.embed_query.return_value = [0.1] * 1536
        return mock_embedder

    @pytest.fixture
    def query_engine(
        self, mock_vector_store: Mock, mock_embedder: Mock
    ) -> RAGQueryEngine:
        """Create RAGQueryEngine with mocked dependencies."""
        return RAGQueryEngine(
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            primary_llm="gpt-4-turbo-preview",
            fallback_llm="gpt-3.5-turbo",
            temperature=0.0,
            max_tokens=2000,
            top_k=5,
            min_score=0.7,
        )

    @pytest.fixture
    def mock_search_results(self) -> list[dict]:
        """Create mock search results from vector store."""
        doc_id = str(uuid4())
        return [
            {
                "chunk_id": str(uuid4()),
                "score": 0.95,
                "document_id": doc_id,
                "content": "The company reported revenue of $10 million in Q4 2023.",
                "page_numbers": [1],
            },
            {
                "chunk_id": str(uuid4()),
                "score": 0.88,
                "document_id": doc_id,
                "content": "Operating expenses decreased by 15% compared to previous quarter.",
                "page_numbers": [2],
            },
            {
                "chunk_id": str(uuid4()),
                "score": 0.82,
                "document_id": doc_id,
                "content": "Net profit margin improved from 12% to 18% year-over-year.",
                "page_numbers": [3, 4],
            },
        ]

    @pytest.fixture
    def mock_llm_response(self) -> Mock:
        """Create mock LLM response matching OpenAI structure."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Based on the financial documents, the company reported revenue of $10 million in Q4 2023 [Page 1]. Operating expenses decreased by 15% [Page 2], resulting in improved profit margins [Page 3-4]."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        return mock_response

    def test_initialization_success(
        self, mock_vector_store: Mock, mock_embedder: Mock
    ) -> None:
        """Test successful initialization with valid parameters."""
        engine = RAGQueryEngine(
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            primary_llm="gpt-4-turbo-preview",
            fallback_llm="gpt-3.5-turbo",
            temperature=0.5,
            max_tokens=1000,
            top_k=10,
            min_score=0.8,
        )

        assert engine.vector_store == mock_vector_store
        assert engine.embedder == mock_embedder
        assert engine.primary_llm == "gpt-4-turbo-preview"
        assert engine.fallback_llm == "gpt-3.5-turbo"
        assert engine.temperature == 0.5
        assert engine.max_tokens == 1000
        assert engine.top_k == 10
        assert engine.min_score == 0.8

    def test_initialization_empty_primary_llm_raises_error(
        self, mock_vector_store: Mock, mock_embedder: Mock
    ) -> None:
        """Test that empty primary_llm raises ValueError."""
        with pytest.raises(ValueError, match="primary_llm cannot be empty"):
            RAGQueryEngine(
                vector_store=mock_vector_store,
                embedder=mock_embedder,
                primary_llm="",
                fallback_llm="gpt-3.5-turbo",
            )

    def test_initialization_empty_fallback_llm_raises_error(
        self, mock_vector_store: Mock, mock_embedder: Mock
    ) -> None:
        """Test that empty fallback_llm raises ValueError."""
        with pytest.raises(ValueError, match="fallback_llm cannot be empty"):
            RAGQueryEngine(
                vector_store=mock_vector_store,
                embedder=mock_embedder,
                primary_llm="gpt-4-turbo-preview",
                fallback_llm="",
            )

    def test_initialization_invalid_temperature_raises_error(
        self, mock_vector_store: Mock, mock_embedder: Mock
    ) -> None:
        """Test that temperature outside 0.0-1.0 range raises ValueError."""
        with pytest.raises(ValueError, match="temperature must be between 0.0 and 1.0"):
            RAGQueryEngine(
                vector_store=mock_vector_store,
                embedder=mock_embedder,
                primary_llm="gpt-4-turbo-preview",
                fallback_llm="gpt-3.5-turbo",
                temperature=1.5,
            )

    def test_initialization_negative_max_tokens_raises_error(
        self, mock_vector_store: Mock, mock_embedder: Mock
    ) -> None:
        """Test that negative max_tokens raises ValueError."""
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            RAGQueryEngine(
                vector_store=mock_vector_store,
                embedder=mock_embedder,
                primary_llm="gpt-4-turbo-preview",
                fallback_llm="gpt-3.5-turbo",
                max_tokens=-100,
            )

    def test_initialization_invalid_top_k_raises_error(
        self, mock_vector_store: Mock, mock_embedder: Mock
    ) -> None:
        """Test that non-positive top_k raises ValueError."""
        with pytest.raises(ValueError, match="top_k must be positive"):
            RAGQueryEngine(
                vector_store=mock_vector_store,
                embedder=mock_embedder,
                primary_llm="gpt-4-turbo-preview",
                fallback_llm="gpt-3.5-turbo",
                top_k=0,
            )

    def test_initialization_invalid_min_score_raises_error(
        self, mock_vector_store: Mock, mock_embedder: Mock
    ) -> None:
        """Test that min_score outside 0.0-1.0 range raises ValueError."""
        with pytest.raises(ValueError, match="min_score must be between 0.0 and 1.0"):
            RAGQueryEngine(
                vector_store=mock_vector_store,
                embedder=mock_embedder,
                primary_llm="gpt-4-turbo-preview",
                fallback_llm="gpt-3.5-turbo",
                min_score=1.5,
            )

    @patch("src.rag.query_engine.completion")
    def test_query_success_with_relevant_chunks(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_search_results: list[dict],
        mock_llm_response: Mock,
    ) -> None:
        """Test successful query with relevant chunks returned."""
        # Setup mocks
        query_engine.vector_store.search.return_value = mock_search_results
        mock_completion.return_value = mock_llm_response

        # Execute query
        question = "What were the Q4 2023 financial results?"
        result = query_engine.query(question)

        # Verify embedder was called
        query_engine.embedder.embed_query.assert_called_once_with(question)

        # Verify vector store search was called
        query_engine.vector_store.search.assert_called_once()
        search_call_args = query_engine.vector_store.search.call_args
        assert search_call_args.kwargs["top_k"] == 5
        assert search_call_args.kwargs["min_score"] == 0.7

        # Verify LLM was called with correct parameters
        mock_completion.assert_called_once()
        llm_call_args = mock_completion.call_args
        assert llm_call_args.kwargs["model"] == "gpt-4-turbo-preview"
        assert llm_call_args.kwargs["temperature"] == 0.0
        assert llm_call_args.kwargs["max_tokens"] == 2000
        assert llm_call_args.kwargs["fallbacks"] == [
            {"gpt-4-turbo-preview": ["gpt-3.5-turbo"]}
        ]

        # Verify result structure
        assert isinstance(result, QueryResult)
        assert result.success is True
        assert result.answer is not None
        assert len(result.answer) > 0
        assert result.chunks_retrieved == 3
        assert len(result.sources) == 3
        assert result.query_time_seconds > 0
        assert result.error_message is None

        # Verify sources
        for i, source in enumerate(result.sources):
            assert isinstance(source, SourceCitation)
            assert source.document_id == mock_search_results[i]["document_id"]
            assert source.page_numbers == mock_search_results[i]["page_numbers"]
            assert source.relevance_score == mock_search_results[i]["score"]
            assert len(source.snippet) <= 200  # Should be truncated to 200 chars

    @patch("src.rag.query_engine.completion")
    def test_query_no_relevant_chunks(
        self, mock_completion: Mock, query_engine: RAGQueryEngine
    ) -> None:
        """Test query with no relevant chunks returns refusal message."""
        # Setup mock to return no results
        query_engine.vector_store.search.return_value = []

        # Execute query
        question = "What is the weather today?"
        result = query_engine.query(question)

        # Verify embedder was called
        query_engine.embedder.embed_query.assert_called_once_with(question)

        # Verify vector store search was called
        query_engine.vector_store.search.assert_called_once()

        # Verify LLM was NOT called
        mock_completion.assert_not_called()

        # Verify result
        assert result.success is True
        assert (
            result.answer
            == "I don't have enough information in the documents to answer that question."
        )
        assert result.sources == []
        assert result.chunks_retrieved == 0
        assert result.error_message is None

    @patch("src.rag.query_engine.completion")
    def test_query_source_citation_extraction(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_search_results: list[dict],
        mock_llm_response: Mock,
    ) -> None:
        """Test that source citations are correctly extracted from search results."""
        query_engine.vector_store.search.return_value = mock_search_results
        mock_completion.return_value = mock_llm_response

        result = query_engine.query("What were the financial results?")

        # Verify all sources were extracted
        assert len(result.sources) == 3

        # Verify first source details
        source_1 = result.sources[0]
        assert source_1.document_id == mock_search_results[0]["document_id"]
        assert source_1.page_numbers == [1]
        assert source_1.relevance_score == 0.95
        assert (
            source_1.snippet
            == "The company reported revenue of $10 million in Q4 2023."
        )

        # Verify second source
        source_2 = result.sources[1]
        assert source_2.page_numbers == [2]
        assert source_2.relevance_score == 0.88

        # Verify third source (multi-page)
        source_3 = result.sources[2]
        assert source_3.page_numbers == [3, 4]
        assert source_3.relevance_score == 0.82

    @patch("src.rag.query_engine.completion")
    def test_query_llm_fallback_on_primary_failure(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_search_results: list[dict],
        mock_llm_response: Mock,
    ) -> None:
        """Test LLM fallback mechanism when primary model fails."""
        query_engine.vector_store.search.return_value = mock_search_results
        # Mock completion to succeed (litellm handles fallback internally)
        mock_completion.return_value = mock_llm_response

        result = query_engine.query("What were the results?")

        # Verify fallback configuration was passed to litellm
        llm_call_args = mock_completion.call_args
        assert llm_call_args.kwargs["fallbacks"] == [
            {"gpt-4-turbo-preview": ["gpt-3.5-turbo"]}
        ]

        # Verify query still succeeded
        assert result.success is True
        assert result.answer is not None

    @patch("src.rag.query_engine.completion")
    def test_query_prompt_template_includes_guardrails(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_search_results: list[dict],
        mock_llm_response: Mock,
    ) -> None:
        """Test that system prompt includes proper guardrails."""
        query_engine.vector_store.search.return_value = mock_search_results
        mock_completion.return_value = mock_llm_response

        query_engine.query("What were the results?")

        # Get the prompt that was sent to LLM
        llm_call_args = mock_completion.call_args
        messages = llm_call_args.kwargs["messages"]
        prompt = messages[0]["content"]

        # Verify guardrails are present in prompt
        assert "financial document analysis assistant" in prompt
        assert "based ONLY on the provided context" in prompt
        assert "Only use information from the context" in prompt
        assert "Cite sources using [Page X]" in prompt
        assert (
            "I don't have enough information in the documents to answer that question."
            in prompt
        )
        assert "Do not make up or infer information" in prompt

        # Verify context is included
        assert "[Page 1]" in prompt
        assert "[Page 2]" in prompt
        assert "[Page 3-4]" in prompt  # Multi-page citation
        assert mock_search_results[0]["content"] in prompt
        assert mock_search_results[1]["content"] in prompt
        assert mock_search_results[2]["content"] in prompt

    def test_query_empty_question_raises_error(
        self, query_engine: RAGQueryEngine
    ) -> None:
        """Test that empty question raises ValueError."""
        with pytest.raises(ValueError, match="Question cannot be empty"):
            query_engine.query("")

    def test_query_whitespace_question_raises_error(
        self, query_engine: RAGQueryEngine
    ) -> None:
        """Test that whitespace-only question raises ValueError."""
        with pytest.raises(ValueError, match="Question cannot be empty"):
            query_engine.query("   \n\t  ")

    def test_query_embedder_failure_raises_query_error(
        self, query_engine: RAGQueryEngine
    ) -> None:
        """Test that embedder failure raises QueryError."""
        query_engine.embedder.embed_query.side_effect = Exception(
            "Embedding API failed"
        )

        with pytest.raises(QueryError, match="Failed to embed query"):
            query_engine.query("What are the results?")

    def test_query_vector_store_failure_raises_query_error(
        self, query_engine: RAGQueryEngine
    ) -> None:
        """Test that vector store failure raises QueryError."""
        query_engine.vector_store.search.side_effect = Exception(
            "Qdrant connection failed"
        )

        with pytest.raises(QueryError, match="Failed to search vector store"):
            query_engine.query("What are the results?")

    @patch("src.rag.query_engine.completion")
    def test_query_llm_failure_raises_query_error(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_search_results: list[dict],
    ) -> None:
        """Test that LLM failure raises QueryError."""
        query_engine.vector_store.search.return_value = mock_search_results
        mock_completion.side_effect = Exception("OpenAI API error")

        with pytest.raises(QueryError, match="Failed to generate answer from LLM"):
            query_engine.query("What are the results?")

    @patch("src.rag.query_engine.completion")
    def test_query_llm_invalid_response_no_choices(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_search_results: list[dict],
    ) -> None:
        """Test handling of invalid LLM response with no choices."""
        query_engine.vector_store.search.return_value = mock_search_results

        # Mock response without choices
        mock_response = Mock()
        mock_response.choices = []
        mock_completion.return_value = mock_response

        with pytest.raises(QueryError, match="Invalid LLM response: no choices returned"):
            query_engine.query("What are the results?")

    @patch("src.rag.query_engine.completion")
    def test_query_llm_invalid_response_empty_answer(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_search_results: list[dict],
    ) -> None:
        """Test handling of invalid LLM response with empty answer."""
        query_engine.vector_store.search.return_value = mock_search_results

        # Mock response with empty content
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = ""
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_completion.return_value = mock_response

        with pytest.raises(QueryError, match="Invalid LLM response: empty answer"):
            query_engine.query("What are the results?")

    @patch("src.rag.query_engine.completion")
    def test_query_llm_missing_choices_attribute(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_search_results: list[dict],
    ) -> None:
        """Test handling of LLM response without choices attribute."""
        query_engine.vector_store.search.return_value = mock_search_results

        # Mock response without choices attribute
        mock_response = Mock(spec=[])  # No attributes
        mock_completion.return_value = mock_response

        with pytest.raises(QueryError, match="Invalid LLM response: no choices returned"):
            query_engine.query("What are the results?")

    @patch("src.rag.query_engine.completion")
    def test_query_context_formatting_single_page(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_llm_response: Mock,
    ) -> None:
        """Test context formatting for single-page citations."""
        # Create search result with single page
        search_results = [
            {
                "chunk_id": str(uuid4()),
                "score": 0.95,
                "document_id": str(uuid4()),
                "content": "Revenue was $10M.",
                "page_numbers": [5],
            }
        ]

        query_engine.vector_store.search.return_value = search_results
        mock_completion.return_value = mock_llm_response

        query_engine.query("What was the revenue?")

        # Verify context format
        llm_call_args = mock_completion.call_args
        prompt = llm_call_args.kwargs["messages"][0]["content"]
        assert "[Page 5]: Revenue was $10M." in prompt

    @patch("src.rag.query_engine.completion")
    def test_query_context_formatting_multi_page(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_llm_response: Mock,
    ) -> None:
        """Test context formatting for multi-page citations."""
        # Create search result spanning multiple pages
        search_results = [
            {
                "chunk_id": str(uuid4()),
                "score": 0.95,
                "document_id": str(uuid4()),
                "content": "Financial analysis spanning multiple pages.",
                "page_numbers": [7, 8, 9],
            }
        ]

        query_engine.vector_store.search.return_value = search_results
        mock_completion.return_value = mock_llm_response

        query_engine.query("What is the financial analysis?")

        # Verify context format uses range notation
        llm_call_args = mock_completion.call_args
        prompt = llm_call_args.kwargs["messages"][0]["content"]
        assert "[Page 7-9]: Financial analysis spanning multiple pages." in prompt

    @patch("src.rag.query_engine.completion")
    def test_query_snippet_truncation(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_llm_response: Mock,
    ) -> None:
        """Test that snippets are truncated to 200 characters."""
        # Create search result with long content (>200 chars)
        long_content = "A" * 300  # 300 characters
        search_results = [
            {
                "chunk_id": str(uuid4()),
                "score": 0.95,
                "document_id": str(uuid4()),
                "content": long_content,
                "page_numbers": [1],
            }
        ]

        query_engine.vector_store.search.return_value = search_results
        mock_completion.return_value = mock_llm_response

        result = query_engine.query("What is this about?")

        # Verify snippet is truncated
        assert len(result.sources[0].snippet) == 200
        assert result.sources[0].snippet == "A" * 200

    @patch("src.rag.query_engine.completion")
    def test_query_timing_measurement(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_search_results: list[dict],
        mock_llm_response: Mock,
    ) -> None:
        """Test that query execution time is measured."""
        query_engine.vector_store.search.return_value = mock_search_results
        mock_completion.return_value = mock_llm_response

        result = query_engine.query("What are the results?")

        # Verify timing is recorded
        assert result.query_time_seconds > 0
        assert result.query_time_seconds < 10  # Should complete quickly in tests

    @patch("src.rag.query_engine.completion")
    def test_query_with_custom_parameters(
        self, mock_completion: Mock, mock_vector_store: Mock, mock_embedder: Mock
    ) -> None:
        """Test query engine with custom configuration parameters."""
        # Create engine with custom parameters
        custom_engine = RAGQueryEngine(
            vector_store=mock_vector_store,
            embedder=mock_embedder,
            primary_llm="gpt-4",
            fallback_llm="gpt-3.5-turbo-16k",
            temperature=0.7,
            max_tokens=500,
            top_k=3,
            min_score=0.85,
        )

        # Setup mocks
        search_results = [
            {
                "chunk_id": str(uuid4()),
                "score": 0.90,
                "document_id": str(uuid4()),
                "content": "Test content.",
                "page_numbers": [1],
            }
        ]
        mock_vector_store.search.return_value = search_results

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Test answer."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_completion.return_value = mock_response

        custom_engine.query("Test question?")

        # Verify custom parameters were used
        search_call_args = mock_vector_store.search.call_args
        assert search_call_args.kwargs["top_k"] == 3
        assert search_call_args.kwargs["min_score"] == 0.85

        llm_call_args = mock_completion.call_args
        assert llm_call_args.kwargs["model"] == "gpt-4"
        assert llm_call_args.kwargs["temperature"] == 0.7
        assert llm_call_args.kwargs["max_tokens"] == 500
        assert llm_call_args.kwargs["fallbacks"] == [{"gpt-4": ["gpt-3.5-turbo-16k"]}]

    @patch("src.rag.query_engine.completion")
    def test_query_multiple_documents_in_results(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_llm_response: Mock,
    ) -> None:
        """Test query with results from multiple different documents."""
        doc_id_1 = str(uuid4())
        doc_id_2 = str(uuid4())

        search_results = [
            {
                "chunk_id": str(uuid4()),
                "score": 0.95,
                "document_id": doc_id_1,
                "content": "Content from document 1.",
                "page_numbers": [1],
            },
            {
                "chunk_id": str(uuid4()),
                "score": 0.88,
                "document_id": doc_id_2,
                "content": "Content from document 2.",
                "page_numbers": [1],
            },
        ]

        query_engine.vector_store.search.return_value = search_results
        mock_completion.return_value = mock_llm_response

        result = query_engine.query("What information is available?")

        # Verify sources from both documents
        assert len(result.sources) == 2
        assert result.sources[0].document_id == doc_id_1
        assert result.sources[1].document_id == doc_id_2

    @patch("src.rag.query_engine.completion")
    def test_query_preserves_search_result_order(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_search_results: list[dict],
        mock_llm_response: Mock,
    ) -> None:
        """Test that search result order is preserved in sources."""
        query_engine.vector_store.search.return_value = mock_search_results
        mock_completion.return_value = mock_llm_response

        result = query_engine.query("What are the results?")

        # Verify order is preserved (highest score first)
        assert result.sources[0].relevance_score == 0.95
        assert result.sources[1].relevance_score == 0.88
        assert result.sources[2].relevance_score == 0.82

    def test_query_error_wrapping(self, query_engine: RAGQueryEngine) -> None:
        """Test that unexpected errors are wrapped in QueryError."""
        # Mock an unexpected error type
        query_engine.embedder.embed_query.side_effect = RuntimeError(
            "Unexpected error"
        )

        with pytest.raises(QueryError, match="Failed to embed query"):
            query_engine.query("What are the results?")

    def test_create_prompt_template_structure(
        self, query_engine: RAGQueryEngine
    ) -> None:
        """Test the structure of the prompt template."""
        context = "[Page 1]: Test content."
        question = "What is the test content?"

        prompt = query_engine._create_prompt_template(context, question)

        # Verify key components are present
        assert "financial document analysis assistant" in prompt
        assert "RULES:" in prompt
        assert "CONTEXT:" in prompt
        assert "QUESTION:" in prompt
        assert "ANSWER:" in prompt
        assert context in prompt
        assert question in prompt

    @patch("src.rag.query_engine.completion")
    def test_query_success_returns_correct_chunks_count(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_llm_response: Mock,
    ) -> None:
        """Test that chunks_retrieved count matches search results."""
        # Test with different result counts
        for num_results in [1, 3, 5, 10]:
            search_results = []
            for i in range(num_results):
                search_results.append(
                    {
                        "chunk_id": str(uuid4()),
                        "score": 0.9 - i * 0.05,
                        "document_id": str(uuid4()),
                        "content": f"Content {i}",
                        "page_numbers": [i + 1],
                    }
                )

            query_engine.vector_store.search.return_value = search_results
            mock_completion.return_value = mock_llm_response

            result = query_engine.query(f"Test query {num_results}")

            assert result.chunks_retrieved == num_results
            assert len(result.sources) == num_results

    @patch("src.rag.query_engine.completion")
    def test_query_with_special_characters_in_content(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_llm_response: Mock,
    ) -> None:
        """Test query handling content with special characters."""
        search_results = [
            {
                "chunk_id": str(uuid4()),
                "score": 0.95,
                "document_id": str(uuid4()),
                "content": "Revenue: $10M, Profit: 25%, Growth: +15% Y/Y (Q4'23).",
                "page_numbers": [1],
            }
        ]

        query_engine.vector_store.search.return_value = search_results
        mock_completion.return_value = mock_llm_response

        result = query_engine.query("What were the metrics?")

        # Verify special characters are preserved
        assert result.success is True
        assert (
            "$10M" in result.sources[0].snippet
            or "10M" in result.sources[0].snippet
        )

    @patch("src.rag.query_engine.completion")
    def test_query_long_question(
        self,
        mock_completion: Mock,
        query_engine: RAGQueryEngine,
        mock_search_results: list[dict],
        mock_llm_response: Mock,
    ) -> None:
        """Test query with very long question text."""
        query_engine.vector_store.search.return_value = mock_search_results
        mock_completion.return_value = mock_llm_response

        # Create a very long question
        long_question = (
            "What were the detailed quarterly financial results including revenue, "
            "expenses, profit margins, cash flow, and year-over-year growth rates "
            "for Q4 2023 compared to previous quarters and how do these metrics "
            "compare to industry benchmarks and competitor performance?"
        )

        result = query_engine.query(long_question)

        # Verify query succeeded
        assert result.success is True
        assert result.answer is not None

        # Verify embedder received full question
        query_engine.embedder.embed_query.assert_called_with(long_question)
