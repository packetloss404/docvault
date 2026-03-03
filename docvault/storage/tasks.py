"""Celery tasks for the storage module."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def verify_storage_integrity():
    """
    Verify that all stored file hashes match their ContentBlob records.

    Iterates over every blob, re-computes the SHA-256 hash of the stored
    file, and logs any mismatches or missing files.
    """
    from storage.utils import get_storage_backend

    from .backends.content_addressed import ContentAddressedStorageBackend

    backend = get_storage_backend()

    if isinstance(backend, ContentAddressedStorageBackend):
        cas = backend
    else:
        cas = ContentAddressedStorageBackend(underlying_backend=backend)

    mismatches = cas.verify_integrity()

    if mismatches:
        logger.error(
            "Storage integrity check found %d issues: %s",
            len(mismatches),
            mismatches,
        )
    else:
        logger.info("Storage integrity check passed: all blobs verified.")

    return {
        "status": "completed",
        "issues_found": len(mismatches),
        "details": mismatches,
    }
