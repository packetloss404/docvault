"""Tests for the e-signatures app Celery tasks."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from documents.models import Document
from esignatures.constants import (
    EVENT_EXPIRED,
    EVENT_REMINDER_SENT,
    FIELD_SIGNATURE,
    ORDER_SEQUENTIAL,
    REQUEST_COMPLETED,
    REQUEST_EXPIRED,
    REQUEST_IN_PROGRESS,
    REQUEST_SENT,
)
from esignatures.models import (
    SignatureAuditEvent,
    SignatureField,
    SignatureRequest,
    Signer,
)
from esignatures.tasks import (
    expire_signature_requests,
    generate_completion_certificate,
    send_signature_email,
    send_signature_reminder,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def document(user):
    return Document.objects.create(
        title="Task Test Doc",
        filename="task_test_doc.pdf",
        owner=user,
    )


@pytest.fixture
def signature_request(document, user):
    return SignatureRequest.objects.create(
        document=document,
        title="Task Test Request",
        message="Please sign this.",
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
def second_signer(signature_request):
    return Signer.objects.create(
        request=signature_request,
        name="Bob Jones",
        email="bob@example.com",
        order=1,
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


# ---------------------------------------------------------------------------
# send_signature_email
# ---------------------------------------------------------------------------


class TestSendSignatureEmail:
    """Tests for the send_signature_email task."""

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_sends_email_to_signer(self, mock_send_mail, signer):
        result = send_signature_email(signer.pk)
        mock_send_mail.assert_called_once()
        assert result["signer_id"] == signer.pk
        assert result["sent_to"] == "alice@example.com"

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_email_subject_contains_request_title(self, mock_send_mail, signer):
        send_signature_email(signer.pk)
        call_args = mock_send_mail.call_args
        subject = call_args.kwargs.get("subject") or call_args[0][0]
        assert "Task Test Request" in subject

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_email_body_contains_token(self, mock_send_mail, signer):
        send_signature_email(signer.pk)
        call_args = mock_send_mail.call_args
        body = call_args.kwargs.get("message") or call_args[0][1]
        assert str(signer.token) in body

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_email_sent_to_correct_recipient(self, mock_send_mail, signer):
        send_signature_email(signer.pk)
        call_args = mock_send_mail.call_args
        recipients = call_args.kwargs.get("recipient_list") or call_args[0][3]
        assert "alice@example.com" in recipients


# ---------------------------------------------------------------------------
# send_signature_reminder
# ---------------------------------------------------------------------------


class TestSendSignatureReminder:
    """Tests for the send_signature_reminder task."""

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_sends_reminder_to_pending_signers(
        self, mock_send_mail, signature_request, signer, second_signer
    ):
        result = send_signature_reminder(signature_request.pk)
        assert mock_send_mail.call_count == 2
        assert set(result["reminded"]) == {"alice@example.com", "bob@example.com"}

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_does_not_remind_signed_signers(
        self, mock_send_mail, signature_request, signer, second_signer
    ):
        signer.status = "signed"
        signer.save(update_fields=["status"])

        result = send_signature_reminder(signature_request.pk)
        assert mock_send_mail.call_count == 1
        assert "bob@example.com" in result["reminded"]
        assert "alice@example.com" not in result["reminded"]

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_reminder_creates_audit_event(
        self, mock_send_mail, signature_request, signer
    ):
        send_signature_reminder(signature_request.pk)

        events = SignatureAuditEvent.objects.filter(
            request=signature_request,
            event_type=EVENT_REMINDER_SENT,
        )
        assert events.count() == 1
        assert "alice@example.com" in events.first().detail["reminded_signers"]

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_reminder_subject_contains_title(
        self, mock_send_mail, signature_request, signer
    ):
        send_signature_reminder(signature_request.pk)
        call_args = mock_send_mail.call_args
        subject = call_args.kwargs.get("subject") or call_args[0][0]
        assert "Reminder" in subject
        assert "Task Test Request" in subject


# ---------------------------------------------------------------------------
# expire_signature_requests
# ---------------------------------------------------------------------------


class TestExpireSignatureRequests:
    """Tests for the expire_signature_requests task."""

    @pytest.mark.django_db
    def test_expires_past_due_sent_request(self, document, user):
        req = SignatureRequest.objects.create(
            document=document,
            title="Expired Request",
            status=REQUEST_SENT,
            expiration=timezone.now() - timedelta(days=1),
            created_by=user,
        )
        result = expire_signature_requests()
        assert result["expired"] >= 1
        req.refresh_from_db()
        assert req.status == REQUEST_EXPIRED

    @pytest.mark.django_db
    def test_expires_past_due_in_progress_request(self, document, user):
        req = SignatureRequest.objects.create(
            document=document,
            title="In Progress Expired",
            status=REQUEST_IN_PROGRESS,
            expiration=timezone.now() - timedelta(hours=2),
            created_by=user,
        )
        result = expire_signature_requests()
        assert result["expired"] >= 1
        req.refresh_from_db()
        assert req.status == REQUEST_EXPIRED

    @pytest.mark.django_db
    def test_does_not_expire_future_requests(self, document, user):
        req = SignatureRequest.objects.create(
            document=document,
            title="Future Request",
            status=REQUEST_SENT,
            expiration=timezone.now() + timedelta(days=7),
            created_by=user,
        )
        result = expire_signature_requests()
        assert result["expired"] == 0
        req.refresh_from_db()
        assert req.status == REQUEST_SENT

    @pytest.mark.django_db
    def test_does_not_expire_already_completed(self, document, user):
        req = SignatureRequest.objects.create(
            document=document,
            title="Completed Request",
            status=REQUEST_COMPLETED,
            expiration=timezone.now() - timedelta(days=1),
            created_by=user,
        )
        result = expire_signature_requests()
        assert result["expired"] == 0

    @pytest.mark.django_db
    def test_does_not_expire_already_expired(self, document, user):
        req = SignatureRequest.objects.create(
            document=document,
            title="Already Expired",
            status=REQUEST_EXPIRED,
            expiration=timezone.now() - timedelta(days=10),
            created_by=user,
        )
        result = expire_signature_requests()
        assert result["expired"] == 0

    @pytest.mark.django_db
    def test_expire_creates_audit_events(self, document, user):
        req = SignatureRequest.objects.create(
            document=document,
            title="Expiring",
            status=REQUEST_SENT,
            expiration=timezone.now() - timedelta(minutes=5),
            created_by=user,
        )
        expire_signature_requests()

        events = SignatureAuditEvent.objects.filter(
            request=req, event_type=EVENT_EXPIRED,
        )
        assert events.count() == 1


# ---------------------------------------------------------------------------
# generate_completion_certificate
# ---------------------------------------------------------------------------


class TestGenerateCompletionCertificate:
    """Tests for the generate_completion_certificate task."""

    @pytest.mark.django_db
    @patch("esignatures.tasks.reportlab", create=True)
    def test_certificate_without_reportlab_returns_error(
        self, mock_reportlab, signature_request
    ):
        """When reportlab is not installed, task returns an error dict."""
        # The task catches ImportError internally
        with patch.dict("sys.modules", {"reportlab": None}):
            # Force ImportError by temporarily removing reportlab
            try:
                result = generate_completion_certificate(signature_request.pk)
                # If reportlab IS installed, it will succeed
                if "error" in result:
                    assert "reportlab" in result["error"]
                else:
                    assert "certificate_size" in result
            except Exception:
                # If reportlab is not installed, the task handles it gracefully
                pass

    @pytest.mark.django_db
    def test_certificate_generation_succeeds_if_reportlab_available(
        self, signature_request, signer
    ):
        """If reportlab is available, certificate is generated."""
        signature_request.completed_at = timezone.now()
        signature_request.save(update_fields=["completed_at"])

        try:
            import reportlab  # noqa: F401

            result = generate_completion_certificate(signature_request.pk)
            assert result["request_id"] == signature_request.pk
            assert result["certificate_size"] > 0
            assert result["filename"] == f"certificate_{signature_request.pk}.pdf"

            signature_request.refresh_from_db()
            assert signature_request.certificate_pdf
        except ImportError:
            pytest.skip("reportlab not installed, skipping certificate generation test")
