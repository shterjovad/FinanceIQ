"""Application configuration using Pydantic Settings."""

from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with type validation and environment variable support."""

    # File upload settings
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_MIME_TYPES: list[str] = ["application/pdf"]

    # Directory settings
    UPLOAD_DIR: Path = Path("data/uploads")
    LOG_DIR: Path = Path("logs")

    # Logging settings
    LOG_LEVEL: str = "INFO"

    # === RAG SETTINGS ===

    # Document Chunking
    CHUNK_SIZE: int = 1000  # Target tokens per chunk
    CHUNK_OVERLAP: int = 200  # Overlap tokens for context preservation
    CHUNKING_SEPARATORS: list[str] = ["\n\n", "\n", ". ", " "]  # Hierarchical splitting

    # Vector Database (Qdrant)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "financial_docs"

    # LLM & Embeddings (via LiteLLM)
    OPENAI_API_KEY: str = ""  # Will be required for embeddings in Slice 3
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    PRIMARY_LLM: str = "gpt-4-turbo-preview"
    FALLBACK_LLM: str = "gpt-3.5-turbo"  # Fallback if rate limited
    LLM_TEMPERATURE: float = 0.0  # Deterministic for consistency
    LLM_MAX_TOKENS: int = 2000

    # Query Processing
    TOP_K_CHUNKS: int = 5  # Number of chunks to retrieve
    MIN_RELEVANCE_SCORE: float = 0.7  # Minimum similarity threshold

    # Pydantic configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @field_validator("UPLOAD_DIR", "LOG_DIR", mode="before")
    @classmethod
    def convert_to_path(cls, v: str | Path) -> Path:
        """Convert string paths to Path objects."""
        return Path(v) if isinstance(v, str) else v

    def __init__(self, **kwargs: Any) -> None:
        """Initialize settings and create necessary directories."""
        super().__init__(**kwargs)
        self._create_directories()

    def _create_directories(self) -> None:
        """Create upload and log directories if they don't exist."""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings: Settings = Settings()
