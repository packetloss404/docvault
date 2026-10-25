import hashlib
from io import BytesIO
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from documents.downloads import build_document_file_response, open_document_file
from documents.models import Document, DocumentFile, DocumentVersion
from storage.backends.local import LocalStorageBackend
from storage.utils import get_storage_backend


@pytest.mark.django_db
def test_active_version_download_uses_legacy_django_file_without_moving_original(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path / "media"
    backend = LocalStorageBackend(tmp_path / "backend")
    backend.save("originals/original.txt", BytesIO(b"old original"))
    monkeypatch.setattr("storage.utils.get_storage_backend", lambda: backend)
    document = Document.objects.create(filename="originals/original.txt", title="Legacy")
    content = b"new version"
    artifact = DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("new.txt", content),
        filename="new.txt", mime_type="text/plain", checksum=hashlib.sha256(content).hexdigest(),
    )
    DocumentVersion.objects.create(document=document, file=artifact, version_number=1, is_active=True)

    response = build_document_file_response(document)
    assert b"".join(response.streaming_content) == content
    response.close()
    with backend.open("originals/original.txt") as original:
        assert original.read() == b"old original"
    assert artifact.file.storage.exists(artifact.file.name)


@pytest.mark.django_db
def test_artifact_can_reference_existing_backend_file_without_copying_it(tmp_path, monkeypatch):
    backend = LocalStorageBackend(tmp_path)
    backend.save("originals/evidence.txt", BytesIO(b"original evidence"))
    monkeypatch.setattr("storage.utils.get_storage_backend", lambda: backend)
    document = Document.objects.create(filename="originals/evidence.txt", title="Ingested")
    artifact = DocumentFile.objects.create(
        document=document, file=document.filename, filename="evidence.txt", mime_type="text/plain", checksum="",
    )
    with open_document_file(artifact) as original:
        assert original.read() == b"original evidence"
    assert [Path(name).as_posix() for name in backend.list_files("originals")] == ["originals/evidence.txt"]


@pytest.mark.django_db
@pytest.mark.parametrize('cas_enabled', [False, True])
def test_new_versions_honor_encryption_and_optional_cas(settings, tmp_path, cas_enabled):
    from storage.backends.encrypted import MAGIC
    from storage.models import ContentBlob

    settings.STORAGE_BACKEND = 'local'
    settings.STORAGE_DIR = tmp_path / 'backend'
    settings.MEDIA_ROOT = tmp_path / 'media'
    settings.STORAGE_ENCRYPTION_ENABLED = True
    settings.STORAGE_ENCRYPTION_KEY = 'version-test-only-key'
    settings.STORAGE_CONTENT_ADDRESSED = cas_enabled
    backend = get_storage_backend()
    original_key = backend.save('originals/encrypted.txt', BytesIO(b'original encrypted content'))
    owner = User.objects.create_user('encrypted-version-owner')
    document = Document.objects.create(title='Encrypted version', filename=original_key, owner=owner)
    client = APIClient()
    client.force_authenticate(owner)
    content = b'secret replacement contents'

    response = client.post(f'/api/v1/documents/{document.pk}/files/', {
        'document': SimpleUploadedFile('replacement.txt', content, content_type='text/plain'),
    }, format='multipart')
    assert response.status_code == 201
    artifact = document.version_history.get(is_active=True).file
    with open_document_file(artifact) as uploaded:
        assert uploaded.read() == content
    key = ContentBlob.objects.get(pk=artifact.file.name).storage_path if cas_enabled else artifact.file.name
    with LocalStorageBackend(settings.STORAGE_DIR).open(key) as raw:
        encrypted = raw.read()
    assert encrypted.startswith(MAGIC)
    assert content not in encrypted
    assert not settings.MEDIA_ROOT.exists()


@pytest.mark.django_db
def test_metadata_clients_cannot_forge_storage_references(settings, tmp_path):
    settings.STORAGE_BACKEND = 'local'
    settings.STORAGE_DIR = tmp_path
    LocalStorageBackend(tmp_path).save('originals/private.txt', BytesIO(b'private contents'))
    private = Document.objects.create(title='Private', filename='originals/private.txt')
    client = APIClient()
    client.force_authenticate(User.objects.create_user('metadata-owner'))
    forged = {
        'title': 'Metadata only', 'filename': private.filename, 'archive_filename': private.filename,
        'thumbnail_path': private.filename, 'checksum': 'f' * 64, 'mime_type': 'text/plain',
        'original_filename': 'forged.txt', 'page_count': 1,
    }
    created = client.post('/api/v1/documents/', forged, format='json')
    assert created.status_code == 201
    document = Document.objects.get(pk=created.data['id'])
    assert not document.filename and not document.archive_filename and not document.thumbnail_path
    assert not document.checksum and document.page_count == 0
    assert client.get(f'/api/v1/documents/{document.pk}/download/').status_code == 404
    updated = client.patch(f'/api/v1/documents/{document.pk}/', forged, format='json')
    assert updated.status_code == 200
    assert client.get(f'/api/v1/documents/{document.pk}/download/').status_code == 404
    assert client.get(f'/api/v1/documents/{private.pk}/download/').status_code == 404
