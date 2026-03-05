"""Tests for the portal app API views."""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from portal.constants import (
    REQUEST_EXPIRED,
    REQUEST_PARTIALLY_FULFILLED,
    REQUEST_PENDING,
    SUBMISSION_APPROVED,
    SUBMISSION_PENDING,
    SUBMISSION_REJECTED,
)
from portal.models import DocumentRequest, PortalConfig, PortalSubmission

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin", password="adminpass123", email="admin@test.com"
    )


@pytest.fixture
def portal(user):
    return PortalConfig.objects.create(
        name="Test Portal",
        slug="test-portal",
        welcome_text="Welcome!",
        is_active=True,
        require_email=True,
        require_name=True,
        max_file_size_mb=10,
        created_by=user,
    )


@pytest.fixture
def inactive_portal(user):
    return PortalConfig.objects.create(
        name="Inactive Portal",
        slug="inactive-portal",
        is_active=False,
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
        deadline=timezone.now() + timezone.timedelta(days=7),
    )


@pytest.fixture
def submission(portal, doc_request):
    fake_file = SimpleUploadedFile("test.pdf", b"pdf content", content_type="application/pdf")
    return PortalSubmission.objects.create(
        portal=portal,
        request=doc_request,
        file=fake_file,
        original_filename="test.pdf",
        submitter_email="contributor@example.com",
        submitter_name="Jane Doe",
        ip_address="127.0.0.1",
    )


def _make_upload_file(name="upload.pdf", content=b"file data", content_type="application/pdf"):
    return SimpleUploadedFile(name, content, content_type=content_type)


# ===========================================================================
# Admin Views - PortalConfig CRUD
# ===========================================================================


class TestPortalConfigViewSet:
    """Tests for PortalConfigViewSet (admin CRUD)."""

    LIST_URL = "/api/v1/portals/"

    @pytest.mark.django_db
    def test_list_portals(self, client, user, portal):
        client.force_authenticate(user=user)
        response = client.get(self.LIST_URL)
        assert response.status_code == 200
        # The response could be paginated or a list
        data = response.data.get("results", response.data)
        slugs = [p["slug"] for p in data]
        assert "test-portal" in slugs

    @pytest.mark.django_db
    def test_create_portal(self, client, user):
        client.force_authenticate(user=user)
        data = {
            "name": "New Portal",
            "slug": "new-portal",
            "welcome_text": "Hello",
            "is_active": True,
            "require_email": False,
            "require_name": False,
            "max_file_size_mb": 25,
        }
        response = client.post(self.LIST_URL, data, format="json")
        assert response.status_code == 201
        assert response.data["slug"] == "new-portal"
        assert response.data["name"] == "New Portal"

    @pytest.mark.django_db
    def test_retrieve_portal(self, client, user, portal):
        client.force_authenticate(user=user)
        response = client.get(f"{self.LIST_URL}{portal.pk}/")
        assert response.status_code == 200
        assert response.data["slug"] == "test-portal"

    @pytest.mark.django_db
    def test_update_portal(self, client, user, portal):
        client.force_authenticate(user=user)
        data = {"name": "Updated Portal"}
        response = client.patch(f"{self.LIST_URL}{portal.pk}/", data, format="json")
        assert response.status_code == 200
        assert response.data["name"] == "Updated Portal"

    @pytest.mark.django_db
    def test_delete_portal(self, client, user, portal):
        client.force_authenticate(user=user)
        response = client.delete(f"{self.LIST_URL}{portal.pk}/")
        assert response.status_code == 204
        assert not PortalConfig.objects.filter(pk=portal.pk).exists()

    @pytest.mark.django_db
    def test_unauthenticated_access_denied(self, client):
        response = client.get(self.LIST_URL)
        assert response.status_code in (401, 403)


# ===========================================================================
# Admin Views - DocumentRequest CRUD
# ===========================================================================


class TestDocumentRequestViewSet:
    """Tests for DocumentRequestViewSet (admin CRUD + actions)."""

    LIST_URL = "/api/v1/document-requests/"

    @pytest.mark.django_db
    def test_list_requests(self, client, user, doc_request):
        client.force_authenticate(user=user)
        response = client.get(self.LIST_URL)
        assert response.status_code == 200
        data = response.data.get("results", response.data)
        assert len(data) >= 1

    @pytest.mark.django_db
    def test_create_request(self, client, user, portal):
        client.force_authenticate(user=user)
        data = {
            "portal": portal.pk,
            "title": "New Request",
            "assignee_email": "new@example.com",
            "assignee_name": "New Person",
        }
        response = client.post(self.LIST_URL, data, format="json")
        assert response.status_code == 201
        assert response.data["title"] == "New Request"
        assert response.data["token"]  # token auto-generated

    @pytest.mark.django_db
    def test_retrieve_request(self, client, user, doc_request):
        client.force_authenticate(user=user)
        response = client.get(f"{self.LIST_URL}{doc_request.pk}/")
        assert response.status_code == 200
        assert response.data["title"] == "Submit Tax Docs"

    @pytest.mark.django_db
    def test_update_request(self, client, user, doc_request):
        client.force_authenticate(user=user)
        data = {"title": "Updated Request"}
        response = client.patch(
            f"{self.LIST_URL}{doc_request.pk}/", data, format="json"
        )
        assert response.status_code == 200
        assert response.data["title"] == "Updated Request"

    @pytest.mark.django_db
    def test_delete_request(self, client, user, doc_request):
        client.force_authenticate(user=user)
        response = client.delete(f"{self.LIST_URL}{doc_request.pk}/")
        assert response.status_code == 204

    @pytest.mark.django_db
    def test_send_action(self, client, user, doc_request):
        client.force_authenticate(user=user)
        response = client.post(
            f"{self.LIST_URL}{doc_request.pk}/send/", format="json"
        )
        assert response.status_code == 200
        assert response.data["status"] == "sending"
        assert response.data["sent_at"] is not None

    @pytest.mark.django_db
    def test_remind_action(self, client, user, doc_request):
        client.force_authenticate(user=user)
        response = client.post(
            f"{self.LIST_URL}{doc_request.pk}/remind/", format="json"
        )
        assert response.status_code == 200
        assert response.data["status"] == "reminder_sent"
        assert response.data["reminder_sent_at"] is not None

    @pytest.mark.django_db
    def test_unauthenticated_access_denied(self, client):
        response = client.get(self.LIST_URL)
        assert response.status_code in (401, 403)


# ===========================================================================
# Admin Views - Submission List & Review
# ===========================================================================


class TestPortalSubmissionAdminViews:
    """Tests for PortalSubmissionListView and PortalSubmissionReviewView."""

    LIST_URL = "/api/v1/portal-submissions/"

    @pytest.mark.django_db
    def test_list_submissions(self, client, user, submission):
        client.force_authenticate(user=user)
        response = client.get(self.LIST_URL)
        assert response.status_code == 200
        assert len(response.data) >= 1

    @pytest.mark.django_db
    def test_list_filter_by_portal(self, client, user, portal, submission):
        client.force_authenticate(user=user)
        response = client.get(f"{self.LIST_URL}?portal={portal.pk}")
        assert response.status_code == 200
        assert len(response.data) >= 1

    @pytest.mark.django_db
    def test_list_filter_by_status(self, client, user, submission):
        client.force_authenticate(user=user)
        response = client.get(f"{self.LIST_URL}?status={SUBMISSION_PENDING}")
        assert response.status_code == 200
        assert len(response.data) >= 1

    @pytest.mark.django_db
    def test_list_filter_by_request(self, client, user, doc_request, submission):
        client.force_authenticate(user=user)
        response = client.get(f"{self.LIST_URL}?request={doc_request.pk}")
        assert response.status_code == 200
        assert len(response.data) >= 1

    @pytest.mark.django_db
    def test_list_filter_returns_empty_for_nonexistent(self, client, user, submission):
        client.force_authenticate(user=user)
        response = client.get(f"{self.LIST_URL}?portal=99999")
        assert response.status_code == 200
        assert len(response.data) == 0

    @pytest.mark.django_db
    def test_approve_submission_creates_document(self, client, user, submission):
        client.force_authenticate(user=user)
        data = {"status": SUBMISSION_APPROVED, "review_notes": "Looks good"}
        response = client.patch(
            f"{self.LIST_URL}{submission.pk}/review/",
            data,
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == SUBMISSION_APPROVED
        assert response.data["ingested_document"] is not None
        assert response.data["reviewed_by"] == user.pk

    @pytest.mark.django_db
    def test_reject_submission(self, client, user, submission):
        client.force_authenticate(user=user)
        data = {"status": SUBMISSION_REJECTED, "review_notes": "Incorrect format"}
        response = client.patch(
            f"{self.LIST_URL}{submission.pk}/review/",
            data,
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == SUBMISSION_REJECTED
        assert response.data["ingested_document"] is None
        assert response.data["review_notes"] == "Incorrect format"

    @pytest.mark.django_db
    def test_review_already_reviewed_returns_400(self, client, user, submission):
        """Cannot review a submission that has already been reviewed."""
        submission.status = SUBMISSION_APPROVED
        submission.save()

        client.force_authenticate(user=user)
        data = {"status": SUBMISSION_REJECTED}
        response = client.patch(
            f"{self.LIST_URL}{submission.pk}/review/",
            data,
            format="json",
        )
        assert response.status_code == 400
        assert "already been reviewed" in response.data["error"]

    @pytest.mark.django_db
    def test_review_nonexistent_returns_404(self, client, user):
        client.force_authenticate(user=user)
        data = {"status": SUBMISSION_APPROVED}
        response = client.patch(
            f"{self.LIST_URL}99999/review/",
            data,
            format="json",
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_review_unauthenticated(self, client, submission):
        data = {"status": SUBMISSION_APPROVED}
        response = client.patch(
            f"{self.LIST_URL}{submission.pk}/review/",
            data,
            format="json",
        )
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_list_unauthenticated(self, client):
        response = client.get(self.LIST_URL)
        assert response.status_code in (401, 403)


# ===========================================================================
# Public Views - Portal
# ===========================================================================


class TestPublicPortalView:
    """Tests for GET /api/v1/portal/{slug}/ (public, no auth)."""

    @pytest.mark.django_db
    def test_get_public_portal_info(self, client, portal):
        response = client.get(f"/api/v1/portal/{portal.slug}/")
        assert response.status_code == 200
        assert response.data["name"] == "Test Portal"
        assert response.data["slug"] == "test-portal"
        assert response.data["welcome_text"] == "Welcome!"
        assert response.data["require_email"] is True
        assert response.data["require_name"] is True
        assert "max_file_size_mb" in response.data

    @pytest.mark.django_db
    def test_public_portal_no_sensitive_fields(self, client, portal):
        """Public serializer should not expose admin-only fields."""
        response = client.get(f"/api/v1/portal/{portal.slug}/")
        assert response.status_code == 200
        assert "id" not in response.data
        assert "is_active" not in response.data
        assert "created_at" not in response.data

    @pytest.mark.django_db
    def test_inactive_portal_returns_404(self, client, inactive_portal):
        response = client.get(f"/api/v1/portal/{inactive_portal.slug}/")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_invalid_slug_returns_404(self, client):
        response = client.get("/api/v1/portal/nonexistent-slug/")
        assert response.status_code == 404


class TestPublicPortalUpload:
    """Tests for POST /api/v1/portal/{slug}/upload/ (public, no auth)."""

    @pytest.mark.django_db
    def test_upload_file_successfully(self, client, portal):
        data = {
            "file": _make_upload_file(),
            "email": "uploader@example.com",
            "name": "John Doe",
        }
        response = client.post(
            f"/api/v1/portal/{portal.slug}/upload/",
            data,
            format="multipart",
        )
        assert response.status_code == 201
        assert "id" in response.data
        assert response.data["original_filename"] == "upload.pdf"

    @pytest.mark.django_db
    def test_upload_creates_submission_record(self, client, portal):
        data = {
            "file": _make_upload_file(),
            "email": "uploader@example.com",
            "name": "John Doe",
        }
        client.post(
            f"/api/v1/portal/{portal.slug}/upload/",
            data,
            format="multipart",
        )
        assert PortalSubmission.objects.filter(portal=portal).count() == 1

    @pytest.mark.django_db
    def test_upload_inactive_portal_returns_404(self, client, inactive_portal):
        data = {
            "file": _make_upload_file(),
            "email": "uploader@example.com",
            "name": "John",
        }
        response = client.post(
            f"/api/v1/portal/{inactive_portal.slug}/upload/",
            data,
            format="multipart",
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_upload_missing_email_when_required(self, client, portal):
        """Portal requires email but none provided."""
        data = {
            "file": _make_upload_file(),
            "name": "John",
        }
        response = client.post(
            f"/api/v1/portal/{portal.slug}/upload/",
            data,
            format="multipart",
        )
        assert response.status_code == 400
        assert "Email" in response.data.get("error", "")

    @pytest.mark.django_db
    def test_upload_missing_name_when_required(self, client, portal):
        """Portal requires name but none provided."""
        data = {
            "file": _make_upload_file(),
            "email": "uploader@example.com",
        }
        response = client.post(
            f"/api/v1/portal/{portal.slug}/upload/",
            data,
            format="multipart",
        )
        assert response.status_code == 400
        assert "Name" in response.data.get("error", "")

    @pytest.mark.django_db
    def test_upload_without_required_fields_when_not_required(self, client, user):
        """Portal that doesn't require email/name should accept upload without them."""
        portal = PortalConfig.objects.create(
            name="Lenient Portal",
            slug="lenient",
            is_active=True,
            require_email=False,
            require_name=False,
            created_by=user,
        )
        data = {"file": _make_upload_file()}
        response = client.post(
            f"/api/v1/portal/{portal.slug}/upload/",
            data,
            format="multipart",
        )
        assert response.status_code == 201

    @pytest.mark.django_db
    def test_upload_no_file_returns_400(self, client, portal):
        data = {"email": "uploader@example.com", "name": "John"}
        response = client.post(
            f"/api/v1/portal/{portal.slug}/upload/",
            data,
            format="multipart",
        )
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_upload_nonexistent_slug_returns_404(self, client):
        data = {
            "file": _make_upload_file(),
            "email": "a@b.com",
            "name": "X",
        }
        response = client.post(
            "/api/v1/portal/nonexistent/upload/",
            data,
            format="multipart",
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_upload_rate_limit(self, client, portal, settings):
        """After exceeding the rate limit, uploads should be rejected."""
        settings.PORTAL_UPLOAD_RATE_LIMIT = 3
        for i in range(3):
            f = _make_upload_file(name=f"file{i}.pdf")
            data = {
                "file": f,
                "email": "uploader@example.com",
                "name": "John",
            }
            resp = client.post(
                f"/api/v1/portal/{portal.slug}/upload/",
                data,
                format="multipart",
            )
            assert resp.status_code == 201

        # 4th upload should be rate limited
        f = _make_upload_file(name="extra.pdf")
        data = {
            "file": f,
            "email": "uploader@example.com",
            "name": "John",
        }
        response = client.post(
            f"/api/v1/portal/{portal.slug}/upload/",
            data,
            format="multipart",
        )
        assert response.status_code == 429
        assert "rate limit" in response.data["error"].lower()


# ===========================================================================
# Public Views - Request
# ===========================================================================


class TestPublicRequestView:
    """Tests for GET /api/v1/request/{token}/ (public, no auth)."""

    @pytest.mark.django_db
    def test_get_request_info(self, client, doc_request):
        response = client.get(f"/api/v1/request/{doc_request.token}/")
        assert response.status_code == 200
        assert response.data["title"] == "Submit Tax Docs"
        assert response.data["portal_name"] == "Test Portal"
        assert "description" in response.data
        assert "deadline" in response.data

    @pytest.mark.django_db
    def test_invalid_token_returns_404(self, client):
        response = client.get("/api/v1/request/invalid-token-value/")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_request_inactive_portal_returns_404(self, client, inactive_portal):
        req = DocumentRequest.objects.create(
            portal=inactive_portal,
            title="Hidden Request",
            assignee_email="a@b.com",
        )
        response = client.get(f"/api/v1/request/{req.token}/")
        assert response.status_code == 404


class TestPublicRequestUpload:
    """Tests for POST /api/v1/request/{token}/upload/ (public, no auth)."""

    @pytest.mark.django_db
    def test_upload_against_request(self, client, doc_request):
        data = {
            "file": _make_upload_file(),
            "email": "contributor@example.com",
            "name": "Jane Doe",
        }
        response = client.post(
            f"/api/v1/request/{doc_request.token}/upload/",
            data,
            format="multipart",
        )
        assert response.status_code == 201
        assert response.data["original_filename"] == "upload.pdf"

    @pytest.mark.django_db
    def test_upload_updates_request_status_to_partially_fulfilled(
        self, client, doc_request
    ):
        assert doc_request.status == REQUEST_PENDING
        data = {
            "file": _make_upload_file(),
            "email": "contributor@example.com",
            "name": "Jane Doe",
        }
        client.post(
            f"/api/v1/request/{doc_request.token}/upload/",
            data,
            format="multipart",
        )
        doc_request.refresh_from_db()
        assert doc_request.status == REQUEST_PARTIALLY_FULFILLED

    @pytest.mark.django_db
    def test_upload_links_submission_to_request(self, client, doc_request):
        data = {
            "file": _make_upload_file(),
        }
        client.post(
            f"/api/v1/request/{doc_request.token}/upload/",
            data,
            format="multipart",
        )
        sub = PortalSubmission.objects.first()
        assert sub.request == doc_request

    @pytest.mark.django_db
    def test_upload_invalid_token_returns_404(self, client):
        data = {
            "file": _make_upload_file(),
        }
        response = client.post(
            "/api/v1/request/bad-token/upload/",
            data,
            format="multipart",
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_upload_expired_request_returns_400(self, client, doc_request):
        doc_request.status = REQUEST_EXPIRED
        doc_request.save()
        data = {
            "file": _make_upload_file(),
        }
        response = client.post(
            f"/api/v1/request/{doc_request.token}/upload/",
            data,
            format="multipart",
        )
        assert response.status_code == 400
        assert "no longer accepting" in response.data["error"].lower()

    @pytest.mark.django_db
    def test_upload_partially_fulfilled_still_works(self, client, doc_request):
        """A partially fulfilled request should still accept uploads."""
        doc_request.status = REQUEST_PARTIALLY_FULFILLED
        doc_request.save()
        data = {
            "file": _make_upload_file(),
        }
        response = client.post(
            f"/api/v1/request/{doc_request.token}/upload/",
            data,
            format="multipart",
        )
        assert response.status_code == 201

    @pytest.mark.django_db
    def test_upload_uses_assignee_info_when_not_provided(self, client, doc_request):
        """When email/name not provided, falls back to request assignee info."""
        data = {"file": _make_upload_file()}
        client.post(
            f"/api/v1/request/{doc_request.token}/upload/",
            data,
            format="multipart",
        )
        sub = PortalSubmission.objects.first()
        assert sub.submitter_email == doc_request.assignee_email
        assert sub.submitter_name == doc_request.assignee_name

    @pytest.mark.django_db
    def test_upload_rate_limit_on_request(self, client, doc_request, settings):
        """Rate limiting applies to request uploads too."""
        settings.PORTAL_UPLOAD_RATE_LIMIT = 2

        for i in range(2):
            data = {"file": _make_upload_file(name=f"f{i}.pdf")}
            resp = client.post(
                f"/api/v1/request/{doc_request.token}/upload/",
                data,
                format="multipart",
            )
            assert resp.status_code == 201

        data = {"file": _make_upload_file(name="extra.pdf")}
        response = client.post(
            f"/api/v1/request/{doc_request.token}/upload/",
            data,
            format="multipart",
        )
        assert response.status_code == 429
