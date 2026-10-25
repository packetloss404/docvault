"""Tests for storing ingested files under configured path templates."""

import hashlib
from io import BytesIO

import pytest

from documents.models import Document
from organization.models import StoragePath
from processing.context import ProcessingContext
from processing.plugins.store import StorePlugin
from storage.backends.local import LocalStorageBackend


@pytest.fixture
def storage_backend(tmp_path, monkeypatch):
    backend = LocalStorageBackend(tmp_path / "storage")
    monkeypatch.setattr("storage.utils.get_storage_backend", lambda: backend)
    return backend


@pytest.fixture
def context(tmp_path):
    source_path = tmp_path / "source.txt"
    source_path.write_bytes(b"original document content")
    return ProcessingContext(
        source_path=source_path,
        original_filename="source.txt",
        title="Invoice",
        mime_type="text/plain",
        checksum=hashlib.sha256(source_path.read_bytes()).hexdigest(),
    )


@pytest.mark.django_db
def test_template_path_contains_original_file(context, storage_backend):
    path = StoragePath.objects.create(name="Invoices", path="invoices/{{ title }}")
    context.override_storage_path = path.pk

    result = StorePlugin().process(context)

    document = Document.objects.get(pk=context.document_id)
    assert result.success
    assert document.filename.startswith("invoices/Invoice")
    with storage_backend.open(document.filename) as stored_file:
        assert stored_file.read() == context.source_path.read_bytes()
    assert storage_backend.list_files("originals") == []


@pytest.mark.django_db
def test_template_collision_preserves_existing_file(context, storage_backend):
    path = StoragePath.objects.create(name="Invoices", path="invoices/{{ title }}")
    context.override_storage_path = path.pk
    storage_backend.save("invoices/Invoice.txt", BytesIO(b"existing document"))

    StorePlugin().process(context)

    document = Document.objects.get(pk=context.document_id)
    assert document.filename != "invoices/Invoice.txt"
    with storage_backend.open("invoices/Invoice.txt") as existing_file:
        assert existing_file.read() == b"existing document"
    with storage_backend.open(document.filename) as stored_file:
        assert stored_file.read() == context.source_path.read_bytes()


@pytest.mark.django_db
def test_multiple_documents_without_archives_keep_nullable_unique_keys(context, storage_backend):
    StorePlugin().process(context)
    StorePlugin().process(context)

    assert Document.objects.count() == 2
    assert not Document.objects.exclude(archive_filename__isnull=True).exists()
    for document in Document.objects.all():
        version = document.version_history.get()
        assert version.version_number == 1
        assert version.file.size == len(context.source_path.read_bytes())
        assert version.file.file.name == document.filename


@pytest.mark.django_db
def test_failed_template_storage_keeps_original(context, storage_backend, monkeypatch):
    path = StoragePath.objects.create(name="Invoices", path="invoices/{{ title }}")
    context.override_storage_path = path.pk
    save = storage_backend.save

    def failing_save(name, content):
        if name.startswith("invoices/"):
            raise OSError("storage unavailable")
        return save(name, content)

    monkeypatch.setattr(storage_backend, "save", failing_save)

    StorePlugin().process(context)

    document = Document.objects.get(pk=context.document_id)
    assert document.filename.startswith("originals/")
    with storage_backend.open(document.filename) as stored_file:
        assert stored_file.read() == context.source_path.read_bytes()
