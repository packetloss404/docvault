"""Tests for collaboration module signal handlers."""

from unittest.mock import patch

import pytest
from django.contrib.auth.models import User

from collaboration.models import Comment
from documents.models import Document


@pytest.fixture
def user(db):
    """Create and return a regular user."""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="pass123!"
    )


@pytest.fixture
def doc_owner(db):
    """Create and return the document owner."""
    return User.objects.create_user(
        username="docowner", email="owner@example.com", password="pass123!"
    )


@pytest.fixture
def document(doc_owner):
    """Create a sample document owned by doc_owner."""
    return Document.objects.create(
        title="Signal Test Doc",
        content="Content.",
        filename="signal_test.pdf",
        owner=doc_owner,
    )


@pytest.fixture
def document_no_owner(db):
    """Create a document with no owner."""
    return Document.objects.create(
        title="No Owner Doc",
        content="Content.",
        filename="no_owner.pdf",
        owner=None,
    )


@pytest.mark.django_db
class TestNotifyCommentAddedSignal:
    """Tests for the notify_comment_added signal handler."""

    @patch("collaboration.signals.send_notification")
    def test_comment_creation_triggers_notification(
        self, mock_send, user, doc_owner, document
    ):
        """Creating a comment sends a notification to the document owner."""
        Comment.objects.create(
            document=document,
            user=user,
            text="Great document!",
            created_by=user,
        )
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["user"] == doc_owner
        assert call_kwargs["event_type"] == "comment_added"
        assert call_kwargs["document"] == document
        assert "testuser" in call_kwargs["body"]

    @patch("collaboration.signals.send_notification")
    def test_comment_by_doc_owner_does_not_self_notify(
        self, mock_send, doc_owner, document
    ):
        """The document owner commenting on their own doc does not trigger a notification."""
        Comment.objects.create(
            document=document,
            user=doc_owner,
            text="My own comment.",
            created_by=doc_owner,
        )
        mock_send.assert_not_called()

    @patch("collaboration.signals.send_notification")
    def test_comment_on_doc_with_no_owner_does_not_crash(
        self, mock_send, user, document_no_owner
    ):
        """Commenting on a document with no owner should not crash or notify."""
        Comment.objects.create(
            document=document_no_owner,
            user=user,
            text="Comment on orphan doc.",
            created_by=user,
        )
        mock_send.assert_not_called()

    @patch("collaboration.signals.send_notification")
    def test_updating_comment_does_not_trigger_notification(
        self, mock_send, user, doc_owner, document
    ):
        """Updating an existing comment (not created=True) should not notify."""
        comment = Comment.objects.create(
            document=document,
            user=user,
            text="Initial text.",
            created_by=user,
        )
        # Reset mock after the creation call
        mock_send.reset_mock()

        # Update the comment
        comment.text = "Updated text."
        comment.save(update_fields=["text", "updated_at"])

        mock_send.assert_not_called()
