"""Tests for collaboration module models."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.utils import timezone

from collaboration.models import Checkout, Comment, ShareLink
from documents.models import Document


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
def document(user):
    """Create a sample document."""
    return Document.objects.create(
        title="Test Document",
        content="Some content here.",
        filename="test_doc.pdf",
        owner=user,
    )


# --- Comment model tests ---


@pytest.mark.django_db
class TestCommentModel:
    """Tests for the Comment model."""

    def test_comment_creation(self, user, document):
        """Creating a comment stores text and associates with document and user."""
        comment = Comment.objects.create(
            document=document,
            user=user,
            text="This is a test comment.",
            created_by=user,
        )
        assert comment.pk is not None
        assert comment.text == "This is a test comment."
        assert comment.document == document
        assert comment.user == user

    def test_comment_str(self, user, document):
        """__str__ returns 'Comment by <user> on <document>'."""
        comment = Comment.objects.create(
            document=document,
            user=user,
            text="A comment.",
            created_by=user,
        )
        assert str(comment) == f"Comment by {user} on {document}"

    def test_comment_soft_delete(self, user, document):
        """soft_delete() sets deleted_at and hides from default manager."""
        comment = Comment.objects.create(
            document=document,
            user=user,
            text="To be soft deleted.",
            created_by=user,
        )
        comment.soft_delete()

        # Default manager should exclude soft-deleted comments
        assert Comment.objects.filter(pk=comment.pk).count() == 0
        # all_objects manager should still include it
        assert Comment.all_objects.filter(pk=comment.pk).count() == 1
        assert comment.is_deleted is True

    def test_comment_ordering(self, user, document):
        """Comments are ordered by -created_at (newest first)."""
        c1 = Comment.objects.create(
            document=document, user=user, text="First", created_by=user,
        )
        c2 = Comment.objects.create(
            document=document, user=user, text="Second", created_by=user,
        )
        comments = list(Comment.objects.filter(document=document))
        # c2 was created after c1 so should come first in -created_at ordering
        assert comments[0].pk == c2.pk
        assert comments[1].pk == c1.pk

    def test_comment_cascade_delete_with_document(self, user, document):
        """Deleting a document cascades to its comments."""
        Comment.objects.create(
            document=document, user=user, text="Will be gone.", created_by=user,
        )
        doc_pk = document.pk
        document.hard_delete()
        assert Comment.all_objects.filter(document_id=doc_pk).count() == 0


# --- Checkout model tests ---


@pytest.mark.django_db
class TestCheckoutModel:
    """Tests for the Checkout model."""

    def test_checkout_creation_and_not_expired(self, user, document):
        """Creating a checkout with future expiration is not expired."""
        checkout = Checkout.objects.create(
            document=document,
            user=user,
            expiration=timezone.now() + timedelta(hours=24),
        )
        assert checkout.pk is not None
        assert checkout.is_expired is False

    def test_checkout_is_expired_when_past(self, user, document):
        """A checkout with expiration in the past reports is_expired=True."""
        checkout = Checkout.objects.create(
            document=document,
            user=user,
            expiration=timezone.now() - timedelta(hours=1),
        )
        assert checkout.is_expired is True

    def test_checkout_is_expired_none_means_never(self, user, document):
        """A checkout with expiration=None never expires."""
        checkout = Checkout.objects.create(
            document=document,
            user=user,
            expiration=None,
        )
        assert checkout.is_expired is False

    def test_checkout_one_to_one_constraint(self, user, other_user, document):
        """Only one checkout per document (OneToOneField enforced)."""
        Checkout.objects.create(
            document=document,
            user=user,
            expiration=timezone.now() + timedelta(hours=24),
        )
        with pytest.raises(IntegrityError):
            Checkout.objects.create(
                document=document,
                user=other_user,
                expiration=timezone.now() + timedelta(hours=24),
            )


# --- ShareLink model tests ---


@pytest.mark.django_db
class TestShareLinkModel:
    """Tests for the ShareLink model."""

    def test_share_link_creation_auto_slug(self, user, document):
        """Creating a ShareLink auto-generates a slug."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
        )
        assert link.pk is not None
        assert link.slug is not None
        assert len(link.slug) > 0

    def test_share_link_set_and_check_password(self, user, document):
        """set_password hashes the password; check_password verifies it."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
        )
        link.set_password("mysecret")
        link.save()

        assert link.check_password("mysecret") is True
        assert link.check_password("wrongpassword") is False

    def test_share_link_has_password_property(self, user, document):
        """has_password is False when no password set, True after setting one."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
        )
        assert link.has_password is False

        link.set_password("secret123")
        assert link.has_password is True

    def test_share_link_not_expired(self, user, document):
        """A share link with future expiration is not expired."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
            expiration=timezone.now() + timedelta(hours=48),
        )
        assert link.is_expired is False

    def test_share_link_expired(self, user, document):
        """A share link with past expiration is expired."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
            expiration=timezone.now() - timedelta(hours=1),
        )
        assert link.is_expired is True

    def test_share_link_no_expiration_never_expires(self, user, document):
        """A share link with expiration=None never expires."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
            expiration=None,
        )
        assert link.is_expired is False

    def test_share_link_slug_uniqueness(self, user, document):
        """Two ShareLinks with the same slug should raise IntegrityError."""
        ShareLink.objects.create(
            document=document,
            created_by=user,
            slug="duplicate-slug",
        )
        with pytest.raises(IntegrityError):
            ShareLink.objects.create(
                document=document,
                created_by=user,
                slug="duplicate-slug",
            )

    def test_share_link_default_file_version(self, user, document):
        """Default file_version is 'original'."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
        )
        assert link.file_version == "original"

    def test_share_link_download_count_default(self, user, document):
        """download_count defaults to 0."""
        link = ShareLink.objects.create(
            document=document,
            created_by=user,
        )
        assert link.download_count == 0
