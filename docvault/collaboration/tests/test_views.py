"""Tests for collaboration module API views."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from collaboration.models import Checkout, Comment, ShareLink
from documents.models import Document
from notifications.models import Notification


@pytest.fixture
def api_client():
    """Return an APIClient instance."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create and return a regular user."""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="pass123!"
    )


@pytest.fixture
def other_user(db):
    """Create and return a second user."""
    return User.objects.create_user(
        username="otheruser", email="other@example.com", password="pass123!"
    )


@pytest.fixture
def admin_user(db):
    """Create and return a superuser."""
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass123!"
    )


@pytest.fixture
def document(user):
    """Create a sample document owned by user."""
    return Document.objects.create(
        title="Test Document",
        content="Some content here.",
        filename="test_doc.pdf",
        owner=user,
    )


@pytest.fixture
def document_no_owner(db):
    """Create a document with no owner."""
    return Document.objects.create(
        title="Orphan Document",
        content="No owner.",
        filename="orphan_doc.pdf",
        owner=None,
    )


# --- Comment Views ---


@pytest.mark.django_db
class TestDocumentCommentListView:
    """Tests for GET/POST /api/v1/documents/{id}/comments/"""

    def test_get_comments_requires_auth(self, api_client, document):
        """Unauthenticated request returns 401."""
        resp = api_client.get(f"/api/v1/documents/{document.pk}/comments/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_comments_returns_list(self, api_client, user, document):
        """Authenticated GET returns list of comments for the document."""
        Comment.objects.create(
            document=document, user=user, text="First comment.", created_by=user,
        )
        Comment.objects.create(
            document=document, user=user, text="Second comment.", created_by=user,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.get(f"/api/v1/documents/{document.pk}/comments/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 2

    def test_post_comment_creates_new(self, api_client, user, document):
        """POST with text creates a new comment and returns 201."""
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            f"/api/v1/documents/{document.pk}/comments/",
            {"text": "New comment."},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["text"] == "New comment."
        assert resp.data["user"] == user.pk
        assert Comment.objects.filter(document=document).count() == 1

    def test_post_comment_missing_doc_returns_404(self, api_client, user):
        """POST to a non-existent document ID returns 404."""
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            "/api/v1/documents/99999/comments/",
            {"text": "Comment on missing doc."},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestDocumentCommentDetailView:
    """Tests for PATCH/DELETE /api/v1/documents/{id}/comments/{cid}/"""

    def test_patch_comment_updates_text(self, api_client, user, document):
        """PATCH by the comment owner updates the text."""
        comment = Comment.objects.create(
            document=document, user=user, text="Original text.", created_by=user,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.patch(
            f"/api/v1/documents/{document.pk}/comments/{comment.pk}/",
            {"text": "Updated text."},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["text"] == "Updated text."

    def test_patch_comment_by_non_owner_returns_403(
        self, api_client, user, other_user, document
    ):
        """PATCH by a user who is not the comment owner returns 403."""
        comment = Comment.objects.create(
            document=document, user=user, text="Owner's comment.", created_by=user,
        )
        api_client.force_authenticate(user=other_user)
        resp = api_client.patch(
            f"/api/v1/documents/{document.pk}/comments/{comment.pk}/",
            {"text": "Hijack attempt."},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_comment_soft_deletes(self, api_client, user, document):
        """DELETE soft-deletes the comment (hidden from default manager)."""
        comment = Comment.objects.create(
            document=document, user=user, text="To delete.", created_by=user,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.delete(
            f"/api/v1/documents/{document.pk}/comments/{comment.pk}/"
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        # Should be hidden from default manager
        assert Comment.objects.filter(pk=comment.pk).count() == 0
        # But still exists in all_objects
        assert Comment.all_objects.filter(pk=comment.pk).count() == 1

    def test_delete_by_admin_allowed(self, api_client, user, admin_user, document):
        """A superuser can delete any comment."""
        comment = Comment.objects.create(
            document=document, user=user, text="User's comment.", created_by=user,
        )
        api_client.force_authenticate(user=admin_user)
        resp = api_client.delete(
            f"/api/v1/documents/{document.pk}/comments/{comment.pk}/"
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT


# --- Checkout Views ---


@pytest.mark.django_db
class TestDocumentCheckoutView:
    """Tests for POST /api/v1/documents/{id}/checkout/"""

    def test_post_checkout_creates_lock(self, api_client, user, document):
        """POST creates a checkout lock on the document."""
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            f"/api/v1/documents/{document.pk}/checkout/",
            {"expiration_hours": 8},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["document"] == document.pk
        assert Checkout.objects.filter(document=document).exists()

    def test_post_checkout_already_checked_out_returns_409(
        self, api_client, user, other_user, document
    ):
        """POST on an already-checked-out document returns 409."""
        Checkout.objects.create(
            document=document,
            user=other_user,
            expiration=timezone.now() + timedelta(hours=24),
        )
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            f"/api/v1/documents/{document.pk}/checkout/",
            {"expiration_hours": 8},
            format="json",
        )
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert "already checked out" in resp.data["error"].lower()

    def test_post_checkout_replaces_expired(self, api_client, user, other_user, document):
        """POST on a document with an expired checkout replaces it."""
        Checkout.objects.create(
            document=document,
            user=other_user,
            expiration=timezone.now() - timedelta(hours=1),
        )
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            f"/api/v1/documents/{document.pk}/checkout/",
            {"expiration_hours": 4},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        checkout = Checkout.objects.get(document=document)
        assert checkout.user == user


@pytest.mark.django_db
class TestDocumentCheckinView:
    """Tests for POST /api/v1/documents/{id}/checkin/"""

    def test_post_checkin_releases_lock(self, api_client, user, document):
        """POST by the checker-outer releases the lock."""
        Checkout.objects.create(
            document=document,
            user=user,
            expiration=timezone.now() + timedelta(hours=24),
        )
        api_client.force_authenticate(user=user)
        resp = api_client.post(f"/api/v1/documents/{document.pk}/checkin/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "checked_in"
        assert not Checkout.objects.filter(document=document).exists()

    def test_post_checkin_by_doc_owner_allowed(
        self, api_client, user, other_user, document
    ):
        """The document owner can check in a document checked out by someone else."""
        Checkout.objects.create(
            document=document,
            user=other_user,
            expiration=timezone.now() + timedelta(hours=24),
        )
        # user is the document owner
        api_client.force_authenticate(user=user)
        resp = api_client.post(f"/api/v1/documents/{document.pk}/checkin/")
        assert resp.status_code == status.HTTP_200_OK
        assert not Checkout.objects.filter(document=document).exists()


@pytest.mark.django_db
class TestDocumentCheckoutStatusView:
    """Tests for GET /api/v1/documents/{id}/checkout_status/"""

    def test_get_status_not_checked_out(self, api_client, user, document):
        """GET returns checked_out=False when no checkout exists."""
        api_client.force_authenticate(user=user)
        resp = api_client.get(
            f"/api/v1/documents/{document.pk}/checkout_status/"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["checked_out"] is False

    def test_get_status_when_checked_out(self, api_client, user, document):
        """GET returns checked_out=True with checkout data when locked."""
        Checkout.objects.create(
            document=document,
            user=user,
            expiration=timezone.now() + timedelta(hours=24),
        )
        api_client.force_authenticate(user=user)
        resp = api_client.get(
            f"/api/v1/documents/{document.pk}/checkout_status/"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["checked_out"] is True
        assert "checkout" in resp.data


# --- Share Link Views ---


@pytest.mark.django_db
class TestDocumentShareCreateView:
    """Tests for POST /api/v1/documents/{id}/share/"""

    def test_post_share_creates_link_with_slug(self, api_client, user, document):
        """POST creates a share link with an auto-generated slug."""
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            f"/api/v1/documents/{document.pk}/share/",
            {},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert "slug" in resp.data
        assert len(resp.data["slug"]) > 0
        assert ShareLink.objects.filter(document=document).count() == 1

    def test_post_share_with_password(self, api_client, user, document):
        """POST with password creates a password-protected share link."""
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            f"/api/v1/documents/{document.pk}/share/",
            {"password": "s3cret"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["has_password"] is True
        link = ShareLink.objects.get(pk=resp.data["id"])
        assert link.check_password("s3cret") is True

    def test_post_share_with_expiration(self, api_client, user, document):
        """POST with expiration_hours sets an expiration time."""
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            f"/api/v1/documents/{document.pk}/share/",
            {"expiration_hours": 48},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["expiration"] is not None


@pytest.mark.django_db
class TestShareLinkListView:
    """Tests for GET /api/v1/share-links/"""

    def test_get_share_links_lists_own(self, api_client, user, other_user, document):
        """GET returns only the current user's share links."""
        ShareLink.objects.create(document=document, created_by=user)
        ShareLink.objects.create(document=document, created_by=other_user)

        api_client.force_authenticate(user=user)
        resp = api_client.get("/api/v1/share-links/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1


@pytest.mark.django_db
class TestShareLinkDeleteView:
    """Tests for DELETE /api/v1/share-links/{id}/"""

    def test_delete_share_link_revokes(self, api_client, user, document):
        """DELETE removes the share link."""
        link = ShareLink.objects.create(document=document, created_by=user)
        api_client.force_authenticate(user=user)
        resp = api_client.delete(f"/api/v1/share-links/{link.pk}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not ShareLink.objects.filter(pk=link.pk).exists()


@pytest.mark.django_db
class TestPublicShareAccessView:
    """Tests for GET/POST /api/v1/share/{slug}/ (no auth required)."""

    def test_get_public_share_no_password(self, api_client, user, document):
        """GET on a non-password-protected link returns document info."""
        link = ShareLink.objects.create(
            document=document, created_by=user, slug="open-link-abc",
        )
        resp = api_client.get("/api/v1/share/open-link-abc/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["document_id"] == document.pk
        assert resp.data["document_title"] == document.title
        # download_count should have incremented
        link.refresh_from_db()
        assert link.download_count == 1

    def test_get_public_share_with_password_returns_requires_password(
        self, api_client, user, document
    ):
        """GET on a password-protected link returns requires_password=True."""
        link = ShareLink.objects.create(
            document=document, created_by=user, slug="pwd-link-xyz",
        )
        link.set_password("secret")
        link.save()

        resp = api_client.get("/api/v1/share/pwd-link-xyz/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["requires_password"] is True

    def test_post_public_share_verifies_password(self, api_client, user, document):
        """POST with correct password returns document info."""
        link = ShareLink.objects.create(
            document=document, created_by=user, slug="pwd-verify",
        )
        link.set_password("mypass")
        link.save()

        # Correct password
        resp = api_client.post(
            "/api/v1/share/pwd-verify/",
            {"password": "mypass"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["document_id"] == document.pk

        # Wrong password
        resp_bad = api_client.post(
            "/api/v1/share/pwd-verify/",
            {"password": "wrong"},
            format="json",
        )
        assert resp_bad.status_code == status.HTTP_403_FORBIDDEN

    def test_get_expired_share_returns_404(self, api_client, user, document):
        """GET on an expired share link returns 404."""
        ShareLink.objects.create(
            document=document,
            created_by=user,
            slug="expired-link",
            expiration=timezone.now() - timedelta(hours=1),
        )
        resp = api_client.get("/api/v1/share/expired-link/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# --- Activity Views ---


@pytest.mark.django_db
class TestDocumentActivityView:
    """Tests for GET /api/v1/documents/{id}/activity/"""

    def test_get_document_activity_returns_entries(
        self, api_client, user, document
    ):
        """GET returns notification-based activity entries for the document."""
        # Note: document creation may trigger its own notification via signals,
        # so we count existing notifications first.
        existing_count = Notification.objects.filter(document=document).count()

        Notification.objects.create(
            user=user,
            event_type="comment_added",
            title="New comment",
            body="Someone commented.",
            document=document,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.get(f"/api/v1/documents/{document.pk}/activity/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == existing_count + 1
        # The most recent entry should be the comment_added notification
        assert resp.data[0]["event_type"] == "comment_added"
        assert resp.data[0]["document_id"] == document.pk


@pytest.mark.django_db
class TestGlobalActivityView:
    """Tests for GET /api/v1/activity/"""

    def test_get_global_activity_filtered_for_non_superuser(
        self, api_client, user, other_user, document
    ):
        """Non-superuser only sees their own notifications in global activity."""
        # Count any pre-existing notifications for user (e.g., from document creation signals)
        existing_user_count = Notification.objects.filter(user=user).count()

        Notification.objects.create(
            user=user,
            event_type="comment_added",
            title="User's notification",
            body="For the user.",
            document=document,
        )
        Notification.objects.create(
            user=other_user,
            event_type="document_added",
            title="Other's notification",
            body="For the other user.",
            document=document,
        )

        # Authenticate as regular user - should only see own notifications
        api_client.force_authenticate(user=user)
        resp = api_client.get("/api/v1/activity/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == existing_user_count + 1
        # Most recent should be the one we just created
        assert resp.data[0]["title"] == "User's notification"
        # None should belong to other_user
        for entry in resp.data:
            assert entry["user"] != other_user.username

    def test_get_global_activity_superuser_sees_all(
        self, api_client, user, admin_user, document
    ):
        """Superuser sees all notifications in global activity."""
        # Count any pre-existing notifications (e.g., from document creation signals)
        existing_total = Notification.objects.count()

        Notification.objects.create(
            user=user,
            event_type="comment_added",
            title="User notification",
            body="For user.",
            document=document,
        )
        Notification.objects.create(
            user=admin_user,
            event_type="document_added",
            title="Admin notification",
            body="For admin.",
            document=document,
        )

        api_client.force_authenticate(user=admin_user)
        resp = api_client.get("/api/v1/activity/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == existing_total + 2
