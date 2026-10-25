from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from documents.models import Document
from esignatures.constants import (
    REQUEST_CANCELLED,
    REQUEST_COMPLETED,
    REQUEST_DRAFT,
    REQUEST_EXPIRED,
    REQUEST_SENT,
    SIGNER_PENDING,
    SIGNER_SIGNED,
    VERIFY_EMAIL,
    VERIFY_NONE,
    VERIFY_SMS,
)
from esignatures.engine import InvalidStateError, complete_signing, record_view
from esignatures.models import SignatureField, SignatureRequest, Signer

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def isolate_public_signing_throttle():
    from django.core.cache import cache

    cache.clear()


def test_configured_signing_rate_is_applied(settings):
    from esignatures.views import SigningRateThrottle

    settings.ESIGNATURE_SIGNING_RATE = "2000/minute"
    throttle = SigningRateThrottle()
    assert throttle.rate == "2000/minute"
    assert throttle.num_requests == 2000


@pytest.fixture
def signing(db, prepare_document, prepare_request):
    document = Document.objects.create(title="Contract", filename="contract.pdf")
    prepare_document(document)
    request = SignatureRequest.objects.create(document=document, title="Sign contract", status=REQUEST_SENT)
    prepare_request(request)
    signer = Signer.objects.create(request=request, name="Alice", email="alice@example.com")
    field = SignatureField.objects.create(
        request=request, signer=signer, page=1, x=0.1, y=0.1, width=0.3, height=0.1, field_type="signature",
    )
    return request, signer, field


def assert_unsigned(signer, field):
    signer.refresh_from_db()
    field.refresh_from_db()
    assert signer.status == SIGNER_PENDING
    assert signer.signed_at is None
    assert field.value == ""
    assert field.signed_at is None
    assert not signer.request.audit_events.exists()


@pytest.mark.parametrize("request_status", [REQUEST_DRAFT, REQUEST_CANCELLED, REQUEST_COMPLETED, REQUEST_EXPIRED])
def test_engine_rejects_inactive_request(signing, request_status):
    request, signer, field = signing
    request.status = request_status
    request.save(update_fields=["status"])

    with pytest.raises(InvalidStateError):
        complete_signing(signer, [{"field_id": field.pk, "value": "Alice"}])

    assert_unsigned(signer, field)


def test_engine_rechecks_request_expiration(signing):
    request, signer, field = signing
    request.expiration = timezone.now() - timedelta(seconds=1)
    request.save(update_fields=["expiration"])

    with pytest.raises(InvalidStateError, match="expired"):
        complete_signing(signer, [{"field_id": field.pk, "value": "Alice"}])

    assert_unsigned(signer, field)


def test_engine_rechecks_persisted_signer_state(signing):
    _, signer, field = signing
    Signer.objects.filter(pk=signer.pk).update(status=SIGNER_SIGNED)

    with pytest.raises(InvalidStateError):
        complete_signing(signer, [{"field_id": field.pk, "value": "Alice"}])

    field.refresh_from_db()
    assert field.value == ""


@pytest.mark.parametrize("request_status", [REQUEST_CANCELLED, REQUEST_COMPLETED])
def test_stale_page_view_cannot_reopen_request(signing, request_status):
    request, signer, _ = signing
    SignatureRequest.objects.filter(pk=request.pk).update(status=request_status)

    record_view(signer)

    request.refresh_from_db()
    assert request.status == request_status


def test_stale_page_view_cannot_reset_signed_signer(signing):
    _, signer, _ = signing
    Signer.objects.filter(pk=signer.pk).update(status=SIGNER_SIGNED)

    record_view(signer)

    signer.refresh_from_db()
    assert signer.status == SIGNER_SIGNED


def test_declining_advances_sequential_invitation(signing):
    from esignatures.engine import decline_signing

    request, signer, _ = signing
    second = Signer.objects.create(request=request, name="Bob", email="bob@example.com", order=1)
    with patch("esignatures.tasks.send_signature_email.delay") as invite:
        decline_signing(signer)

    invite.assert_called_once_with(second.pk)


def test_expiration_worker_does_not_overwrite_completed_request(signing, monkeypatch):
    from esignatures.tasks import expire_signature_requests

    request, _, _ = signing
    request.expiration = timezone.now() - timedelta(seconds=1)
    request.save(update_fields=["expiration"])
    query = SignatureRequest.objects.filter
    query(pk=request.pk).update(status=REQUEST_COMPLETED)

    def stale_candidates(**kwargs):
        if "pk" not in kwargs:
            return [request]
        return query(**kwargs)

    monkeypatch.setattr(SignatureRequest.objects, "filter", stale_candidates)

    assert expire_signature_requests() == {"expired": 0}
    request.refresh_from_db()
    assert request.status == REQUEST_COMPLETED
    assert not request.audit_events.exists()


def test_sequential_signer_cannot_skip_predecessor(signing):
    request, _, _ = signing
    second = Signer.objects.create(request=request, name="Bob", email="bob@example.com", order=1)
    field = SignatureField.objects.create(
        request=request, signer=second, page=1, x=0.1, y=0.2, width=0.3, height=0.1, field_type="signature",
    )

    response = APIClient().post(
        f"/api/v1/sign/{second.token}/complete/",
        {"fields": [{"field_id": field.pk, "value": "Bob"}]}, format="json",
    )

    assert response.status_code == 400
    assert_unsigned(second, field)


def test_sms_signer_must_verify_before_signing(signing):
    _, signer, field = signing
    signer.verification_method = VERIFY_SMS
    signer.verification_code = "123456"
    signer.save(update_fields=["verification_method", "verification_code"])

    response = APIClient().post(
        f"/api/v1/sign/{signer.token}/complete/",
        {"fields": [{"field_id": field.pk, "value": "Alice"}]}, format="json",
    )

    assert response.status_code == 400
    assert "verif" in response.data["error"].lower()
    assert_unsigned(signer, field)


def test_public_preview_does_not_reveal_document_before_signers_turn(signing):
    request, _, _ = signing
    second = Signer.objects.create(request=request, name="Bob", email="bob@example.com", order=1)
    response = APIClient().get(f"/api/v1/sign/{second.token}/preview/?page=1")
    assert response.status_code == 403
    assert "turn" in response.data["error"]


def test_public_preview_requires_sms_verification(signing):
    _, signer, _ = signing
    signer.verification_method = VERIFY_SMS
    signer.save(update_fields=["verification_method"])
    response = APIClient().get(f"/api/v1/sign/{signer.token}/preview/?page=1")
    assert response.status_code == 403
    assert "Verif" in response.data["error"]


def test_expired_public_preview_is_denied(signing):
    request, signer, _ = signing
    request.expiration = timezone.now() - timedelta(seconds=1)
    request.save(update_fields=["expiration"])
    response = APIClient().get(f"/api/v1/sign/{signer.token}/preview/?page=1")
    assert response.status_code == 410


@patch("esignatures.tasks.generate_completion_certificate.delay")
def test_verified_sms_signer_can_sign(mock_certificate, signing):
    _, signer, field = signing
    signer.verification_method = VERIFY_SMS
    signer.verification_code = "123456"
    signer.save(update_fields=["verification_method", "verification_code"])
    client = APIClient()
    verified = client.post(
        "/api/v1/esignatures/verify/", {"token": str(signer.token), "code": "123456"}, format="json",
    )
    assert verified.status_code == 200

    response = client.post(
        f"/api/v1/sign/{signer.token}/complete/",
        {"fields": [{"field_id": field.pk, "value": "Alice"}]}, format="json",
    )

    assert response.status_code == 200
    signer.refresh_from_db()
    assert signer.status == SIGNER_SIGNED


@pytest.mark.parametrize("method", [VERIFY_EMAIL, VERIFY_NONE])
@patch("esignatures.tasks.generate_completion_certificate.delay")
def test_token_signing_without_sms_remains_supported(mock_certificate, signing, method):
    _, signer, field = signing
    signer.verification_method = method
    signer.save(update_fields=["verification_method"])

    response = APIClient().post(
        f"/api/v1/sign/{signer.token}/complete/",
        {"fields": [{"field_id": field.pk, "value": "Alice"}]}, format="json",
    )

    assert response.status_code == 200


@pytest.mark.parametrize("endpoint", ["", "view_page/", "complete/", "decline/", "verify"])
def test_draft_tokens_cannot_access_public_signing(signing, endpoint):
    request, signer, field = signing
    request.status = REQUEST_DRAFT
    request.save(update_fields=["status"])
    client = APIClient()
    url = f"/api/v1/sign/{signer.token}/{endpoint}"
    if endpoint == "":
        response = client.get(url)
    elif endpoint == "verify":
        response = client.post(
            "/api/v1/esignatures/verify/", {"token": str(signer.token), "code": "123456"}, format="json",
        )
    else:
        response = client.post(url, {"fields": [{"field_id": field.pk, "value": "Alice"}], "page": 1}, format="json")

    assert response.status_code == 400
    assert_unsigned(signer, field)
