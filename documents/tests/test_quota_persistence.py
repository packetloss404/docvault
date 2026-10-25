from io import BytesIO

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from documents.models import Document, DocumentFile
from notifications.models import Quota
from notifications.quotas import QuotaExceededError
from processing.context import ProcessingContext
from processing.plugins.store import StorePlugin
from storage.utils import get_storage_backend


@pytest.mark.django_db
def test_metadata_creation_obeys_document_quota():
    owner = User.objects.create_user('quota-metadata-owner')
    Quota.objects.create(user=owner, max_documents=1)
    client = APIClient()
    client.force_authenticate(owner)
    assert client.post('/api/v1/documents/', {'title': 'One'}, format='json').status_code == 201
    rejected = client.post('/api/v1/documents/', {'title': 'Two'}, format='json')
    assert rejected.status_code == 429
    assert 'Document limit reached' in str(rejected.data)
    assert Document.objects.filter(owner=owner).count() == 1


@pytest.mark.django_db
def test_worker_rechecks_quota_before_saving_any_bytes(settings, tmp_path):
    settings.STORAGE_BACKEND = 'local'
    settings.STORAGE_DIR = tmp_path / 'storage'
    owner = User.objects.create_user('quota-source-owner')
    Quota.objects.create(user=owner, max_storage_bytes=3)
    source = tmp_path / 'source.txt'
    source.write_bytes(b'too large')
    context = ProcessingContext(
        source_path=source, original_filename='source.txt', mime_type='text/plain', checksum='checksum',
        user_id=owner.pk,
    )
    with pytest.raises(QuotaExceededError, match='Storage limit reached'):
        StorePlugin().process(context)
    assert not Document.objects.filter(owner=owner).exists()
    assert get_storage_backend().list_files() == []


@pytest.mark.django_db
def test_new_versions_enforce_storage_quota_without_counting_another_document(settings, tmp_path):
    settings.STORAGE_BACKEND = 'local'
    settings.STORAGE_DIR = tmp_path
    backend = get_storage_backend()
    key = backend.save('originals/first.txt', BytesIO(b'old!'))
    owner = User.objects.create_user('quota-version-owner')
    document = Document.objects.create(title='Existing', filename=key, owner=owner)
    DocumentFile.objects.create(document=document, file=key, filename='first.txt', mime_type='text/plain', size=4)
    Quota.objects.create(user=owner, max_documents=1, max_storage_bytes=8)
    client = APIClient()
    client.force_authenticate(owner)
    first = client.post(f'/api/v1/documents/{document.pk}/files/', {
        'document': SimpleUploadedFile('second.txt', b'new!', content_type='text/plain'),
    }, format='multipart')
    assert first.status_code == 201
    rejected = client.post(f'/api/v1/documents/{document.pk}/files/', {
        'document': SimpleUploadedFile('third.txt', b'x', content_type='text/plain'),
    }, format='multipart')
    assert rejected.status_code == 429
    assert 'Storage limit reached' in str(rejected.data)
    assert Document.objects.filter(owner=owner).count() == 1
    assert list(document.files.order_by('pk').values_list('size', flat=True)) == [4, 4]
