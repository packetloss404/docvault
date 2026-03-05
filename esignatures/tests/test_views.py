"""Tests for the e-signatures app API views."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from documents.models import Document
from esignatures.constants import (
    EVENT_CREATED,
    FIELD_SIGNATURE,
    ORDER_SEQUENTIAL,
    REQUEST_CANCELLED,
    REQUEST_COMPLETED,
    REQUEST_EXPIRED,
    REQUEST_IN_PROGRESS,
    REQUEST_SENT,
    SIGNER_PENDING,
    SIGNER_SIGNED,
    SIGNER_VIEWED,
)
from esignatures.models import (
    SignatureAuditEvent,
    SignatureField,
    SignatureRequest,
    Signer,
)

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="otheruser", password="testpass456")


@pytest.fixture
def document(user):
    return Document.objects.create(
        title="View Test Doc",
        filename="view_test_doc.pdf",
        owner=user,
        page_count=5,
    )


@pytest.fixture
def signature_request(document, user):
    return SignatureRequest.objects.create(
        document=document,
        title="Test Request",
        message="Please sign",
        signing_order=ORDER_SEQUENTIAL,
        created_by=user,
    )


@pytest.fixture
def signer(signature_request):
    return Signer.objects.create(
        request=signature_request,
        name="Alice Smith",
        email="alice@example.com",
        order=0,
    )


@pytest.fixture
def signature_field(signature_request, signer):
    return SignatureField.objects.create(
        request=signature_request,
        signer=signer,
        page=1,
        x=0.1, y=0.5, width=0.3, height=0.05,
        field_type=FIELD_SIGNATURE,
        required=True,
    )


# ===========================================================================
# Authenticated Views - SignatureRequestViewSet
# ===========================================================================


class TestSignatureRequestViewSet:
    """Tests for the authenticated SignatureRequest CRUD viewset."""

    LIST_URL = "/api/v1/signature-requests/"

    @pytest.mark.django_db
    def test_list_requests(self, client, user, signature_request):
        client.force_authenticate(user=user)
        response = client.get(self.LIST_URL)
        assert response.status_code == 200
        data = response.data.get("results", response.data)
        assert len(data) >= 1

    @pytest.mark.django_db
    def test_list_filters_to_created_by_user(
        self, client, user, other_user, document, signature_request
    ):
        # Create a request owned by other_user
        SignatureRequest.objects.create(
            document=document,
            title="Other User Request",
            created_by=other_user,
        )
        client.force_authenticate(user=user)
        response = client.get(self.LIST_URL)
        data = response.data.get("results", response.data)
        titles = [r["title"] for r in data]
        assert "Test Request" in titles
        assert "Other User Request" not in titles

    @pytest.mark.django_db
    def test_retrieve_request(self, client, user, signature_request):
        client.force_authenticate(user=user)
        response = client.get(f"{self.LIST_URL}{signature_request.pk}/")
        assert response.status_code == 200
        assert response.data["title"] == "Test Request"
        assert "signers" in response.data
        assert "fields_data" in response.data

    @pytest.mark.django_db
    def test_update_request(self, client, user, signature_request):
        client.force_authenticate(user=user)
        response = client.patch(
            f"{self.LIST_URL}{signature_request.pk}/",
            {"title": "Updated Title"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["title"] == "Updated Title"

    @pytest.mark.django_db
    def test_delete_request(self, client, user, signature_request):
        client.force_authenticate(user=user)
        response = client.delete(f"{self.LIST_URL}{signature_request.pk}/")
        assert response.status_code == 204
        assert not SignatureRequest.objects.filter(pk=signature_request.pk).exists()

    @pytest.mark.django_db
    def test_unauthenticated_access_denied(self, client):
        response = client.get(self.LIST_URL)
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    @patch("esignatures.tasks.send_signature_email.delay")
    def test_send_action(self, mock_delay, client, user, signature_request, signer, signature_field):
        client.force_authenticate(user=user)
        response = client.post(
            f"{self.LIST_URL}{signature_request.pk}/send/", format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "sent"
        assert response.data["sent_at"] is not None

    @pytest.mark.django_db
    @patch("esignatures.tasks.send_signature_email.delay")
    def test_send_action_no_signers_returns_400(
        self, mock_delay, client, user, document
    ):
        req = SignatureRequest.objects.create(
            document=document, title="Empty", created_by=user,
        )
        client.force_authenticate(user=user)
        response = client.post(f"{self.LIST_URL}{req.pk}/send/", format="json")
        assert response.status_code == 400
        assert "error" in response.data

    @pytest.mark.django_db
    def test_cancel_action(self, client, user, signature_request):
        signature_request.status = REQUEST_SENT
        signature_request.save(update_fields=["status"])

        client.force_authenticate(user=user)
        response = client.post(
            f"{self.LIST_URL}{signature_request.pk}/cancel/", format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "cancelled"

    @pytest.mark.django_db
    def test_cancel_already_completed_returns_400(
        self, client, user, signature_request
    ):
        signature_request.status = REQUEST_COMPLETED
        signature_request.save(update_fields=["status"])

        client.force_authenticate(user=user)
        response = client.post(
            f"{self.LIST_URL}{signature_request.pk}/cancel/", format="json",
        )
        assert response.status_code == 400

    @pytest.mark.django_db
    @patch("esignatures.tasks.send_signature_reminder.delay")
    def test_remind_action(self, mock_delay, client, user, signature_request):
        client.force_authenticate(user=user)
        response = client.post(
            f"{self.LIST_URL}{signature_request.pk}/remind/", format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "reminder_queued"
        mock_delay.assert_called_once_with(signature_request.pk)


# ===========================================================================
# Authenticated Views - DocumentSignatureRequestView (nested create)
# ===========================================================================


class TestDocumentSignatureRequestCreate:
    """Tests for POST /api/v1/documents/{id}/signature-request/."""

    @pytest.mark.django_db
    def test_create_request_with_signers_and_fields(self, client, user, document):
        client.force_authenticate(user=user)
        data = {
            "title": "New Signature Request",
            "message": "Please sign this document.",
            "signing_order": "sequential",
            "signers": [
                {"name": "Alice", "email": "alice@example.com", "order": 0},
                {"name": "Bob", "email": "bob@example.com", "order": 1},
            ],
            "fields": [
                {
                    "signer_index": 0,
                    "page": 1,
                    "x": 0.1, "y": 0.5, "width": 0.3, "height": 0.05,
                    "field_type": "signature",
                    "required": True,
                    "order": 0,
                },
                {
                    "signer_index": 1,
                    "page": 2,
                    "x": 0.2, "y": 0.6, "width": 0.3, "height": 0.05,
                    "field_type": "initials",
                    "required": True,
                    "order": 0,
                },
            ],
        }
        response = client.post(
            f"/api/v1/documents/{document.pk}/signature-request/",
            data,
            format="json",
        )
        assert response.status_code == 201
        assert response.data["title"] == "New Signature Request"
        assert response.data["signer_count"] == 2
        assert response.data["field_count"] == 2

    @pytest.mark.django_db
    def test_create_request_no_signers_returns_400(self, client, user, document):
        client.force_authenticate(user=user)
        data = {
            "title": "No Signers",
            "signers": [],
            "fields": [],
        }
        response = client.post(
            f"/api/v1/documents/{document.pk}/signature-request/",
            data,
            format="json",
        )
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_create_request_invalid_signer_index_returns_400(
        self, client, user, document
    ):
        client.force_authenticate(user=user)
        data = {
            "title": "Bad Index",
            "signers": [
                {"name": "Alice", "email": "alice@example.com", "order": 0},
            ],
            "fields": [
                {
                    "signer_index": 5,  # out of range
                    "page": 1,
                    "x": 0.1, "y": 0.5, "width": 0.3, "height": 0.05,
                    "field_type": "signature",
                },
            ],
        }
        response = client.post(
            f"/api/v1/documents/{document.pk}/signature-request/",
            data,
            format="json",
        )
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_create_request_creates_audit_event(self, client, user, document):
        client.force_authenticate(user=user)
        data = {
            "title": "Audited Request",
            "signers": [
                {"name": "Alice", "email": "alice@example.com", "order": 0},
            ],
            "fields": [
                {
                    "signer_index": 0,
                    "page": 1,
                    "x": 0.1, "y": 0.5, "width": 0.3, "height": 0.05,
                    "field_type": "signature",
                },
            ],
        }
        response = client.post(
            f"/api/v1/documents/{document.pk}/signature-request/",
            data,
            format="json",
        )
        assert response.status_code == 201
        req_id = response.data["id"]
        events = SignatureAuditEvent.objects.filter(
            request_id=req_id, event_type=EVENT_CREATED,
        )
        assert events.count() == 1

    @pytest.mark.django_db
    def test_create_request_unauthenticated(self, client, document):
        data = {"title": "No Auth", "signers": [], "fields": []}
        response = client.post(
            f"/api/v1/documents/{document.pk}/signature-request/",
            data,
            format="json",
        )
        assert response.status_code in (401, 403)


# ===========================================================================
# Authenticated Views - Audit Trail
# ===========================================================================


class TestSignatureRequestAuditView:
    """Tests for GET /api/v1/signature-requests/{pk}/audit/."""

    @pytest.mark.django_db
    def test_audit_trail(self, client, user, signature_request):
        SignatureAuditEvent.objects.create(
            request=signature_request,
            event_type=EVENT_CREATED,
            detail={"test": True},
        )
        client.force_authenticate(user=user)
        response = client.get(
            f"/api/v1/signature-requests/{signature_request.pk}/audit/",
        )
        assert response.status_code == 200
        assert len(response.data) >= 1
        assert response.data[0]["event_type"] == EVENT_CREATED

    @pytest.mark.django_db
    def test_audit_trail_other_user_404(self, client, other_user, signature_request):
        client.force_authenticate(user=other_user)
        response = client.get(
            f"/api/v1/signature-requests/{signature_request.pk}/audit/",
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_audit_trail_unauthenticated(self, client, signature_request):
        response = client.get(
            f"/api/v1/signature-requests/{signature_request.pk}/audit/",
        )
        assert response.status_code in (401, 403)


# ===========================================================================
# Public Signing Views
# ===========================================================================


class TestPublicSigningView:
    """Tests for GET /api/v1/sign/{token}/ (public)."""

    @pytest.mark.django_db
    def test_get_signing_page(self, client, signature_request, signer, signature_field):
        signature_request.status = REQUEST_SENT
        signature_request.save(update_fields=["status"])

        response = client.get(f"/api/v1/sign/{signer.token}/")
        assert response.status_code == 200
        assert response.data["request_title"] == "Test Request"
        assert response.data["signer_name"] == "Alice Smith"
        assert response.data["signer_email"] == "alice@example.com"
        assert "fields" in response.data

    @pytest.mark.django_db
    def test_signing_view_marks_signer_as_viewed(
        self, client, signature_request, signer, signature_field
    ):
        signature_request.status = REQUEST_SENT
        signature_request.save(update_fields=["status"])

        assert signer.status == SIGNER_PENDING
        client.get(f"/api/v1/sign/{signer.token}/")

        signer.refresh_from_db()
        assert signer.status == SIGNER_VIEWED

    @pytest.mark.django_db
    def test_invalid_token_returns_404(self, client):
        import uuid
        fake_token = uuid.uuid4()
        response = client.get(f"/api/v1/sign/{fake_token}/")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_expired_request_returns_410(self, client, signature_request, signer):
        signature_request.status = REQUEST_SENT
        signature_request.expiration = timezone.now() - timedelta(days=1)
        signature_request.save(update_fields=["status", "expiration"])

        response = client.get(f"/api/v1/sign/{signer.token}/")
        assert response.status_code == 410

    @pytest.mark.django_db
    def test_completed_request_returns_410(self, client, signature_request, signer):
        signature_request.status = REQUEST_COMPLETED
        signature_request.save(update_fields=["status"])

        response = client.get(f"/api/v1/sign/{signer.token}/")
        assert response.status_code == 410

    @pytest.mark.django_db
    def test_cancelled_request_returns_410(self, client, signature_request, signer):
        signature_request.status = REQUEST_CANCELLED
        signature_request.save(update_fields=["status"])

        response = client.get(f"/api/v1/sign/{signer.token}/")
        assert response.status_code == 410


class TestPublicViewPageView:
    """Tests for POST /api/v1/sign/{token}/view_page/."""

    @pytest.mark.django_db
    def test_record_page_view(self, client, signature_request, signer):
        signature_request.status = REQUEST_SENT
        signature_request.save(update_fields=["status"])

        response = client.post(
            f"/api/v1/sign/{signer.token}/view_page/",
            {"page": 2},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "recorded"
        assert response.data["page"] == 2

    @pytest.mark.django_db
    def test_view_page_expired_returns_410(self, client, signature_request, signer):
        signature_request.status = REQUEST_SENT
        signature_request.expiration = timezone.now() - timedelta(hours=1)
        signature_request.save(update_fields=["status", "expiration"])

        response = client.post(
            f"/api/v1/sign/{signer.token}/view_page/",
            {"page": 1},
            format="json",
        )
        assert response.status_code == 410


class TestPublicSigningCompleteView:
    """Tests for POST /api/v1/sign/{token}/complete/."""

    @pytest.mark.django_db
    @patch("esignatures.tasks.generate_completion_certificate.delay")
    def test_complete_signing(self, mock_cert, client, signature_request, signer, signature_field):
        signature_request.status = REQUEST_SENT
        signature_request.save(update_fields=["status"])
        signer.status = SIGNER_VIEWED
        signer.save(update_fields=["status"])

        response = client.post(
            f"/api/v1/sign/{signer.token}/complete/",
            {
                "fields": [
                    {"field_id": signature_field.pk, "value": "Alice Smith"},
                ],
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "signed"
        assert "signed_at" in response.data

    @pytest.mark.django_db
    def test_complete_no_fields_returns_400(
        self, client, signature_request, signer, signature_field
    ):
        signature_request.status = REQUEST_SENT
        signature_request.save(update_fields=["status"])
        signer.status = SIGNER_VIEWED
        signer.save(update_fields=["status"])

        response = client.post(
            f"/api/v1/sign/{signer.token}/complete/",
            {"fields": []},
            format="json",
        )
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_complete_already_signed_returns_400(
        self, client, signature_request, signer, signature_field
    ):
        signature_request.status = REQUEST_IN_PROGRESS
        signature_request.save(update_fields=["status"])
        signer.status = SIGNER_SIGNED
        signer.save(update_fields=["status"])

        response = client.post(
            f"/api/v1/sign/{signer.token}/complete/",
            {
                "fields": [
                    {"field_id": signature_field.pk, "value": "sig"},
                ],
            },
            format="json",
        )
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_complete_expired_request_returns_410(
        self, client, signature_request, signer, signature_field
    ):
        signature_request.status = REQUEST_SENT
        signature_request.expiration = timezone.now() - timedelta(hours=1)
        signature_request.save(update_fields=["status", "expiration"])

        response = client.post(
            f"/api/v1/sign/{signer.token}/complete/",
            {
                "fields": [
                    {"field_id": signature_field.pk, "value": "sig"},
                ],
            },
            format="json",
        )
        assert response.status_code == 410

    @pytest.mark.django_db
    @patch("esignatures.tasks.generate_completion_certificate.delay")
    def test_complete_missing_required_fields_returns_400(
        self, mock_cert, client, signature_request, signer, signature_field
    ):
        signature_request.status = REQUEST_SENT
        signature_request.save(update_fields=["status"])
        signer.status = SIGNER_VIEWED
        signer.save(update_fields=["status"])

        # Don't provide the required field value
        response = client.post(
            f"/api/v1/sign/{signer.token}/complete/",
            {
                "fields": [
                    {"field_id": signature_field.pk, "value": ""},
                ],
            },
            format="json",
        )
        assert response.status_code == 400


class TestPublicSigningDeclineView:
    """Tests for POST /api/v1/sign/{token}/decline/."""

    @pytest.mark.django_db
    def test_decline_signing(self, client, signature_request, signer):
        signature_request.status = REQUEST_SENT
        signature_request.save(update_fields=["status"])

        response = client.post(
            f"/api/v1/sign/{signer.token}/decline/",
            {"reason": "Not the right document"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "declined"

    @pytest.mark.django_db
    def test_decline_without_reason(self, client, signature_request, signer):
        signature_request.status = REQUEST_SENT
        signature_request.save(update_fields=["status"])

        response = client.post(
            f"/api/v1/sign/{signer.token}/decline/",
            {},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "declined"

    @pytest.mark.django_db
    def test_decline_already_signed_returns_400(
        self, client, signature_request, signer
    ):
        signature_request.status = REQUEST_IN_PROGRESS
        signature_request.save(update_fields=["status"])
        signer.status = SIGNER_SIGNED
        signer.save(update_fields=["status"])

        response = client.post(
            f"/api/v1/sign/{signer.token}/decline/",
            {"reason": "Changed my mind"},
            format="json",
        )
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_decline_expired_returns_410(self, client, signature_request, signer):
        signature_request.status = REQUEST_EXPIRED
        signature_request.save(update_fields=["status"])

        response = client.post(
            f"/api/v1/sign/{signer.token}/decline/",
            {},
            format="json",
        )
        assert response.status_code == 410
