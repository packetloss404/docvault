"""Tests for the portal app models."""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError

from documents.models import Document
from portal.constants import (
    REQUEST_PENDING,
    SUBMISSION_PENDING,
)
from portal.models import DocumentRequest, PortalConfig, PortalSubmission

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def portal(user):
    return PortalConfig.objects.create(
        name="Test Portal",
        slug="test-portal",
        welcome_text="Welcome to test",
        is_active=True,
        require_email=True,
        require_name=True,
        max_file_size_mb=50,
        created_by=user,
    )


@pytest.fixture
def portal_b(user):
    return PortalConfig.objects.create(
        name="Portal B",
        slug="portal-b",
        is_active=True,
        created_by=user,
    )


@pytest.fixture
def doc_request(portal):
    return DocumentRequest.objects.create(
        portal=portal,
        title="Submit Tax Docs",
        description="Please submit your tax documents",
        assignee_email="contributor@example.com",
        assignee_name="Jane Doe",
    )


@pytest.fixture
def submission(portal, doc_request):
    fake_file = SimpleUploadedFile("test.pdf", b"fake pdf content", content_type="application/pdf")
    return PortalSubmission.objects.create(
        portal=portal,
        request=doc_request,
        file=fake_file,
        original_filename="test.pdf",
        submitter_email="contributor@example.com",
        submitter_name="Jane Doe",
    )


# ---------------------------------------------------------------------------
# PortalConfig
# ---------------------------------------------------------------------------


class TestPortalConfig:
    """Tests for the PortalConfig model."""

    @pytest.mark.django_db
    def test_create_portal(self, portal):
        assert portal.pk is not None
        assert portal.name == "Test Portal"
        assert portal.slug == "test-portal"
        assert portal.is_active is True
        assert portal.require_email is True
        assert portal.require_name is True
        assert portal.max_file_size_mb == 50
        assert portal.primary_color == "#0d6efd"

    @pytest.mark.django_db
    def test_str_returns_name(self, portal):
        assert str(portal) == "Test Portal"

    @pytest.mark.django_db
    def test_slug_uniqueness(self, portal):
        with pytest.raises(IntegrityError):
            PortalConfig.objects.create(
                name="Duplicate Portal",
                slug="test-portal",
            )

    @pytest.mark.django_db
    def test_default_values(self, user):
        p = PortalConfig.objects.create(
            name="Minimal Portal",
            slug="minimal",
            created_by=user,
        )
        assert p.welcome_text == ""
        assert p.primary_color == "#0d6efd"
        assert p.is_active is True
        assert p.require_email is True
        assert p.require_name is True
        assert p.max_file_size_mb == 50
        assert p.allowed_mime_types == []
        assert p.logo is not None  # ImageField exists, even if empty
        assert p.default_document_type is None

    @pytest.mark.django_db
    def test_ordering_by_name(self, user):
        PortalConfig.objects.create(name="Zulu Portal", slug="zulu", created_by=user)
        PortalConfig.objects.create(name="Alpha Portal", slug="alpha", created_by=user)
        names = list(PortalConfig.objects.values_list("name", flat=True))
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# DocumentRequest
# ---------------------------------------------------------------------------


class TestDocumentRequest:
    """Tests for the DocumentRequest model."""

    @pytest.mark.django_db
    def test_create_request(self, doc_request):
        assert doc_request.pk is not None
        assert doc_request.title == "Submit Tax Docs"
        assert doc_request.assignee_email == "contributor@example.com"
        assert doc_request.status == REQUEST_PENDING

    @pytest.mark.django_db
    def test_str_representation(self, doc_request):
        assert str(doc_request) == "Submit Tax Docs -> contributor@example.com"

    @pytest.mark.django_db
    def test_token_auto_generated_on_save(self, doc_request):
        assert doc_request.token is not None
        assert len(doc_request.token) > 0

    @pytest.mark.django_db
    def test_token_unique(self, portal):
        req1 = DocumentRequest.objects.create(
            portal=portal,
            title="Request 1",
            assignee_email="a@example.com",
        )
        req2 = DocumentRequest.objects.create(
            portal=portal,
            title="Request 2",
            assignee_email="b@example.com",
        )
        assert req1.token != req2.token

    @pytest.mark.django_db
    def test_token_preserved_on_re_save(self, doc_request):
        original_token = doc_request.token
        doc_request.title = "Updated Title"
        doc_request.save()
        doc_request.refresh_from_db()
        assert doc_request.token == original_token

    @pytest.mark.django_db
    def test_default_status_is_pending(self, doc_request):
        assert doc_request.status == REQUEST_PENDING

    @pytest.mark.django_db
    def test_cascade_delete_portal_removes_requests(self, portal, doc_request):
        assert DocumentRequest.objects.count() == 1
        portal.delete()
        assert DocumentRequest.objects.count() == 0

    @pytest.mark.django_db
    def test_default_sent_at_is_none(self, doc_request):
        assert doc_request.sent_at is None

    @pytest.mark.django_db
    def test_default_reminder_sent_at_is_none(self, doc_request):
        assert doc_request.reminder_sent_at is None


# ---------------------------------------------------------------------------
# PortalSubmission
# ---------------------------------------------------------------------------


class TestPortalSubmission:
    """Tests for the PortalSubmission model."""

    @pytest.mark.django_db
    def test_create_submission(self, submission):
        assert submission.pk is not None
        assert submission.original_filename == "test.pdf"
        assert submission.submitter_email == "contributor@example.com"

    @pytest.mark.django_db
    def test_str_representation(self, submission):
        assert str(submission) == "Submission: test.pdf"

    @pytest.mark.django_db
    def test_default_status_is_pending_review(self, submission):
        assert submission.status == SUBMISSION_PENDING

    @pytest.mark.django_db
    def test_submitted_at_auto_set(self, submission):
        assert submission.submitted_at is not None

    @pytest.mark.django_db
    def test_reviewed_fields_null_by_default(self, submission):
        assert submission.reviewed_by is None
        assert submission.reviewed_at is None
        assert submission.review_notes == ""

    @pytest.mark.django_db
    def test_ingested_document_null_by_default(self, submission):
        assert submission.ingested_document is None

    @pytest.mark.django_db
    def test_cascade_delete_portal_removes_submissions(self, portal, submission):
        assert PortalSubmission.objects.count() == 1
        portal.delete()
        assert PortalSubmission.objects.count() == 0

    @pytest.mark.django_db
    def test_request_set_null_on_delete(self, portal, doc_request, submission):
        """Deleting a request should set submission.request to null, not delete."""
        assert submission.request == doc_request
        doc_request.delete()
        submission.refresh_from_db()
        assert submission.request is None

    @pytest.mark.django_db
    def test_submission_without_request(self, portal):
        fake_file = SimpleUploadedFile(
            "orphan.pdf", b"data", content_type="application/pdf"
        )
        sub = PortalSubmission.objects.create(
            portal=portal,
            file=fake_file,
            original_filename="orphan.pdf",
        )
        assert sub.pk is not None
        assert sub.request is None

    @pytest.mark.django_db
    def test_metadata_defaults_to_empty_dict(self, portal):
        fake_file = SimpleUploadedFile("f.txt", b"x", content_type="text/plain")
        sub = PortalSubmission.objects.create(
            portal=portal,
            file=fake_file,
            original_filename="f.txt",
        )
        assert sub.metadata == {}
