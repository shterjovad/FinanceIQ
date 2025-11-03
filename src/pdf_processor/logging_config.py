"""Logging configuration for the PDF processing application."""

import logging
import sys

from src.config.settings import settings


def setup_logging() -> None:
    """Configure logging with console and file handlers.

    - Console handler: INFO level for user-facing messages
    - File handler: DEBUG level for detailed debugging
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Capture all levels

    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_formatter = logging.Formatter(
        fmt="%(levelname)s - %(message)s"
    )

    # Console handler (INFO level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (DEBUG level)
    log_file = settings.LOG_DIR / "financeiq.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Log initial setup message
    logger.info("Logging configured successfully")
    logger.debug(f"Log file: {log_file}")
