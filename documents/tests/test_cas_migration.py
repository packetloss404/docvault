import hashlib
from io import BytesIO, StringIO

import pytest
from django.core.management import call_command

from documents.downloads import build_document_file_response, open_document_file
from documents.models import Document, DocumentFile
from storage.backends.local import LocalStorageBackend
from storage.models import ContentBlob


@pytest.mark.django_db
def test_cas_migration_processes_every_batch_and_preserves_original_files(settings, tmp_path):
    settings.STORAGE_BACKEND = 'local'
    settings.STORAGE_DIR = tmp_path
    settings.STORAGE_CONTENT_ADDRESSED = False
    settings.STORAGE_ENCRYPTION_ENABLED = False
    backend = LocalStorageBackend(tmp_path)
    documents = []
    artifacts = []
    for index, content in enumerate([b'one', b'two', b'one', b'four']):
        name = f'originals/migration-{index}.txt'
        backend.save(name, BytesIO(content))
        digest = hashlib.sha256(content).hexdigest()
        document = Document.objects.create(title=f'Legacy {index}', filename=name, checksum=digest)
        artifacts.append(DocumentFile.objects.create(
            document=document, file=name, filename=name, mime_type='text/plain', checksum=digest, size=len(content),
        ))
        documents.append((document, content))

    output = StringIO()
    call_command('migrate_to_cas', batch_size=1, stdout=output)
    assert '4 migrated, 0 skipped, 0 errors' in output.getvalue()
    assert ContentBlob.objects.count() == 3
    assert ContentBlob.objects.get(pk=hashlib.sha256(b'one').hexdigest()).reference_count == 2
    for artifact in artifacts:
        artifact.refresh_from_db()
        assert artifact.blob_id
        assert backend.exists(artifact.blob.storage_path)
        assert backend.exists(artifact.file.name)
        with open_document_file(artifact) as migrated:
            assert hashlib.sha256(migrated.read()).hexdigest() == artifact.checksum
    for document, content in documents:
        response = build_document_file_response(document)
        assert b''.join(response.streaming_content) == content
        response.close()

    second = StringIO()
    call_command('migrate_to_cas', batch_size=1, stdout=second)
    assert 'Nothing to do' in second.getvalue()
