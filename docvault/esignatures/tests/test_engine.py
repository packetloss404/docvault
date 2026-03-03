"""Tests for the e-signatures engine module."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from documents.models import Document
from esignatures.constants import (
    EVENT_CANCELLED,
    EVENT_DECLINED,
    EVENT_PAGE_VIEWED,
    EVENT_SENT,
    EVENT_SIGNED,
    EVENT_VIEWED,
    FIELD_SIGNATURE,
    FIELD_TEXT,
    ORDER_PARALLEL,
    ORDER_SEQUENTIAL,
    REQUEST_CANCELLED,
    REQUEST_COMPLETED,
    REQUEST_IN_PROGRESS,
    REQUEST_SENT,
    SIGNER_DECLINED,
    SIGNER_PENDING,
    SIGNER_SIGNED,
    SIGNER_VIEWED,
)
from esignatures.engine import (
    InvalidStateError,
    ValidationError,
    cancel_request,
    check_completion,
    complete_signing,
    decline_signing,
    get_next_signer,
    record_page_view,
    record_view,
    send_request,
)
from esignatures.models import (
    SignatureAuditEvent,
    SignatureField,
    SignatureRequest,
    Signer,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def document(user):
    return Document.objects.create(
        title="Engine Test Doc",
        filename="engine_test_doc.pdf",
        owner=user,
    )


@pytest.fixture
def seq_request(document, user):
    return SignatureRequest.objects.create(
        document=document,
        title="Sequential Request",
        signing_order=ORDER_SEQUENTIAL,
        created_by=user,
    )


@pytest.fixture
def par_request(document, user):
    return SignatureRequest.objects.create(
        document=document,
        title="Parallel Request",
        signing_order=ORDER_PARALLEL,
        created_by=user,
    )


def _add_signer(request, name, email, order=0):
    return Signer.objects.create(
        request=request, name=name, email=email, order=order,
    )


def _add_field(request, signer, field_type=FIELD_SIGNATURE, required=True, page=1):
    return SignatureField.objects.create(
        request=request,
        signer=signer,
        page=page,
        x=0.1, y=0.5, width=0.3, height=0.05,
        field_type=field_type,
        required=required,
    )


# ---------------------------------------------------------------------------
# send_request
# ---------------------------------------------------------------------------


class TestSendRequest:
    """Tests for the send_request engine function."""

    @pytest.mark.django_db
    @patch("esignatures.tasks.send_signature_email.delay")
    def test_send_sequential_notifies_first_signer_only(self, mock_delay, seq_request):
        s1 = _add_signer(seq_request, "Alice", "alice@example.com", order=0)
        s2 = _add_signer(seq_request, "Bob", "bob@example.com", order=1)
        _add_field(seq_request, s1)
        _add_field(seq_request, s2)

        send_request(seq_request)

        mock_delay.assert_called_once_with(s1.pk)
        seq_request.refresh_from_db()
        assert seq_request.status == REQUEST_SENT

    @pytest.mark.django_db
    @patch("esignatures.tasks.send_signature_email.delay")
    def test_send_parallel_notifies_all_signers(self, mock_delay, par_request):
        s1 = _add_signer(par_request, "Alice", "alice@example.com", order=0)
        s2 = _add_signer(par_request, "Bob", "bob@example.com", order=1)
        _add_field(par_request, s1)
        _add_field(par_request, s2)

        send_request(par_request)

        assert mock_delay.call_count == 2
        called_ids = {call.args[0] for call in mock_delay.call_args_list}
        assert s1.pk in called_ids
        assert s2.pk in called_ids

    @pytest.mark.django_db
    def test_send_request_no_signers_raises(self, seq_request):
        _add_field(
            seq_request,
            _add_signer(seq_request, "A", "a@example.com"),
        )
        # Remove signers after adding field (field requires a signer)
        seq_request.signers.all().delete()
        with pytest.raises(ValidationError, match="no signers"):
            send_request(seq_request)

    @pytest.mark.django_db
    def test_send_request_no_fields_raises(self, seq_request):
        _add_signer(seq_request, "Alice", "alice@example.com")
        with pytest.raises(ValidationError, match="no signature fields"):
            send_request(seq_request)

    @pytest.mark.django_db
    @patch("esignatures.tasks.send_signature_email.delay")
    def test_send_request_not_draft_raises(self, mock_delay, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        _add_field(seq_request, s)

        send_request(seq_request)  # Now status is SENT

        with pytest.raises(InvalidStateError, match="draft"):
            send_request(seq_request)

    @pytest.mark.django_db
    @patch("esignatures.tasks.send_signature_email.delay")
    def test_send_creates_audit_event(self, mock_delay, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        _add_field(seq_request, s)

        send_request(seq_request)

        events = SignatureAuditEvent.objects.filter(
            request=seq_request, event_type=EVENT_SENT,
        )
        assert events.count() == 1
        assert events.first().detail["signing_order"] == ORDER_SEQUENTIAL


# ---------------------------------------------------------------------------
# record_view
# ---------------------------------------------------------------------------


class TestRecordView:
    """Tests for the record_view engine function."""

    @pytest.mark.django_db
    def test_record_view_transitions_pending_to_viewed(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        assert s.status == SIGNER_PENDING

        record_view(s, ip_address="10.0.0.1")

        s.refresh_from_db()
        assert s.status == SIGNER_VIEWED

    @pytest.mark.django_db
    def test_record_view_transitions_request_to_in_progress(self, seq_request):
        seq_request.status = REQUEST_SENT
        seq_request.save(update_fields=["status"])

        s = _add_signer(seq_request, "Alice", "alice@example.com")
        record_view(s)

        seq_request.refresh_from_db()
        assert seq_request.status == REQUEST_IN_PROGRESS

    @pytest.mark.django_db
    def test_record_view_already_viewed_no_status_change(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        s.status = SIGNER_VIEWED
        s.save(update_fields=["status"])

        record_view(s)

        s.refresh_from_db()
        assert s.status == SIGNER_VIEWED

    @pytest.mark.django_db
    def test_record_view_creates_audit_event(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        record_view(s, ip_address="1.2.3.4")

        event = SignatureAuditEvent.objects.filter(
            request=seq_request, event_type=EVENT_VIEWED,
        ).first()
        assert event is not None
        assert event.signer == s
        assert event.ip_address == "1.2.3.4"


# ---------------------------------------------------------------------------
# record_page_view
# ---------------------------------------------------------------------------


class TestRecordPageView:
    """Tests for the record_page_view engine function."""

    @pytest.mark.django_db
    def test_page_added_to_viewed_pages(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        record_page_view(s, 1)

        s.refresh_from_db()
        assert 1 in s.viewed_pages

    @pytest.mark.django_db
    def test_duplicate_page_not_added(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        record_page_view(s, 1)
        record_page_view(s, 1)

        s.refresh_from_db()
        assert s.viewed_pages.count(1) == 1

    @pytest.mark.django_db
    def test_multiple_pages_tracked(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        record_page_view(s, 1)
        record_page_view(s, 2)
        record_page_view(s, 3)

        s.refresh_from_db()
        assert set(s.viewed_pages) == {1, 2, 3}

    @pytest.mark.django_db
    def test_page_view_creates_audit_event(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        record_page_view(s, 5, ip_address="1.2.3.4")

        event = SignatureAuditEvent.objects.filter(
            event_type=EVENT_PAGE_VIEWED,
        ).first()
        assert event is not None
        assert event.detail["page"] == 5


# ---------------------------------------------------------------------------
# complete_signing
# ---------------------------------------------------------------------------


class TestCompleteSigning:
    """Tests for the complete_signing engine function."""

    @pytest.mark.django_db
    @patch("esignatures.tasks.generate_completion_certificate.delay")
    def test_complete_signing_basic(self, mock_cert, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        f = _add_field(seq_request, s)
        s.status = SIGNER_VIEWED
        s.save(update_fields=["status"])

        complete_signing(
            s,
            field_values=[{"field_id": f.pk, "value": "Alice Smith"}],
            ip_address="10.0.0.1",
            user_agent="TestBrowser/1.0",
        )

        s.refresh_from_db()
        assert s.status == SIGNER_SIGNED
        assert s.signed_at is not None
        assert s.ip_address == "10.0.0.1"
        assert s.user_agent == "TestBrowser/1.0"

        f.refresh_from_db()
        assert f.value == "Alice Smith"
        assert f.signed_at is not None

    @pytest.mark.django_db
    @patch("esignatures.tasks.generate_completion_certificate.delay")
    def test_complete_signing_completes_request_when_all_done(self, mock_cert, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        f = _add_field(seq_request, s)
        seq_request.status = REQUEST_SENT
        seq_request.save(update_fields=["status"])
        s.status = SIGNER_VIEWED
        s.save(update_fields=["status"])

        complete_signing(s, field_values=[{"field_id": f.pk, "value": "sig"}])

        seq_request.refresh_from_db()
        assert seq_request.status == REQUEST_COMPLETED
        assert seq_request.completed_at is not None
        mock_cert.assert_called_once_with(seq_request.pk)

    @pytest.mark.django_db
    @patch("esignatures.tasks.send_signature_email.delay")
    def test_complete_signing_sequential_triggers_next_signer(
        self, mock_delay, seq_request
    ):
        s1 = _add_signer(seq_request, "Alice", "alice@example.com", order=0)
        s2 = _add_signer(seq_request, "Bob", "bob@example.com", order=1)
        f1 = _add_field(seq_request, s1)
        _add_field(seq_request, s2)
        seq_request.status = REQUEST_SENT
        seq_request.save(update_fields=["status"])
        s1.status = SIGNER_VIEWED
        s1.save(update_fields=["status"])

        complete_signing(s1, field_values=[{"field_id": f1.pk, "value": "sig"}])

        # Should trigger email to next signer
        mock_delay.assert_called_once_with(s2.pk)

    @pytest.mark.django_db
    def test_complete_signing_missing_required_field_raises(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        f = _add_field(seq_request, s, required=True)
        s.status = SIGNER_VIEWED
        s.save(update_fields=["status"])

        with pytest.raises(ValidationError, match="Required fields"):
            complete_signing(s, field_values=[])

    @pytest.mark.django_db
    def test_complete_signing_already_signed_raises(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        _add_field(seq_request, s)
        s.status = SIGNER_SIGNED
        s.save(update_fields=["status"])

        with pytest.raises(InvalidStateError, match="cannot complete signing"):
            complete_signing(s, field_values=[])

    @pytest.mark.django_db
    @patch("esignatures.tasks.generate_completion_certificate.delay")
    def test_complete_signing_creates_audit_event(self, mock_cert, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        f = _add_field(seq_request, s)
        s.status = SIGNER_VIEWED
        s.save(update_fields=["status"])

        complete_signing(s, field_values=[{"field_id": f.pk, "value": "sig"}])

        event = SignatureAuditEvent.objects.filter(
            request=seq_request, event_type=EVENT_SIGNED,
        ).first()
        assert event is not None
        assert event.signer == s
        assert event.detail["signer_email"] == "alice@example.com"

    @pytest.mark.django_db
    @patch("esignatures.tasks.generate_completion_certificate.delay")
    def test_complete_signing_optional_field_can_be_empty(self, mock_cert, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        f_req = _add_field(seq_request, s, required=True)
        f_opt = _add_field(seq_request, s, required=False, field_type=FIELD_TEXT)
        s.status = SIGNER_VIEWED
        s.save(update_fields=["status"])

        complete_signing(
            s,
            field_values=[
                {"field_id": f_req.pk, "value": "sig"},
                {"field_id": f_opt.pk, "value": ""},
            ],
        )

        s.refresh_from_db()
        assert s.status == SIGNER_SIGNED


# ---------------------------------------------------------------------------
# decline_signing
# ---------------------------------------------------------------------------


class TestDeclineSigning:
    """Tests for the decline_signing engine function."""

    @pytest.mark.django_db
    def test_decline_signing_basic(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")

        decline_signing(s, reason="Not relevant", ip_address="10.0.0.1")

        s.refresh_from_db()
        assert s.status == SIGNER_DECLINED
        assert s.ip_address == "10.0.0.1"

    @pytest.mark.django_db
    def test_decline_already_signed_raises(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        s.status = SIGNER_SIGNED
        s.save(update_fields=["status"])

        with pytest.raises(InvalidStateError, match="cannot decline"):
            decline_signing(s)

    @pytest.mark.django_db
    def test_decline_already_declined_raises(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        s.status = SIGNER_DECLINED
        s.save(update_fields=["status"])

        with pytest.raises(InvalidStateError, match="cannot decline"):
            decline_signing(s)

    @pytest.mark.django_db
    def test_decline_creates_audit_event(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        decline_signing(s, reason="Wrong doc")

        event = SignatureAuditEvent.objects.filter(
            request=seq_request, event_type=EVENT_DECLINED,
        ).first()
        assert event is not None
        assert event.detail["reason"] == "Wrong doc"

    @pytest.mark.django_db
    @patch("esignatures.tasks.generate_completion_certificate.delay")
    def test_decline_completes_request_when_all_done(self, mock_cert, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        _add_field(seq_request, s)
        seq_request.status = REQUEST_SENT
        seq_request.save(update_fields=["status"])

        decline_signing(s)

        seq_request.refresh_from_db()
        assert seq_request.status == REQUEST_COMPLETED


# ---------------------------------------------------------------------------
# cancel_request
# ---------------------------------------------------------------------------


class TestCancelRequest:
    """Tests for the cancel_request engine function."""

    @pytest.mark.django_db
    def test_cancel_request_basic(self, seq_request, user):
        seq_request.status = REQUEST_SENT
        seq_request.save(update_fields=["status"])

        cancel_request(seq_request, user=user)

        seq_request.refresh_from_db()
        assert seq_request.status == REQUEST_CANCELLED

    @pytest.mark.django_db
    def test_cancel_already_completed_raises(self, seq_request, user):
        seq_request.status = REQUEST_COMPLETED
        seq_request.save(update_fields=["status"])

        with pytest.raises(InvalidStateError, match="Cannot cancel"):
            cancel_request(seq_request, user=user)

    @pytest.mark.django_db
    def test_cancel_already_cancelled_raises(self, seq_request, user):
        seq_request.status = REQUEST_CANCELLED
        seq_request.save(update_fields=["status"])

        with pytest.raises(InvalidStateError, match="Cannot cancel"):
            cancel_request(seq_request, user=user)

    @pytest.mark.django_db
    def test_cancel_creates_audit_event(self, seq_request, user):
        cancel_request(seq_request, user=user)

        event = SignatureAuditEvent.objects.filter(
            request=seq_request, event_type=EVENT_CANCELLED,
        ).first()
        assert event is not None
        assert event.detail["cancelled_by"] == "testuser"


# ---------------------------------------------------------------------------
# get_next_signer / check_completion
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    """Tests for get_next_signer and check_completion."""

    @pytest.mark.django_db
    def test_get_next_signer_returns_lowest_order(self, seq_request):
        s1 = _add_signer(seq_request, "Alice", "alice@example.com", order=0)
        s2 = _add_signer(seq_request, "Bob", "bob@example.com", order=1)

        assert get_next_signer(seq_request) == s1

    @pytest.mark.django_db
    def test_get_next_signer_skips_signed(self, seq_request):
        s1 = _add_signer(seq_request, "Alice", "alice@example.com", order=0)
        s2 = _add_signer(seq_request, "Bob", "bob@example.com", order=1)
        s1.status = SIGNER_SIGNED
        s1.save(update_fields=["status"])

        assert get_next_signer(seq_request) == s2

    @pytest.mark.django_db
    def test_get_next_signer_returns_none_when_all_done(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        s.status = SIGNER_SIGNED
        s.save(update_fields=["status"])

        assert get_next_signer(seq_request) is None

    @pytest.mark.django_db
    def test_check_completion_all_signed(self, seq_request):
        s = _add_signer(seq_request, "Alice", "alice@example.com")
        s.status = SIGNER_SIGNED
        s.save(update_fields=["status"])

        assert check_completion(seq_request) is True

    @pytest.mark.django_db
    def test_check_completion_pending_signers(self, seq_request):
        _add_signer(seq_request, "Alice", "alice@example.com")
        assert check_completion(seq_request) is False

    @pytest.mark.django_db
    def test_check_completion_mixed_signed_and_declined(self, seq_request):
        s1 = _add_signer(seq_request, "Alice", "alice@example.com", order=0)
        s2 = _add_signer(seq_request, "Bob", "bob@example.com", order=1)
        s1.status = SIGNER_SIGNED
        s1.save(update_fields=["status"])
        s2.status = SIGNER_DECLINED
        s2.save(update_fields=["status"])

        assert check_completion(seq_request) is True
