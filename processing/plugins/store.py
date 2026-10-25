"""Store plugin - saves original file to storage backend and creates Document record."""

import hashlib
import json
import logging
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User

from processing.context import PluginResult, ProcessingContext

from .base import ProcessingPlugin

logger = logging.getLogger(__name__)


class StorePlugin(ProcessingPlugin):
    """Store the original file, archive, thumbnail, and create the Document record."""

    name = "Store"
    order = 90

    def can_run(self, context: ProcessingContext) -> bool:
        return context.source_path is not None and context.checksum != ""

    def process(self, context: ProcessingContext) -> PluginResult:
        from documents.models import Document
        from storage.utils import get_storage_backend

        backend = get_storage_backend()
        file_uuid = uuid.uuid4().hex

        # Store the original file
        ext = Path(context.original_filename).suffix or ""
        storage_name = f"originals/{file_uuid}{ext}"

        with open(context.source_path, "rb") as f:
            storage_name = backend.save(storage_name, f)

        self.update_progress(context, 0.80, "Original file stored")

        # Store archive (searchable PDF) if non-destructive mode is on
        archive_name = None
        archive_checksum = ""
        non_destructive = getattr(settings, "NON_DESTRUCTIVE_MODE", True)
        if non_destructive and context.archive_path and context.archive_path.is_file():
            archive_name = f"archive/{file_uuid}.pdf"
            with open(context.archive_path, "rb") as f:
                backend.save(archive_name, f)
            archive_checksum = self._calculate_checksum(context.archive_path)
            self.update_progress(context, 0.85, "Archive file stored")

        # Store thumbnail if generated
        thumbnail_name = None
        if context.thumbnail_path and context.thumbnail_path.is_file():
            thumbnail_name = f"thumbnails/{file_uuid}.webp"
            with open(context.thumbnail_path, "rb") as f:
                backend.save(thumbnail_name, f)

        self.update_progress(context, 0.88, "Creating document record")

        # Resolve owner
        owner = None
        if context.override_owner:
            owner = User.objects.filter(pk=context.override_owner).first()
        elif context.user_id:
            owner = User.objects.filter(pk=context.user_id).first()

        # Resolve document type
        document_type = None
        type_id = context.override_document_type or context.suggested_document_type
        if type_id:
            from documents.models import DocumentType
            document_type = DocumentType.objects.filter(pk=type_id).first()

        # Resolve correspondent and storage path from explicit overrides first,
        # then classifier suggestions.
        correspondent_id = context.override_correspondent or context.suggested_correspondent
        storage_path_id = context.override_storage_path or context.suggested_storage_path

        # Create the document
        doc = Document.objects.create(
            title=context.title,
            content=context.content,
            document_type=document_type,
            correspondent_id=correspondent_id,
            storage_path_id=storage_path_id,
            original_filename=context.original_filename,
            mime_type=context.mime_type,
            checksum=context.checksum,
            archive_checksum=archive_checksum,
            page_count=context.page_count,
            filename=storage_name,
            archive_filename=archive_name or "",
            language=context.language or "en",
            archive_serial_number=context.override_asn,
            owner=owner,
            created_by=owner,
        )

        tag_ids = self._normalize_id_list(
            context.override_tags if context.override_tags is not None else context.suggested_tags
        )
        if tag_ids:
            doc.tags.set(tag_ids)

        if context.date_created:
            doc.created = context.date_created
            doc.save(update_fields=["created"])

        if doc.storage_path_id:
            try:
                rendered_path = doc.storage_path.render(doc)
                if rendered_path:
                    # Keep the UUID so matching templates cannot overwrite each other's files.
                    target_name = f"{rendered_path}_{file_uuid}{ext}"
                    with backend.open(storage_name) as original:
                        new_storage_name = backend.save(target_name, original)
                    doc.filename = new_storage_name
                    doc.save(update_fields=["filename"])
                    if new_storage_name != storage_name:
                        backend.delete(storage_name)
                    logger.debug(
                        "StoragePath template applied for document #%s: %s",
                        doc.pk,
                        doc.filename,
                    )
            except Exception:
                logger.exception(
                    "Failed to apply StoragePath template for document #%s.",
                    doc.pk,
                )

        context.document_id = doc.pk
        self.update_progress(context, 0.95, "Document created")
        return PluginResult(success=True, message=f"Document #{doc.pk} created")

    @staticmethod
    def _calculate_checksum(path: Path) -> str:
        """Calculate SHA-256 checksum."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _normalize_id_list(value) -> list[int]:
        """Normalize list-like form values into integer primary keys."""
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                parsed = [part.strip() for part in value.split(",")]
            value = parsed
        if not isinstance(value, (list, tuple, set)):
            value = [value]

        ids = []
        for item in value:
            if item in (None, ""):
                continue
            try:
                ids.append(int(item))
            except (TypeError, ValueError):
                logger.warning("Ignoring invalid tag id in processing context: %r", item)
        return ids
