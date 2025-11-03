"""File storage management for uploaded PDFs."""

import logging
from datetime import datetime
from pathlib import Path

from src.pdf_processor.models import UploadedFile

logger = logging.getLogger(__name__)


class FileStorageManager:
    """Manages storage of uploaded PDF files with date-based organization."""

    def __init__(self, base_dir: Path):
        """Initialize the storage manager.

        Args:
            base_dir: Base directory for storing uploaded files
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"FileStorageManager initialized with base_dir={base_dir}")

    def save_file(self, file: UploadedFile) -> Path:
        """Save an uploaded file to disk with date-based organization.

        Files are saved in the structure: base_dir/YYYY/MM/DD/filename.pdf
        If a file with the same name exists, a timestamp suffix is added.

        Args:
            file: The uploaded file to save

        Returns:
            Path to the saved file

        Raises:
            IOError: If file cannot be written to disk
        """
        logger.info(f"Saving file: {file.name} ({file.size_mb}MB)")

        try:
            # Create date-based path
            date_path = self._get_date_path()
            target_dir = self.base_dir / date_path
            target_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique file path (handle collisions)
            file_path = self._generate_unique_path(target_dir, file.name)

            # Write file to disk
            file_path.write_bytes(file.content)

            logger.info(f"File saved successfully: {file_path}")
            return file_path

        except IOError as e:
            logger.error(f"Failed to save file {file.name}: {str(e)}", exc_info=True)
            raise IOError(f"Failed to save file: {str(e)}") from e

        except Exception as e:
            logger.error(f"Unexpected error saving file {file.name}: {str(e)}", exc_info=True)
            raise IOError(f"Unexpected error saving file: {str(e)}") from e

    def _get_date_path(self) -> Path:
        """Get date-based directory path in YYYY/MM/DD format.

        Returns:
            Path representing the current date structure
        """
        now = datetime.now()
        return Path(f"{now.year:04d}/{now.month:02d}/{now.day:02d}")

    def _generate_unique_path(self, directory: Path, filename: str) -> Path:
        """Generate a unique file path, handling filename collisions.

        If a file with the given name already exists, adds a timestamp suffix.

        Args:
            directory: Directory where file will be saved
            filename: Original filename

        Returns:
            Unique file path
        """
        file_path = directory / filename

        # If file doesn't exist, use original name
        if not file_path.exists():
            return file_path

        # Handle collision by adding timestamp suffix
        logger.debug(f"File collision detected for {filename}, adding timestamp suffix")

        # Split filename into stem and extension
        stem = Path(filename).stem
        extension = Path(filename).suffix

        # Add timestamp to create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        unique_filename = f"{stem}_{timestamp}{extension}"
        unique_path = directory / unique_filename

        logger.debug(f"Generated unique filename: {unique_filename}")
        return unique_path
