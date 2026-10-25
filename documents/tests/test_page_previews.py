from io import BytesIO

import pytest
from django.contrib.auth.models import User
from PIL import Image
from reportlab.pdfgen import canvas
from rest_framework.test import APIClient

from documents.models import Document


@pytest.fixture
def pdf_document(db, settings, tmp_path):
    settings.STORAGE_BACKEND = 'local'
    settings.STORAGE_DIR = tmp_path
    path = tmp_path / 'originals' / 'preview.pdf'
    path.parent.mkdir()
    pdf = canvas.Canvas(str(path))
    pdf.drawString(40, 700, 'First page')
    pdf.showPage()
    pdf.drawString(40, 700, 'Second page')
    pdf.showPage()
    pdf.save()
    user = User.objects.create_user('preview-owner')
    document = Document.objects.create(
        title='Page previews', owner=user, filename='originals/preview.pdf', mime_type='application/pdf', page_count=2,
    )
    client = APIClient()
    client.force_authenticate(user)
    return document, client, path


def test_pdf_pages_render_distinct_bounded_private_images(pdf_document):
    document, client, _ = pdf_document
    first = client.get(f'/api/v1/documents/{document.pk}/preview/?page=1')
    second = client.get(f'/api/v1/documents/{document.pk}/preview/?page=2')

    assert first.status_code == second.status_code == 200
    assert first['Content-Type'] == 'image/png'
    assert first['Cache-Control'] == 'private, no-store'
    assert first.content.startswith(b'\x89PNG')
    assert first.content != second.content
    image = Image.open(BytesIO(first.content))
    assert image.width <= 1600 and image.height <= 2000


@pytest.mark.parametrize('page,status', [('0', 400), ('abc', 400), ('3', 404)])
def test_invalid_or_missing_pages_are_rejected(pdf_document, page, status):
    document, client, _ = pdf_document
    assert client.get(f'/api/v1/documents/{document.pk}/preview/?page={page}').status_code == status


def test_page_preview_obeys_document_permissions(pdf_document):
    document, client, _ = pdf_document
    client.force_authenticate(User.objects.create_user('other-preview-user'))
    assert client.get(f'/api/v1/documents/{document.pk}/preview/?page=1').status_code == 404
    client.force_authenticate(None)
    assert client.get(f'/api/v1/documents/{document.pk}/preview/?page=1').status_code == 401


def test_page_preview_uses_archive_for_image_documents(pdf_document):
    document, client, _ = pdf_document
    document.archive_filename = document.filename
    document.filename = 'originals/image.png'
    document.mime_type = 'image/png'
    document.save(update_fields=['archive_filename', 'filename', 'mime_type'])
    assert client.get(f'/api/v1/documents/{document.pk}/preview/?page=1').status_code == 200


def test_invalid_pdf_data_has_a_controlled_missing_preview_response(pdf_document):
    document, client, path = pdf_document
    path.write_bytes(b'not a PDF')
    assert client.get(f'/api/v1/documents/{document.pk}/preview/?page=1').status_code == 404
