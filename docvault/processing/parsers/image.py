"""Image parser - converts images to PDF, then runs OCR."""

import logging
import tempfile
from pathlib import Path

from .base import DocumentParser, ParseResult

logger = logging.getLogger(__name__)


class ImageParser(DocumentParser):
    """Parse images by converting to PDF and running OCR."""

    supported_mime_types = [
        "image/jpeg",
        "image/png",
        "image/tiff",
        "image/webp",
        "image/bmp",
        "image/gif",
    ]

    def parse(self, source_path: Path, mime_type: str,
              language: str = "eng") -> ParseResult:
        # Convert image to PDF
        pdf_path = self._image_to_pdf(source_path)
        if not pdf_path:
            return ParseResult(content="", page_count=1)

        # Run PDF parser on the converted file
        from .pdf import PDFParser
        pdf_parser = PDFParser()
        result = pdf_parser.parse(pdf_path, "application/pdf", language)
        result.page_count = 1
        return result

    def _image_to_pdf(self, image_path: Path) -> Path | None:
        """Convert image to PDF using Pillow."""
        try:
            from PIL import Image
            pdf_path = Path(tempfile.mkdtemp()) / f"{image_path.stem}.pdf"
            img = Image.open(image_path)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            img.save(str(pdf_path), "PDF")
            return pdf_path
        except Exception:
            logger.warning("Failed to convert image to PDF: %s", image_path, exc_info=True)
            return None
