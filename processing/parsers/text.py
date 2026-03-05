"""Text and markup parser - plain text, HTML, CSV, JSON, Markdown."""

import logging
from pathlib import Path

from .base import DocumentParser, ParseResult

logger = logging.getLogger(__name__)


class TextParser(DocumentParser):
    """Parse plain text and markup formats."""

    supported_mime_types = [
        "text/plain",
        "text/html",
        "text/csv",
        "text/markdown",
        "text/xml",
        "application/json",
        "application/xml",
    ]

    def parse(self, source_path: Path, mime_type: str,
              language: str = "eng") -> ParseResult:
        try:
            content = source_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = ""

        if mime_type == "text/html":
            content = self._strip_html(content)

        return ParseResult(content=content, page_count=1)

    @staticmethod
    def _strip_html(html: str) -> str:
        """Strip HTML tags to extract plain text."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            # Remove script and style tags
            for tag in soup(["script", "style"]):
                tag.decompose()
            return soup.get_text(separator="\n", strip=True)
        except ImportError:
            # Fallback: basic regex stripping
            import re
            clean = re.sub(r"<[^>]+>", " ", html)
            return re.sub(r"\s+", " ", clean).strip()
