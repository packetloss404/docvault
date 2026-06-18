"""Shared document file response helpers."""

import hashlib
import logging
from pathlib import Path

from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def build_document_file_response(document, version="original"):
    """Return a FileResponse for a document original or archive file."""
    from storage.utils import get_storage_backend

    backend = get_storage_backend()
    version = version or "original"

    if version == "archive":
        if not document.archive_filename:
            raise Http404("No archive file available for this document.")
        storage_name = document.archive_filename
        content_type = "application/pdf"
        download_name = Path(document.original_filename).stem + ".pdf"
        expected_checksum = document.archive_checksum
    elif version == "original":
        if not document.filename:
            raise Http404("No file available for this document.")
        storage_name = document.filename
        content_type = document.mime_type or "application/octet-stream"
        download_name = document.original_filename or Path(storage_name).name
        expected_checksum = document.checksum
    else:
        raise Http404("Unsupported file version.")

    if not backend.exists(storage_name):
        raise Http404("File not found in storage.")

    if expected_checksum:
        file_handle = backend.open(storage_name)
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

    file_handle = backend.open(storage_name)
    return FileResponse(
        file_handle,
        content_type=content_type,
        as_attachment=True,
        filename=download_name,
    )
