"""Shared document file response helpers."""

import hashlib
import logging
from pathlib import Path

from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def open_document_file(artifact):
    """Read an artifact from DocVault storage or its legacy Django upload location."""
    from storage.backends.content_addressed import ContentAddressedStorageBackend
    from storage.utils import get_storage_backend

    backend = get_storage_backend()
    if artifact.blob_id:
        cas = (
            backend if isinstance(backend, ContentAddressedStorageBackend)
            else ContentAddressedStorageBackend(backend)
        )
        return cas.open(artifact.blob_id)
    if artifact.file.name and backend.exists(artifact.file.name):
        return backend.open(artifact.file.name)
    return artifact.file.open("rb")


def active_original(document):
    """Return active-version metadata, falling back to pre-versioning documents."""
    if hasattr(document, "_active_versions"):
        versions = document._active_versions
        version = versions[0] if versions else None
    else:
        version = document.version_history.select_related("file").filter(is_active=True).first()
    return version.file if version and version.file else None


def build_document_file_response(document, version="original"):
    """Return a FileResponse for a document original or archive file."""
    from storage.utils import get_storage_backend

    backend = get_storage_backend()
    version = version or "original"
    active_file = active_original(document)
    artifact = active_file if version == "original" else None

    if version == "archive":
        if active_file and active_file.file.name != document.filename:
            raise Http404("No archive file is available for the active version.")
        if not document.archive_filename:
            raise Http404("No archive file available for this document.")
        storage_name = document.archive_filename
        content_type = "application/pdf"
        download_name = Path(document.original_filename).stem + ".pdf"
        expected_checksum = document.archive_checksum
    elif artifact:
        storage_name = artifact.file.name
        content_type = artifact.mime_type or "application/octet-stream"
        download_name = artifact.filename
        expected_checksum = artifact.checksum
    elif version == "original":
        if not document.filename:
            raise Http404("No file available for this document.")
        storage_name = document.filename
        content_type = document.mime_type or "application/octet-stream"
        download_name = document.original_filename or Path(storage_name).name
        expected_checksum = document.checksum
    else:
        raise Http404("Unsupported file version.")

    if not artifact and not backend.exists(storage_name):
        raise Http404("File not found in storage.")

    def open_file():
        try:
            return open_document_file(artifact) if artifact else backend.open(storage_name)
        except FileNotFoundError as exc:
            raise Http404("File not found in storage.") from exc

    if expected_checksum:
        file_handle = open_file()
        try:
            sha256 = hashlib.sha256()
            for chunk in iter(lambda: file_handle.read(65536), b""):
                sha256.update(chunk)
            actual_checksum = sha256.hexdigest()
        finally:
            file_handle.close()

        if actual_checksum != expected_checksum:
            logger.error(
                "Checksum mismatch for document %s (%s): expected %s, got %s",
                document.pk,
                version,
                expected_checksum,
                actual_checksum,
            )
            return Response(
                {"error": "File integrity check failed."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    file_handle = open_file()
    return FileResponse(
        file_handle,
        content_type=content_type,
        as_attachment=True,
        filename=download_name,
    )
