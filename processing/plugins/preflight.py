"""Preflight plugin - MIME detection, checksum, duplicate checking."""

import hashlib
import logging
from pathlib import Path

from processing.context import PluginResult, ProcessingContext

from .base import ProcessingPlugin

logger = logging.getLogger(__name__)


class PreflightPlugin(ProcessingPlugin):
    """Preflight checks: MIME type detection, checksum calculation, duplicate detection."""

    name = "Preflight"
    order = 10

    def can_run(self, context: ProcessingContext) -> bool:
        return context.source_path is not None

    def process(self, context: ProcessingContext) -> PluginResult:
        source = context.source_path
        if not source or not source.is_file():
            return PluginResult(
                success=False, should_stop=True,
                message=f"Source file not found: {source}",
            )

        # 1. Detect MIME type
        context.mime_type = self._detect_mime_type(source)
        logger.info("Detected MIME type: %s", context.mime_type)

        # 2. Calculate checksum and file size
        context.checksum = self._calculate_checksum(source)
        context.file_size = source.stat().st_size

        # 3. Check for duplicates
        from documents.models import Document
        if Document.objects.filter(checksum=context.checksum).exists():
            return PluginResult(
                success=False, should_stop=True,
                message=f"Duplicate document detected (checksum: {context.checksum[:12]}...)",
            )

        # 4. Set title from filename if not overridden
        if not context.override_title:
            context.title = Path(context.original_filename).stem
        else:
            context.title = context.override_title

        self.update_progress(context, 0.05, "Preflight checks complete")
        return PluginResult(success=True)

    @staticmethod
    def _detect_mime_type(path: Path) -> str:
        """Detect MIME type using python-magic."""
        try:
            import magic
            return magic.from_file(str(path), mime=True)
        except Exception:
            logger.warning("Could not detect MIME type for %s", path)
            return "application/octet-stream"

    @staticmethod
    def _calculate_checksum(path: Path) -> str:
        """Calculate SHA-256 checksum."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
