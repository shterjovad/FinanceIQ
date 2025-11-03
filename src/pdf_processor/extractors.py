"""PDF text extraction logic."""

import logging
from io import BytesIO

from pypdf import PdfReader

from src.pdf_processor.exceptions import NoTextContentError
from src.pdf_processor.models import DocumentMetadata, UploadedFile

logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """Extracts text and metadata from PDF files."""

    def __init__(self, min_text_length: int = 100):
        """Initialize the text extractor.

        Args:
            min_text_length: Minimum number of characters required for valid text extraction
        """
        self.min_text_length = min_text_length
        logger.debug(f"PDFTextExtractor initialized with min_text_length={min_text_length}")

    def extract_text(self, file: UploadedFile) -> str:
        """Extract text from a PDF file.

        Args:
            file: The uploaded PDF file to extract text from

        Returns:
            Extracted text as a string

        Raises:
            NoTextContentError: If PDF contains insufficient text content
        """
        logger.info(f"Extracting text from: {file.name}")

        try:
            # Open PDF with PdfReader
            pdf_reader = PdfReader(BytesIO(file.content))
            total_pages = len(pdf_reader.pages)

            logger.debug(f"PDF has {total_pages} pages")

            # Extract text from all pages
            extracted_text_parts = []

            for page_num, page in enumerate(pdf_reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text_parts.append(page_text)
                        logger.debug(f"Extracted {len(page_text)} chars from page {page_num}")
                    else:
                        logger.debug(f"No text found on page {page_num}")
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
                    # Continue with other pages

            # Concatenate all text with page separators
            full_text = "\n\n".join(extracted_text_parts)

            # Validate minimum text length
            if len(full_text.strip()) < self.min_text_length:
                logger.warning(
                    f"Insufficient text content: {len(full_text)} chars "
                    f"(minimum: {self.min_text_length})"
                )
                raise NoTextContentError(text_length=len(full_text))

            logger.info(
                f"Text extraction successful: {len(full_text)} chars from {total_pages} pages"
            )

            return full_text

        except NoTextContentError:
            # Re-raise NoTextContentError as-is
            raise

        except Exception as e:
            logger.error(f"Unexpected error during text extraction: {str(e)}", exc_info=True)
            raise NoTextContentError(text_length=0) from e

    def extract_metadata(self, file: UploadedFile, extracted_text: str) -> DocumentMetadata:
        """Extract metadata from a PDF file.

        Args:
            file: The uploaded PDF file
            extracted_text: The extracted text content

        Returns:
            DocumentMetadata with page count, file size, and text length
        """
        logger.info(f"Extracting metadata from: {file.name}")

        try:
            # Open PDF to get page count
            pdf_reader = PdfReader(BytesIO(file.content))
            page_count = len(pdf_reader.pages)

            # Create metadata
            metadata = DocumentMetadata(
                page_count=page_count,
                file_size_mb=file.size_mb,
                text_length=len(extracted_text),
            )

            logger.info(
                f"Metadata extracted: {metadata.page_count} pages, "
                f"{metadata.file_size_mb}MB, {metadata.text_length} chars"
            )

            return metadata

        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}", exc_info=True)
            raise
