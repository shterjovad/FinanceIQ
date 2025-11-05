"""Pydantic data models for RAG operations."""

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """A chunk of document text with metadata."""

    content: str = Field(description="The text content of the chunk")
    chunk_id: str = Field(description="UUID for unique identification")
    document_id: str = Field(description="Links back to ExtractedDocument")
    chunk_index: int = Field(ge=0, description="Position in document (0-based)")
    page_numbers: list[int] = Field(description="Pages this chunk spans")
    char_start: int = Field(ge=0, description="Character position in original text")
    char_end: int = Field(ge=0, description="End character position in original text")
    token_count: int = Field(ge=0, description="Number of tokens in the chunk")
    embedding: list[float] | None = Field(
        default=None, description="1536-dimensional vector embedding"
    )


class SourceCitation(BaseModel):
    """Citation to source document."""

    document_id: str = Field(description="Document identifier")
    page_numbers: list[int] = Field(description="Page numbers referenced")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Cosine similarity score")
    snippet: str = Field(description="Actual text from document")


class QueryResult(BaseModel):
    """Result of a RAG query."""

    success: bool = Field(description="Whether the query was successful")
    answer: str = Field(description="Generated answer to the query")
    sources: list[SourceCitation] = Field(
        default_factory=list, description="Source citations for the answer"
    )
    chunks_retrieved: int = Field(ge=0, description="Number of chunks retrieved from vector store")
    query_time_seconds: float = Field(ge=0, description="Time taken to process query")
    error_message: str | None = Field(default=None, description="Error message if query failed")


class RAGResult(BaseModel):
    """Result of document processing for RAG."""

    success: bool = Field(description="Whether the processing was successful")
    document_id: str = Field(description="Document identifier")
    chunks_created: int = Field(ge=0, description="Number of chunks created")
    chunks_indexed: int = Field(ge=0, description="Number of chunks indexed")
    processing_time_seconds: float = Field(ge=0, description="Time taken to process document")
    error_message: str | None = Field(
        default=None, description="Error message if processing failed"
    )


class ChatMessage(BaseModel):
    """A message in the chat conversation."""

    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the message was created"
    )
    sources: list[SourceCitation] = Field(
        default_factory=list, description="Source citations for assistant messages"
    )
