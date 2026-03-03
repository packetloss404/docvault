"""Thumbnail plugin - generates WebP preview from first page."""

import logging
import uuid
from pathlib import Path

from django.conf import settings

from processing.context import PluginResult, ProcessingContext

from .base import ProcessingPlugin

logger = logging.getLogger(__name__)


class ThumbnailPlugin(ProcessingPlugin):
    """Generate WebP thumbnail from the first page of the document."""

    name = "Thumbnail"
    order = 130

    def can_run(self, context: ProcessingContext) -> bool:
        return context.source_path is not None and context.mime_type != ""

    def process(self, context: ProcessingContext) -> PluginResult:
        self.update_progress(context, 0.90, "Generating thumbnail")

        width = getattr(settings, "THUMBNAIL_WIDTH", 400)
        height = getattr(settings, "THUMBNAIL_HEIGHT", 560)
        source = context.archive_path or context.source_path

        try:
            thumb = self._generate_thumbnail(source, context.mime_type, width, height)
            if thumb:
                context.thumbnail_path = thumb
                # If document already created (StorePlugin ran first),
                # store the thumbnail and update the record
                if context.document_id:
                    self._store_thumbnail(context, thumb)
                return PluginResult(success=True, message="Thumbnail generated")
        except Exception as e:
            logger.warning("Thumbnail generation failed: %s", e)

        return PluginResult(success=True, message="Thumbnail skipped")

    @staticmethod
    def _store_thumbnail(context: ProcessingContext, thumb_path: Path) -> None:
        """Store the thumbnail via the storage backend and update the document."""
        import uuid as _uuid

        from documents.models import Document
        from storage.utils import get_storage_backend

        backend = get_storage_backend()
        thumbnail_name = f"thumbnails/{_uuid.uuid4().hex}.webp"

        with open(thumb_path, "rb") as f:
            backend.save(thumbnail_name, f)

        try:
            doc = Document.objects.get(pk=context.document_id)
            doc.thumbnail_path = thumbnail_name
            doc.save(update_fields=["thumbnail_path"])
        except Document.DoesNotExist:
            logger.warning("Document %s not found for thumbnail update", context.document_id)

    def _generate_thumbnail(
        self, source: Path, mime_type: str, width: int, height: int,
    ) -> Path | None:
        """Generate a WebP thumbnail and return the path."""
        from PIL import Image

        if mime_type == "application/pdf" or str(source).endswith(".pdf"):
            return self._thumbnail_from_pdf(source, width, height)

        if mime_type.startswith("image/"):
            return self._thumbnail_from_image(source, width, height)

        # For office documents, try the archive PDF if available
        return None

    @staticmethod
    def _thumbnail_from_pdf(pdf_path: Path, width: int, height: int) -> Path | None:
        """Generate thumbnail from first page of a PDF."""
        try:
            from pdf2image import convert_from_path
        except ImportError:
            logger.warning("pdf2image not installed, skipping PDF thumbnail")
            return None

        try:
            images = convert_from_path(
                str(pdf_path), first_page=1, last_page=1, dpi=150,
            )
        except Exception as e:
            logger.warning("pdf2image conversion failed: %s", e)
            return None

        if not images:
            return None

        return ThumbnailPlugin._save_thumbnail(images[0], width, height)

    @staticmethod
    def _thumbnail_from_image(image_path: Path, width: int, height: int) -> Path | None:
        """Generate thumbnail from an image file."""
        from PIL import Image

        try:
            img = Image.open(image_path)
        except Exception as e:
            logger.warning("Failed to open image %s: %s", image_path, e)
            return None

        return ThumbnailPlugin._save_thumbnail(img, width, height)

    @staticmethod
    def _save_thumbnail(img, width: int, height: int) -> Path:
        """Resize and save as WebP thumbnail."""
        import tempfile

        from PIL import Image

        # Convert to RGB if needed
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        img.thumbnail((width, height), Image.LANCZOS)

        thumb_dir = Path(tempfile.mkdtemp(prefix="docvault_thumb_"))
        thumb_path = thumb_dir / f"{uuid.uuid4().hex}.webp"
        img.save(str(thumb_path), "WEBP", quality=80)
        return thumb_path
