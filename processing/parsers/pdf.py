"""PDF parser - OCRmyPDF for searchable PDFs, pikepdf/pdfminer for text extraction."""

import logging
import shutil
import tempfile
from pathlib import Path

from .base import DocumentParser, ParseResult

logger = logging.getLogger(__name__)


class PDFParser(DocumentParser):
    """Parse PDF documents with OCRmyPDF and text extraction."""

    supported_mime_types = ["application/pdf"]

    def parse(self, source_path: Path, mime_type: str,
              language: str = "eng") -> ParseResult:
        # 1. Try to run OCRmyPDF for searchable PDF
        archive_path = self._run_ocrmypdf(source_path, language)

        # 2. Extract text from the best available PDF
        pdf_to_read = archive_path or source_path
        content = self._extract_text(pdf_to_read)

        # 3. Get page count
        page_count = self._get_page_count(source_path)

        return ParseResult(
            content=content,
            archive_path=archive_path,
            page_count=page_count,
        )

    def _run_ocrmypdf(self, source_path: Path, language: str) -> Path | None:
        """Run OCRmyPDF to create a searchable PDF."""
        try:
            import ocrmypdf
            from processing.config import get_ocr_config
        except ImportError:
            logger.warning("ocrmypdf not available, skipping OCR")
            return None

        ocr_config = get_ocr_config()
        archive_path = Path(tempfile.mkdtemp()) / f"{source_path.stem}.pdf"

        try:
            kwargs = {
                "input_file": source_path,
                "output_file": archive_path,
                "language": language,
                "output_type": ocr_config.output_type,
                "deskew": ocr_config.deskew,
                "rotate_pages": ocr_config.rotate,
                "image_dpi": ocr_config.image_dpi,
                "jobs": 2,
            }

            if ocr_config.mode == "skip":
                kwargs["skip_text"] = True
            elif ocr_config.mode == "redo":
                kwargs["redo_ocr"] = True
            elif ocr_config.mode == "force":
                kwargs["force_ocr"] = True

            if ocr_config.clean != "none":
                kwargs["clean"] = True
            if ocr_config.clean == "finalize":
                kwargs["clean_final"] = True

            ocrmypdf.ocr(**kwargs)
            return archive_path

        except ocrmypdf.exceptions.PriorOcrFoundError:
            shutil.copy(source_path, archive_path)
            return archive_path
        except Exception:
            logger.warning("OCRmyPDF failed for %s", source_path, exc_info=True)
            return None

    def _extract_text(self, pdf_path: Path) -> str:
        """Extract text from PDF using pdfminer.six (more reliable than pikepdf)."""
        try:
            from pdfminer.high_level import extract_text
            return extract_text(str(pdf_path)).strip()
        except Exception:
            pass

        # Fallback to pikepdf
        try:
            import pikepdf
            text_parts = []
            with pikepdf.open(pdf_path) as pdf:
                for page in pdf.pages:
                    try:
                        text_parts.append(page.extract_text() or "")
                    except Exception:
                        text_parts.append("")
            return "\n".join(text_parts).strip()
        except Exception:
            logger.warning("Could not extract text from %s", pdf_path)
            return ""

    def _get_page_count(self, pdf_path: Path) -> int:
        """Get page count using pikepdf."""
        try:
            import pikepdf
            with pikepdf.open(pdf_path) as pdf:
                return len(pdf.pages)
        except Exception:
            return 0
