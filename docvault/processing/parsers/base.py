"""Parser base class, result dataclass, and registry."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class ParseResult:
    """Result returned by a document parser."""

    content: str = ""
    archive_path: Path | None = None
    page_count: int = 0
    metadata: dict = field(default_factory=dict)
    date: date | None = None


class DocumentParser(ABC):
    """Abstract base class for format-specific document parsers."""

    supported_mime_types: list[str] = []

    @abstractmethod
    def parse(self, source_path: Path, mime_type: str,
              language: str = "eng") -> ParseResult:
        """Parse document and extract content."""

    def get_thumbnail(self, source_path: Path, page: int = 1) -> Path | None:
        """Generate thumbnail for first page. Override if supported."""
        return None


# --- Parser registry ---

_parser_registry: dict[str, list[type[DocumentParser]]] = {}


def register_parser(parser_class: type[DocumentParser]) -> None:
    """Register a parser class for its supported MIME types."""
    for mime_type in parser_class.supported_mime_types:
        _parser_registry.setdefault(mime_type, []).append(parser_class)


def get_parser_for_mime_type(mime_type: str) -> DocumentParser | None:
    """Return a parser instance for the given MIME type, or None."""
    parsers = _parser_registry.get(mime_type, [])
    if parsers:
        return parsers[0]()
    return None


def get_supported_mime_types() -> list[str]:
    """Return all MIME types that have registered parsers."""
    return list(_parser_registry.keys())


def clear_registry() -> None:
    """Clear the parser registry (for testing)."""
    _parser_registry.clear()
