from io import BytesIO

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from documents.models import Document
from security.models import Signature
from storage.backends.local import LocalStorageBackend


@pytest.mark.django_db
def test_version_changes_clear_gpg_verification_cache_without_deleting_signature(settings, tmp_path):
    settings.STORAGE_BACKEND = 'local'
    settings.STORAGE_DIR = tmp_path
    backend = LocalStorageBackend(tmp_path)
    backend.save('originals/signed.txt', BytesIO(b'signed original'))
    user = User.objects.create_user('signed-version-owner')
    document = Document.objects.create(
        title='Signed original', owner=user, filename='originals/signed.txt', mime_type='text/plain',
    )
    signature = Signature.objects.create(
        document=document, signer=user, signature_data='retained signature', key_id='key',
        verified=True, verified_at=timezone.now(),
    )
    client = APIClient()
    client.force_authenticate(user)
    uploaded = client.post(f'/api/v1/documents/{document.pk}/files/', {
        'document': SimpleUploadedFile('replacement.txt', b'new contents', content_type='text/plain'),
    }, format='multipart')
    assert uploaded.status_code == 201
    signature.refresh_from_db()
    assert not signature.verified
    assert signature.verified_at is None
    assert signature.signature_data == 'retained signature'
    signature.verified = True
    signature.verified_at = timezone.now()
    signature.save(update_fields=['verified', 'verified_at'])
    original = document.version_history.get(version_number=1)
    assert client.post(f'/api/v1/documents/{document.pk}/versions/{original.pk}/activate/').status_code == 200
    signature.refresh_from_db()
    assert not signature.verified
    assert signature.verified_at is None
