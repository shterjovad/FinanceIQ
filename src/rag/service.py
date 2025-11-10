"""RAG service orchestration layer."""

import logging
import time
import traceback

from src.pdf_processor.models import ExtractedDocument
from src.rag.chunker import DocumentChunker
from src.rag.embedder import EmbeddingGenerator
from src.rag.models import QueryResult, RAGResult
from src.rag.query_engine import RAGQueryEngine
from src.rag.vector_store import VectorStoreManager

logger = logging.getLogger(__name__)


class RAGService:
    """Service layer orchestrating all RAG components.

    This class provides a high-level API for document processing and querying,
    coordinating the chunker, embedder, vector store, and query engine components.

    The service handles the complete document processing pipeline:
    1. Chunking documents into smaller segments
    2. Generating embeddings for each chunk
    3. Storing chunks in the vector database
    4. Querying the knowledge base with natural language questions

    Attributes:
        chunker: DocumentChunker for splitting documents into chunks
        embedder: EmbeddingGenerator for creating vector embeddings
        vector_store: VectorStoreManager for persisting and retrieving chunks
        query_engine: RAGQueryEngine for answering questions
    """

    def __init__(
        self,
        chunker: DocumentChunker,
        embedder: EmbeddingGenerator,
        vector_store: VectorStoreManager,
        query_engine: RAGQueryEngine,
    ) -> None:
        """Initialize RAG service with all dependencies.

        Args:
            chunker: Document chunking component
            embedder: Embedding generation component
            vector_store: Vector database manager
            query_engine: RAG query processing component
        """
        self.chunker = chunker
        self.embedder = embedder
        self.vector_store = vector_store
        self.query_engine = query_engine

        logger.info("RAGService initialized with all components")

    def process_document(self, document: ExtractedDocument) -> RAGResult:
        """Process a document through the complete RAG pipeline.

        This method orchestrates the following steps:
        1. Chunk the document into smaller segments
        2. Generate embeddings for each chunk
        3. Store chunks with embeddings in the vector database

        Args:
            document: The extracted document to process

        Returns:
            RAGResult containing processing status, statistics, and any error information
        """
        start_time = time.time()
        document_id = document.document_id

        logger.info(f"Starting RAG processing for document: {document.filename} (ID: {document_id})")

        try:
            # Step 1: Chunk the document
            logger.info(f"Step 1/3: Chunking document {document_id}")
            chunks = self.chunker.chunk_document(document)
            chunks_created = len(chunks)
            logger.info(f"Created {chunks_created} chunks for document {document_id}")

            # Step 2: Generate embeddings for chunks
            logger.info(f"Step 2/3: Generating embeddings for {chunks_created} chunks")
            chunks_with_embeddings = self.embedder.embed_chunks(chunks)
            logger.info(f"Generated embeddings for all {len(chunks_with_embeddings)} chunks")

            # Step 3: Store chunks in vector database
            logger.info(f"Step 3/3: Upserting {len(chunks_with_embeddings)} chunks to vector store")
            chunks_indexed = self.vector_store.upsert_chunks(chunks_with_embeddings)
            logger.info(f"Successfully indexed {chunks_indexed} chunks in vector store")

            # Calculate processing time
            processing_time = time.time() - start_time

            logger.info(
                f"Document {document_id} processed successfully in {processing_time:.2f}s "
                f"({chunks_created} chunks created, {chunks_indexed} chunks indexed)"
            )

            return RAGResult(
                success=True,
                document_id=document_id,
                chunks_created=chunks_created,
                chunks_indexed=chunks_indexed,
                processing_time_seconds=processing_time,
                error_message=None,
            )

        except Exception as e:
            # Calculate processing time even on failure
            processing_time = time.time() - start_time

            # Log full error with traceback
            error_msg = f"Failed to process document {document_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

            return RAGResult(
                success=False,
                document_id=document_id,
                chunks_created=0,
                chunks_indexed=0,
                processing_time_seconds=processing_time,
                error_message=error_msg,
            )

    def query(self, question: str) -> QueryResult:
        """Query the knowledge base with a natural language question.

        This is a simple delegation to the query engine, with added logging
        for monitoring and debugging purposes. The query engine handles
        the complete RAG query pipeline including retrieval and generation.

        Args:
            question: User's natural language question

        Returns:
            QueryResult containing the answer, source citations, and metadata

        Raises:
            QueryError: If query processing fails
            ValueError: If question is empty
        """
        logger.info(f"RAGService received query: {question[:100]}...")

        try:
            result = self.query_engine.query(question)
            logger.info(
                f"Query completed successfully in {result.query_time_seconds:.2f}s "
                f"({result.chunks_retrieved} chunks retrieved)"
            )
            return result

        except Exception as e:
            logger.error(f"Query failed: {str(e)}", exc_info=True)
            raise

    def delete_document(self, document_id: str) -> bool:
        """Delete all chunks associated with a document from the vector store.

        This method removes the document from the knowledge base by deleting
        all of its associated chunks from the vector database.

        Args:
            document_id: ID of the document to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        logger.info(f"RAGService received deletion request for document: {document_id}")

        try:
            result = self.vector_store.delete_document(document_id)

            if result:
                logger.info(f"Successfully deleted document {document_id} from vector store")
            else:
                logger.warning(f"Failed to delete document {document_id} from vector store")

            return result

        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}", exc_info=True)
            return False
