"""Request-owned copies of the exact source and review artifacts sent to signers."""

import hashlib
import logging
import uuid
from pathlib import Path
from tempfile import SpooledTemporaryFile

from django.utils import timezone

logger = logging.getLogger(__name__)


class SnapshotError(ValueError):
    pass


def freeze_document(signature_request, document):
    import pymupdf

    from documents.downloads import open_document_file
    from storage.utils import get_storage_backend

    version = document.version_history.select_related("file").filter(is_active=True).first()
    artifact = version.file if version and version.file else None
    mime_type = artifact.mime_type if artifact else document.mime_type
    filename = artifact.filename if artifact else document.original_filename
    expected_hash = artifact.checksum if artifact else document.checksum
    backend = get_storage_backend()
    created_keys = []

    if mime_type != "application/pdf" and (
        not document.archive_filename or (artifact and artifact.file.name != document.filename)
    ):
        raise SnapshotError("A PDF or a generated PDF archive is required before sending a signing request.")

    def copy_stream(source, role, extension, expected_checksum):
        with source, SpooledTemporaryFile(max_size=8 * 1024 * 1024) as buffered:
            digest = hashlib.sha256()
            size = 0
            for chunk in iter(lambda: source.read(65536), b""):
                digest.update(chunk)
                buffered.write(chunk)
                size += len(chunk)
            checksum = digest.hexdigest()
            if expected_checksum and checksum != expected_checksum:
                raise SnapshotError("Document integrity verification failed; the signing request was not sent.")
            buffered.seek(0)
            key = backend.save(
                f"esignatures/snapshots/{signature_request.pk}/{uuid.uuid4().hex}-{role}{extension}", buffered,
            )
            created_keys.append(key)
            return key, checksum, size

    valid = False
    try:
        source = open_document_file(artifact) if artifact else backend.open(document.filename)
        source_key, source_hash, source_size = copy_stream(source, "source", Path(filename).suffix, expected_hash)
        if mime_type == "application/pdf":
            review_key, review_hash = source_key, source_hash
        else:
            review_key, review_hash, _ = copy_stream(
                backend.open(document.archive_filename), "review", ".pdf", document.archive_checksum,
            )
        with backend.open(review_key) as review:
            review_data = review.read()
        with pymupdf.open(stream=review_data, filetype="pdf") as pdf:
            if pdf.needs_pass or not len(pdf):
                raise SnapshotError("The signing PDF must contain readable, unencrypted pages.")
            page_count = len(pdf)
        for field in signature_request.fields.only("page"):
            if max(field.page, 1) > page_count:
                raise SnapshotError(f"Signature field page {field.page} exceeds the frozen PDF's {page_count} pages.")
        valid = True
    except SnapshotError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise SnapshotError("The document file could not be frozen for signing.") from exc
    finally:
        if not valid:
            for key in created_keys:
                try:
                    backend.delete(key)
                except Exception:
                    logger.exception("Failed to clean up an incomplete signing snapshot: %s", key)

    return {
        "format": 1,
        "document_id": document.pk,
        "document_title": document.title,
        "source_key": source_key,
        "source_checksum": source_hash,
        "source_size": source_size,
        "source_mime_type": mime_type,
        "source_filename": filename,
        "source_version_number": version.version_number if artifact else None,
        "review_key": review_key,
        "review_checksum": review_hash,
        "review_page_count": page_count,
        "snapshot_at": timezone.now().isoformat(),
    }


def require_snapshot(signature_request):
    snapshot = signature_request.document_snapshot
    required = {"source_key", "source_checksum", "review_key", "review_checksum"}
    if not isinstance(snapshot, dict) or not all(snapshot.get(key) for key in required):
        raise SnapshotError("This signing request has no frozen document. Cancel it and issue a new request.")
    return snapshot


def read_snapshot(signature_request, role="review"):
    from storage.utils import get_storage_backend

    snapshot = require_snapshot(signature_request)
    try:
        with get_storage_backend().open(snapshot[f"{role}_key"]) as source:
            data = source.read()
    except (OSError, ValueError) as exc:
        raise SnapshotError("The frozen signing document is unavailable.") from exc
    if hashlib.sha256(data).hexdigest() != snapshot[f"{role}_checksum"]:
        raise SnapshotError("The frozen signing document failed integrity verification.")
    return data


def verify_snapshot(signature_request):
    from storage.utils import get_storage_backend

    snapshot = require_snapshot(signature_request)
    backend = get_storage_backend()
    checked = set()
    for role in ("source", "review"):
        key, expected = snapshot[f"{role}_key"], snapshot[f"{role}_checksum"]
        if (key, expected) in checked:
            continue
        digest = hashlib.sha256()
        try:
            with backend.open(key) as source:
                for chunk in iter(lambda: source.read(65536), b""):
                    digest.update(chunk)
        except (OSError, ValueError) as exc:
            raise SnapshotError("The frozen signing document is unavailable.") from exc
        if digest.hexdigest() != expected:
            raise SnapshotError("The frozen signing document failed integrity verification.")
        checked.add((key, expected))
    return snapshot
