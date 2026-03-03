"""Processing context - carries state between processing plugins."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class PluginResult:
    """Result returned by a processing plugin."""

    success: bool = True
    should_stop: bool = False
    message: str = ""


@dataclass
class ProcessingContext:
    """Carries state throughout the document processing pipeline."""

    # Input
    source_path: Path | None = None
    original_filename: str = ""
    mime_type: str = ""
    source_type: str = ""  # 'web', 'api', 'email', 'folder', 'scanner'
    user_id: int | None = None

    # Accumulated state
    content: str = ""
    language: str = ""
    date_created: date | None = None
    title: str = ""
    archive_path: Path | None = None
    thumbnail_path: Path | None = None
    page_count: int = 0
    checksum: str = ""
    archive_checksum: str = ""
    file_size: int = 0

    # Classification (populated by later plugins)
    suggested_tags: list = field(default_factory=list)
    suggested_correspondent: int | None = None
    suggested_document_type: int | None = None
    suggested_storage_path: int | None = None

    # Overrides (from API or workflow rules)
    override_title: str | None = None
    override_correspondent: int | None = None
    override_document_type: int | None = None
    override_tags: list | None = None
    override_owner: int | None = None
    override_asn: int | None = None

    # Task tracking
    task_id: str | None = None
    progress: float = 0.0
    status_message: str = ""

    # Result
    document_id: int | None = None
    errors: list = field(default_factory=list)
