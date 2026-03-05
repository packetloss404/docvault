"""Tests for the e-signatures app models."""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from documents.models import Document
from esignatures.constants import (
    EVENT_CREATED,
    EVENT_SENT,
    FIELD_CHECKBOX,
    FIELD_DATE,
    FIELD_INITIALS,
    FIELD_SIGNATURE,
    FIELD_TEXT,
    ORDER_PARALLEL,
    ORDER_SEQUENTIAL,
    REQUEST_DRAFT,
    SIGNER_PENDING,
    VERIFY_EMAIL,
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
        title="Test Document",
        filename="esig_test_doc.pdf",
        owner=user,
    )


@pytest.fixture
def signature_request(document, user):
    return SignatureRequest.objects.create(
        document=document,
        title="Please Sign This",
        message="Please sign at your earliest convenience.",
        signing_order=ORDER_SEQUENTIAL,
        created_by=user,
    )


@pytest.fixture
def signer(signature_request):
    return Signer.objects.create(
        request=signature_request,
        name="Alice Smith",
        email="alice@example.com",
        role="Reviewer",
        order=0,
    )


@pytest.fixture
def second_signer(signature_request):
    return Signer.objects.create(
        request=signature_request,
        name="Bob Jones",
        email="bob@example.com",
        role="Approver",
        order=1,
    )


@pytest.fixture
def signature_field(signature_request, signer):
    return SignatureField.objects.create(
        request=signature_request,
        signer=signer,
        page=1,
        x=0.1,
        y=0.5,
        width=0.3,
        height=0.05,
        field_type=FIELD_SIGNATURE,
        required=True,
        order=0,
    )


# ---------------------------------------------------------------------------
# SignatureRequest
# ---------------------------------------------------------------------------


class TestSignatureRequest:
    """Tests for the SignatureRequest model."""

    @pytest.mark.django_db
    def test_create_request(self, signature_request):
        assert signature_request.pk is not None
        assert signature_request.title == "Please Sign This"
        assert signature_request.message == "Please sign at your earliest convenience."
        assert signature_request.signing_order == ORDER_SEQUENTIAL

    @pytest.mark.django_db
    def test_default_status_is_draft(self, signature_request):
        assert signature_request.status == REQUEST_DRAFT

    @pytest.mark.django_db
    def test_str_representation(self, signature_request):
        assert str(signature_request) == "Please Sign This (draft)"

    @pytest.mark.django_db
    def test_default_values(self, document, user):
        req = SignatureRequest.objects.create(
            document=document,
            title="Minimal Request",
            created_by=user,
        )
        assert req.status == REQUEST_DRAFT
        assert req.signing_order == ORDER_SEQUENTIAL
        assert req.message == ""
        assert req.expiration is None
        assert req.completed_at is None
        assert not req.certificate_pdf

    @pytest.mark.django_db
    def test_signing_order_parallel(self, document, user):
        req = SignatureRequest.objects.create(
            document=document,
            title="Parallel Request",
            signing_order=ORDER_PARALLEL,
            created_by=user,
        )
        assert req.signing_order == ORDER_PARALLEL

    @pytest.mark.django_db
    def test_ordering_by_created_at_descending(self, document, user):
        req1 = SignatureRequest.objects.create(
            document=document, title="First", created_by=user,
        )
        req2 = SignatureRequest.objects.create(
            document=document, title="Second", created_by=user,
        )
        pks = list(SignatureRequest.objects.values_list("pk", flat=True))
        assert pks.index(req2.pk) < pks.index(req1.pk)

    @pytest.mark.django_db
    def test_cascade_delete_document_removes_requests(self, document, signature_request):
        assert SignatureRequest.objects.count() == 1
        document.hard_delete()
        assert SignatureRequest.objects.count() == 0

    @pytest.mark.django_db
    def test_auditable_timestamps(self, signature_request):
        assert signature_request.created_at is not None
        assert signature_request.updated_at is not None

    @pytest.mark.django_db
    def test_created_by_set_null_on_user_delete(self, document, user):
        req = SignatureRequest.objects.create(
            document=document, title="Test", created_by=user,
        )
        user.delete()
        req.refresh_from_db()
        assert req.created_by is None


# ---------------------------------------------------------------------------
# Signer
# ---------------------------------------------------------------------------


class TestSigner:
    """Tests for the Signer model."""

    @pytest.mark.django_db
    def test_create_signer(self, signer):
        assert signer.pk is not None
        assert signer.name == "Alice Smith"
        assert signer.email == "alice@example.com"
        assert signer.role == "Reviewer"
        assert signer.order == 0

    @pytest.mark.django_db
    def test_default_status_is_pending(self, signer):
        assert signer.status == SIGNER_PENDING

    @pytest.mark.django_db
    def test_token_auto_generated_uuid(self, signer):
        assert signer.token is not None
        assert isinstance(signer.token, uuid.UUID)

    @pytest.mark.django_db
    def test_tokens_are_unique(self, signer, second_signer):
        assert signer.token != second_signer.token

    @pytest.mark.django_db
    def test_unique_constraint_request_email(self, signature_request):
        Signer.objects.create(
            request=signature_request,
            name="Charlie",
            email="charlie@example.com",
            order=0,
        )
        with pytest.raises(IntegrityError):
            Signer.objects.create(
                request=signature_request,
                name="Charlie Duplicate",
                email="charlie@example.com",
                order=1,
            )

    @pytest.mark.django_db
    def test_same_email_different_requests(self, document, user):
        req1 = SignatureRequest.objects.create(
            document=document, title="Req 1", created_by=user,
        )
        req2 = SignatureRequest.objects.create(
            document=document, title="Req 2", created_by=user,
        )
        s1 = Signer.objects.create(request=req1, name="A", email="same@example.com")
        s2 = Signer.objects.create(request=req2, name="B", email="same@example.com")
        assert s1.pk != s2.pk

    @pytest.mark.django_db
    def test_str_representation(self, signer):
        assert str(signer) == "Alice Smith <alice@example.com> (pending)"

    @pytest.mark.django_db
    def test_default_verification_method(self, signer):
        assert signer.verification_method == VERIFY_EMAIL

    @pytest.mark.django_db
    def test_viewed_pages_default_empty_list(self, signer):
        assert signer.viewed_pages == []

    @pytest.mark.django_db
    def test_signed_at_null_by_default(self, signer):
        assert signer.signed_at is None

    @pytest.mark.django_db
    def test_ordering_by_order_then_pk(self, signature_request, signer, second_signer):
        signers = list(signature_request.signers.all())
        assert signers[0].order <= signers[1].order

    @pytest.mark.django_db
    def test_cascade_delete_request_removes_signers(
        self, signature_request, signer, second_signer
    ):
        assert Signer.objects.count() == 2
        signature_request.delete()
        assert Signer.objects.count() == 0


# ---------------------------------------------------------------------------
# SignatureField
# ---------------------------------------------------------------------------


class TestSignatureField:
    """Tests for the SignatureField model."""

    @pytest.mark.django_db
    def test_create_field(self, signature_field):
        assert signature_field.pk is not None
        assert signature_field.page == 1
        assert signature_field.field_type == FIELD_SIGNATURE
        assert signature_field.required is True

    @pytest.mark.django_db
    def test_coordinate_values(self, signature_field):
        assert signature_field.x == 0.1
        assert signature_field.y == 0.5
        assert signature_field.width == 0.3
        assert signature_field.height == 0.05

    @pytest.mark.django_db
    def test_str_representation(self, signature_field):
        expected = "Field signature on page 1 for Alice Smith"
        assert str(signature_field) == expected

    @pytest.mark.django_db
    def test_field_type_choices(self, signature_request, signer):
        for field_type in [FIELD_SIGNATURE, FIELD_INITIALS, FIELD_DATE, FIELD_TEXT, FIELD_CHECKBOX]:
            f = SignatureField.objects.create(
                request=signature_request,
                signer=signer,
                page=1,
                x=0.1, y=0.1, width=0.2, height=0.05,
                field_type=field_type,
            )
            assert f.field_type == field_type

    @pytest.mark.django_db
    def test_value_default_empty(self, signature_field):
        assert signature_field.value == ""

    @pytest.mark.django_db
    def test_signed_at_null_by_default(self, signature_field):
        assert signature_field.signed_at is None

    @pytest.mark.django_db
    def test_cascade_delete_request_removes_fields(
        self, signature_request, signature_field
    ):
        assert SignatureField.objects.count() == 1
        signature_request.delete()
        assert SignatureField.objects.count() == 0

    @pytest.mark.django_db
    def test_cascade_delete_signer_removes_fields(self, signer, signature_field):
        assert SignatureField.objects.count() == 1
        signer.delete()
        assert SignatureField.objects.count() == 0


# ---------------------------------------------------------------------------
# SignatureAuditEvent
# ---------------------------------------------------------------------------


class TestSignatureAuditEvent:
    """Tests for the SignatureAuditEvent model."""

    @pytest.mark.django_db
    def test_create_event(self, signature_request):
        event = SignatureAuditEvent.objects.create(
            request=signature_request,
            event_type=EVENT_CREATED,
            detail={"created_by": "testuser"},
        )
        assert event.pk is not None
        assert event.event_type == EVENT_CREATED
        assert event.detail == {"created_by": "testuser"}

    @pytest.mark.django_db
    def test_timestamp_auto_set(self, signature_request):
        event = SignatureAuditEvent.objects.create(
            request=signature_request,
            event_type=EVENT_CREATED,
        )
        assert event.timestamp is not None

    @pytest.mark.django_db
    def test_signer_optional(self, signature_request):
        event = SignatureAuditEvent.objects.create(
            request=signature_request,
            event_type=EVENT_SENT,
        )
        assert event.signer is None

    @pytest.mark.django_db
    def test_signer_set_null_on_delete(self, signature_request, signer):
        event = SignatureAuditEvent.objects.create(
            request=signature_request,
            signer=signer,
            event_type=EVENT_SENT,
        )
        signer.delete()
        event.refresh_from_db()
        assert event.signer is None

    @pytest.mark.django_db
    def test_ordering_by_timestamp_descending(self, signature_request):
        e1 = SignatureAuditEvent.objects.create(
            request=signature_request, event_type=EVENT_CREATED,
        )
        e2 = SignatureAuditEvent.objects.create(
            request=signature_request, event_type=EVENT_SENT,
        )
        pks = list(SignatureAuditEvent.objects.values_list("pk", flat=True))
        assert pks.index(e2.pk) < pks.index(e1.pk)

    @pytest.mark.django_db
    def test_str_representation(self, signature_request):
        event = SignatureAuditEvent.objects.create(
            request=signature_request,
            event_type=EVENT_CREATED,
        )
        assert "created" in str(event)
        assert "at" in str(event)

    @pytest.mark.django_db
    def test_cascade_delete_request_removes_events(self, signature_request):
        SignatureAuditEvent.objects.create(
            request=signature_request, event_type=EVENT_CREATED,
        )
        SignatureAuditEvent.objects.create(
            request=signature_request, event_type=EVENT_SENT,
        )
        assert SignatureAuditEvent.objects.count() == 2
        signature_request.delete()
        assert SignatureAuditEvent.objects.count() == 0

    @pytest.mark.django_db
    def test_ip_address_optional(self, signature_request):
        event = SignatureAuditEvent.objects.create(
            request=signature_request,
            event_type=EVENT_CREATED,
            ip_address="192.168.1.1",
        )
        assert event.ip_address == "192.168.1.1"

    @pytest.mark.django_db
    def test_detail_default_empty_dict(self, signature_request):
        event = SignatureAuditEvent.objects.create(
            request=signature_request,
            event_type=EVENT_CREATED,
        )
        assert event.detail == {}
