import hashlib
from io import BytesIO

import pytest


@pytest.fixture
def prepare_document(tmp_path, settings):
    settings.STORAGE_DIR = tmp_path / "storage"
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.STORAGE_BACKEND = "local"
    settings.STORAGE_ENCRYPTION_ENABLED = False
    settings.STORAGE_CONTENT_ADDRESSED = False

    def prepare(document, text="Signing test document"):
        from reportlab.pdfgen import canvas

        from storage.utils import get_storage_backend

        output = BytesIO()
        pdf = canvas.Canvas(output)
        pages = max(document.page_count, 1)
        for page in range(pages):
            pdf.drawString(60, 700, f"{text}, page {page + 1}")
            pdf.showPage()
        pdf.save()
        data = output.getvalue()
        document.filename = get_storage_backend().save(document.filename, BytesIO(data))
        document.original_filename = "contract.pdf"
        document.mime_type = "application/pdf"
        document.checksum = hashlib.sha256(data).hexdigest()
        document.page_count = pages
        document.save(update_fields=["filename", "original_filename", "mime_type", "checksum", "page_count"])
        return data

    return prepare


@pytest.fixture
def prepare_request():
    def prepare(request):
        from esignatures.snapshots import freeze_document

        request.document_snapshot = freeze_document(request, request.document)
        request.save(update_fields=["document_snapshot"])
        return request

    return prepare
