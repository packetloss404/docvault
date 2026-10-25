import hashlib
from io import BytesIO
from unittest.mock import patch

import pymupdf
import pytest
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError as APIValidationError
from rest_framework.test import APIClient

from documents.models import Document, DocumentFile, DocumentVersion
from documents.previews import render_pdf_page_preview
from esignatures.engine import ValidationError, complete_signing, send_request
from esignatures.models import SignatureField, SignatureRequest, Signer
from esignatures.snapshots import SnapshotError, read_snapshot
from esignatures.tasks import generate_completion_certificate
from storage.utils import get_storage_backend

pytestmark = pytest.mark.django_db


def make_pdf(text, pages=1):
    from reportlab.pdfgen import canvas

    output = BytesIO()
    pdf = canvas.Canvas(output)
    for page in range(pages):
        pdf.drawString(60, 700, f"{text}, page {page + 1}")
        pdf.showPage()
    pdf.save()
    return output.getvalue()


@pytest.fixture
def signing_case(prepare_document):
    owner = get_user_model().objects.create_user("snapshot-owner")
    document = Document.objects.create(title="Immutable contract", filename="originals/base.pdf", owner=owner)
    original = prepare_document(document, "Version one")
    request = SignatureRequest.objects.create(document=document, title="Sign immutable contract", created_by=owner)
    signers, fields = [], []
    for order in range(2):
        signer = Signer.objects.create(
            request=request, name=f"Signer {order}", email=f"signer{order}@example.com", order=order,
        )
        field = SignatureField.objects.create(
            request=request, signer=signer, page=1, x=0.1, y=0.1, width=0.2, height=0.1,
            field_type="signature", required=True,
        )
        signers.append(signer)
        fields.append(field)
    return document, request, signers, fields, original


@patch("esignatures.tasks.send_signature_email.delay")
@patch("esignatures.tasks.generate_completion_certificate.delay")
def test_signers_and_delayed_certificate_keep_frozen_active_v2(mock_certificate, mock_invite, signing_case):
    document, request, signers, fields, original = signing_case
    backend = get_storage_backend()
    first_file = DocumentFile.objects.create(
        document=document, file=document.filename, filename="v1.pdf", mime_type="application/pdf",
        checksum=document.checksum, size=len(original), page_count=1,
    )
    first_version = DocumentVersion.objects.create(document=document, file=first_file, version_number=1)
    second = make_pdf("Version two is the contract being signed")
    second_key = backend.save("versions/v2.pdf", BytesIO(second))
    second_hash = hashlib.sha256(second).hexdigest()
    second_file = DocumentFile.objects.create(
        document=document, file=second_key, filename="v2.pdf", mime_type="application/pdf",
        checksum=second_hash, size=len(second), page_count=1,
    )
    DocumentVersion.objects.create(document=document, file=second_file, version_number=2, is_active=True)

    send_request(request)

    assert request.document_snapshot["source_checksum"] == second_hash
    assert request.document_snapshot["source_version_number"] == 2
    assert read_snapshot(request, "source") == second
    assert document.checksum == hashlib.sha256(original).hexdigest()
    expected_preview = render_pdf_page_preview(second, 1).content
    client = APIClient()
    assert client.get(f"/api/v1/sign/{signers[0].token}/preview/?page=1").content == expected_preview
    complete_signing(signers[0], [{"field_id": fields[0].pk, "value": "First signature"}])

    document.version_history.update(is_active=False)
    first_version.is_active = True
    first_version.save(update_fields=["is_active"])
    document.title = "Changed after the first signer"
    document.save(update_fields=["title"])

    response = client.get(f"/api/v1/sign/{signers[1].token}/preview/?page=1")
    assert response.status_code == 200
    assert response.content == expected_preview
    assert response.content != render_pdf_page_preview(original, 1).content
    complete_signing(signers[1], [{"field_id": fields[1].pk, "value": "Second signature"}])
    generate_completion_certificate(request.pk)
    request.refresh_from_db()
    with request.certificate_pdf.open("rb") as certificate:
        with pymupdf.open(stream=certificate.read(), filetype="pdf") as pdf:
            text = "".join(page.get_text() for page in pdf)
    compact = "".join(text.split())
    assert second_hash in compact
    assert hashlib.sha256(original).hexdigest() not in compact
    assert "Immutable contract" in text
    assert "Changed after" not in text


@patch("esignatures.tasks.send_signature_email.delay")
def test_encrypted_snapshot_uses_configured_backend(mock_invite, signing_case, settings):
    from storage.backends.encrypted import MAGIC

    document, request, _, _, original = signing_case
    settings.STORAGE_ENCRYPTION_ENABLED = True
    settings.STORAGE_ENCRYPTION_KEY = "snapshot-test-key"
    settings.STORAGE_ENCRYPTION_KDF_ITERATIONS = 1000
    backend = get_storage_backend()
    backend.save(document.filename, BytesIO(original))
    send_request(request)
    physical = settings.STORAGE_DIR / request.document_snapshot["source_key"]
    assert physical.read_bytes().startswith(MAGIC)
    assert read_snapshot(request, "source") == original


@patch("esignatures.tasks.send_signature_email.delay")
def test_cas_snapshot_owns_an_independent_reference(mock_invite, signing_case, settings):
    from storage.models import ContentBlob

    document, request, _, _, original = signing_case
    settings.STORAGE_CONTENT_ADDRESSED = True
    backend = get_storage_backend()
    document.filename = backend.save("cas-original.pdf", BytesIO(original))
    document.save(update_fields=["filename"])
    send_request(request)
    key = request.document_snapshot["source_key"]
    assert key == hashlib.sha256(original).hexdigest()
    assert ContentBlob.objects.get(pk=key).reference_count == 2
    backend.delete(document.filename)
    assert read_snapshot(request, "source") == original


@patch("esignatures.tasks.send_signature_email.delay")
def test_image_source_and_ocr_review_have_separate_frozen_hashes(mock_invite, signing_case):
    from PIL import Image

    document, request, _, _, original = signing_case
    image = BytesIO()
    Image.new("RGB", (8, 8), "white").save(image, format="PNG")
    image_bytes = image.getvalue()
    backend = get_storage_backend()
    document.archive_filename = document.filename
    document.archive_checksum = document.checksum
    document.filename = backend.save("originals/scan.png", BytesIO(image_bytes))
    document.original_filename = "scan.png"
    document.mime_type = "image/png"
    document.checksum = hashlib.sha256(image_bytes).hexdigest()
    document.save()
    send_request(request)
    snapshot = request.document_snapshot
    assert snapshot["source_checksum"] == hashlib.sha256(image_bytes).hexdigest()
    assert snapshot["review_checksum"] == hashlib.sha256(original).hexdigest()
    assert read_snapshot(request, "source") == image_bytes
    assert read_snapshot(request) == original


def test_legacy_active_request_without_snapshot_fails_closed(signing_case):
    _, request, signers, fields, _ = signing_case
    request.status = "sent"
    request.save(update_fields=["status"])
    client = APIClient()
    assert client.get(f"/api/v1/sign/{signers[0].token}/preview/?page=1").status_code == 409
    assert client.post(f"/api/v1/sign/{signers[0].token}/complete/", {
        "fields": [{"field_id": fields[0].pk, "value": "Unbound signature"}],
    }, format="json").status_code == 409
    with pytest.raises(SnapshotError, match="no frozen"):
        generate_completion_certificate(request.pk)


@patch("esignatures.tasks.send_signature_email.delay")
def test_modified_snapshot_is_rejected_instead_of_signing_new_bytes(mock_invite, signing_case):
    _, request, signers, fields, _ = signing_case
    send_request(request)
    get_storage_backend().save(request.document_snapshot["source_key"], BytesIO(make_pdf("Tampered")))
    assert APIClient().get(f"/api/v1/sign/{signers[0].token}/preview/?page=1").status_code == 409
    with pytest.raises(ValidationError, match="integrity"):
        complete_signing(signers[0], [{"field_id": fields[0].pk, "value": "Signature"}])
    fields[0].refresh_from_db()
    assert fields[0].value == ""


@patch("esignatures.tasks.send_signature_email.delay")
def test_stale_draft_update_cannot_retarget_a_request_after_send(mock_invite, signing_case):
    from types import SimpleNamespace

    from esignatures.serializers import SignatureRequestSerializer
    from esignatures.views import SignatureRequestViewSet

    document, request, _, _, _ = signing_case
    stale = SignatureRequest.objects.get(pk=request.pk)
    other = Document.objects.create(title="Different contract", owner=document.owner)
    serializer = SignatureRequestSerializer(stale, data={"document": other.pk}, partial=True)
    serializer.is_valid(raise_exception=True)
    send_request(request)
    view = SignatureRequestViewSet()
    view.request = SimpleNamespace(user=document.owner)
    with pytest.raises(APIValidationError, match="cannot be edited"):
        view.perform_update(serializer)
    request.refresh_from_db()
    assert request.document_id == document.pk


@patch("esignatures.tasks.send_signature_email.delay")
def test_send_accepts_fields_on_new_pages_of_the_frozen_active_version(mock_invite, signing_case):
    document, request, _, fields, _ = signing_case
    second = make_pdf("Version two with a new page", pages=2)
    artifact = DocumentFile.objects.create(
        document=document, file=get_storage_backend().save("versions/new-pages.pdf", BytesIO(second)),
        filename="new-pages.pdf", mime_type="application/pdf", checksum=hashlib.sha256(second).hexdigest(),
        size=len(second), page_count=2,
    )
    DocumentVersion.objects.create(document=document, file=artifact, version_number=2, is_active=True)
    fields[0].page = 2
    fields[0].save(update_fields=["page"])
    assert document.page_count == 1
    send_request(request)
    assert request.document_snapshot["review_page_count"] == 2


def test_send_rejects_pages_outside_frozen_review_and_discards_incomplete_copy(signing_case):
    document, request, _, fields, _ = signing_case
    fields[0].page = 3
    fields[0].save(update_fields=["page"])
    with pytest.raises(ValidationError, match="page 3"):
        send_request(request)
    request.refresh_from_db()
    assert request.status == "draft"
    assert request.document_snapshot == {}
    assert get_storage_backend().list_files("esignatures/snapshots") == []
