"""Tests for collaboration module Celery tasks."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from collaboration.models import Checkout, ShareLink
from collaboration.tasks import cleanup_expired_share_links, release_expired_checkouts
from documents.models import Document


@pytest.fixture
def user(db):
    """Create and return a regular user."""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="pass123!"
    )


@pytest.fixture
def document(user):
    """Create a sample document."""
    return Document.objects.create(
        title="Task Test Doc",
        content="Content.",
        filename="task_test.pdf",
        owner=user,
    )


@pytest.fixture
def second_document(user):
    """Create a second document (needed for multiple checkouts)."""
    return Document.objects.create(
        title="Second Doc",
        content="More content.",
        filename="second_doc.pdf",
        owner=user,
    )


# --- release_expired_checkouts ---


@pytest.mark.django_db
class TestReleaseExpiredCheckouts:
    """Tests for the release_expired_checkouts task."""

    def test_deletes_expired_checkouts(self, user, document):
        """Expired checkouts should be deleted by the task."""
        Checkout.objects.create(
            document=document,
            user=user,
            expiration=timezone.now() - timedelta(hours=1),
        )
        result = release_expired_checkouts()
        assert result["released"] == 1
        assert Checkout.objects.filter(document=document).count() == 0

    def test_leaves_non_expired_checkouts(self, user, document, second_document):
        """Non-expired checkouts should not be deleted."""
        Checkout.objects.create(
            document=document,
            user=user,
            expiration=timezone.now() + timedelta(hours=24),
        )
        # Also create an expired one on a different document to verify
        Checkout.objects.create(
            document=second_document,
            user=user,
            expiration=timezone.now() - timedelta(hours=1),
        )
        result = release_expired_checkouts()
        assert result["released"] == 1
        # The non-expired checkout should remain
        assert Checkout.objects.filter(document=document).exists()
        # The expired one should be gone
        assert not Checkout.objects.filter(document=second_document).exists()


# --- cleanup_expired_share_links ---


@pytest.mark.django_db
class TestCleanupExpiredShareLinks:
    """Tests for the cleanup_expired_share_links task."""

    def test_deletes_old_expired_share_links(self, user, document):
        """Share links expired more than 30 days ago should be deleted."""
        ShareLink.objects.create(
            document=document,
            created_by=user,
            expiration=timezone.now() - timedelta(days=31),
        )
        result = cleanup_expired_share_links()
        assert result["cleaned"] == 1
        assert ShareLink.objects.filter(document=document).count() == 0

    def test_leaves_recently_expired_share_links(self, user, document):
        """Share links expired less than 30 days ago should be kept."""
        ShareLink.objects.create(
            document=document,
            created_by=user,
            slug="recently-expired",
            expiration=timezone.now() - timedelta(days=5),
        )
        ShareLink.objects.create(
            document=document,
            created_by=user,
            slug="old-expired",
            expiration=timezone.now() - timedelta(days=60),
        )
        result = cleanup_expired_share_links()
        assert result["cleaned"] == 1
        # The recently expired link should remain
        assert ShareLink.objects.filter(slug="recently-expired").exists()
        # The old one should be gone
        assert not ShareLink.objects.filter(slug="old-expired").exists()
