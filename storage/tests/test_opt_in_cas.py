from io import BytesIO

import pytest

from documents.models import Document
from storage.backends.content_addressed import ContentAddressedStorageBackend
from storage.backends.local import LocalStorageBackend
from storage.utils import get_storage_backend


@pytest.mark.django_db
def test_cas_is_opt_in_and_preserves_existing_files(settings, tmp_path):
    settings.STORAGE_BACKEND = "local"
    settings.STORAGE_DIR = tmp_path
    settings.STORAGE_ENCRYPTION_ENABLED = False
    settings.STORAGE_CONTENT_ADDRESSED = False
    original = LocalStorageBackend(tmp_path)
    original.save("originals/legacy.txt", BytesIO(b"existing document stays put"))
    Document.objects.create(title="Existing stored document", filename="originals/legacy.txt")
    assert isinstance(get_storage_backend(), LocalStorageBackend)

    settings.STORAGE_CONTENT_ADDRESSED = True
    backend = get_storage_backend()
    assert isinstance(backend, ContentAddressedStorageBackend)
    with backend.open("originals/legacy.txt") as saved:
        assert saved.read() == b"existing document stays put"
    digest = backend.save("originals/new.txt", BytesIO(b"new deduplicated content"))
    assert backend.save("originals/another.txt", BytesIO(b"new deduplicated content")) == digest
    assert backend.get_dedup_stats()["bytes_saved"] == len(b"new deduplicated content")
    assert backend.verify_integrity() == []
    assert original.exists("originals/legacy.txt")
    with original.open("originals/legacy.txt") as saved:
        assert saved.read() == b"existing document stays put"


@pytest.mark.django_db
def test_enabling_cas_keeps_existing_signing_snapshot_keys_readable(settings, tmp_path):
    from esignatures.models import SignatureRequest

    settings.STORAGE_BACKEND = "local"
    settings.STORAGE_DIR = tmp_path
    settings.STORAGE_ENCRYPTION_ENABLED = False
    settings.STORAGE_CONTENT_ADDRESSED = False
    raw = get_storage_backend()
    source = raw.save('esignatures/snapshots/source.txt', BytesIO(b'frozen source'))
    review = raw.save('esignatures/snapshots/review.pdf', BytesIO(b'frozen review'))
    document = Document.objects.create(title='Snapshot owner')
    SignatureRequest.objects.create(document=document, title='Existing request', document_snapshot={
        'source_key': source, 'review_key': review,
    })

    settings.STORAGE_CONTENT_ADDRESSED = True
    cas = get_storage_backend()
    for key, content in [(source, b'frozen source'), (review, b'frozen review')]:
        assert cas.exists(key)
        with cas.open(key) as saved:
            assert saved.read() == content
    assert not cas.exists('esignatures/snapshots/unreferenced.pdf')
