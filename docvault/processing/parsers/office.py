"""Office document parser - converts via LibreOffice, then runs PDF parser."""

import logging
import subprocess
import tempfile
from pathlib import Path

from .base import DocumentParser, ParseResult

logger = logging.getLogger(__name__)


class OfficeParser(DocumentParser):
    """Parse Office documents by converting to PDF via LibreOffice."""

    supported_mime_types = [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # pptx
        "application/msword",  # doc
        "application/vnd.ms-excel",  # xls
        "application/vnd.ms-powerpoint",  # ppt
        "application/vnd.oasis.opendocument.text",  # odt
        "application/vnd.oasis.opendocument.spreadsheet",  # ods
        "application/rtf",
    ]

    def parse(self, source_path: Path, mime_type: str,
              language: str = "eng") -> ParseResult:
        # Try LibreOffice conversion to PDF
        pdf_path = self._convert_to_pdf(source_path)
        if pdf_path:
            from .pdf import PDFParser
            return PDFParser().parse(pdf_path, "application/pdf", language)

        # Fallback: direct text extraction
        content = self._extract_text_directly(source_path, mime_type)
        return ParseResult(content=content, page_count=1)

    def _convert_to_pdf(self, source_path: Path) -> Path | None:
        """Convert document to PDF via LibreOffice headless mode."""
        output_dir = Path(tempfile.mkdtemp())

        # Try common LibreOffice binary names
        for binary in ("libreoffice", "soffice", "libreoffice7.6"):
            try:
                subprocess.run(
                    [binary, "--headless", "--convert-to", "pdf",
                     "--outdir", str(output_dir), str(source_path)],
                    check=True,
                    timeout=120,
                    capture_output=True,
                )
                pdf_files = list(output_dir.glob("*.pdf"))
                if pdf_files:
                    return pdf_files[0]
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                    FileNotFoundError):
                continue

        logger.warning("LibreOffice not available for conversion: %s", source_path)
        return None

    def _extract_text_directly(self, source_path: Path, mime_type: str) -> str:
        """Fallback: extract text directly from Office formats."""
        # DOCX
        if mime_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ):
            return self._extract_docx_text(source_path)
        # Plain read for other formats
        try:
            return source_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    @staticmethod
    def _extract_docx_text(path: Path) -> str:
        """Extract text from DOCX using zipfile + XML parsing."""
        import zipfile
        from xml.etree import ElementTree

        try:
            with zipfile.ZipFile(path) as zf:
                with zf.open("word/document.xml") as doc_xml:
                    tree = ElementTree.parse(doc_xml)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = tree.findall(".//w:p", ns)
            text_parts = []
            for para in paragraphs:
                texts = para.findall(".//w:t", ns)
                text_parts.append("".join(t.text or "" for t in texts))
            return "\n".join(text_parts)
        except Exception:
            return ""
