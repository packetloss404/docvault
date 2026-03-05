"""Tests for notification models."""

from django.contrib.auth.models import Group, User
from django.db import IntegrityError
from django.test import TestCase

from documents.models import Document
from notifications.constants import (
    CHANNEL_EMAIL,
    CHANNEL_IN_APP,
    CHANNEL_WEBHOOK,
    EVENT_DOCUMENT_ADDED,
    EVENT_DOCUMENT_PROCESSED,
    EVENT_PROCESSING_FAILED,
    EVENT_WORKFLOW_TRANSITION,
)
from notifications.models import Notification, NotificationPreference, Quota


class NotificationModelTest(TestCase):
    """Tests for the Notification model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123!"
        )

    def test_create_notification(self):
        """A notification can be created with required fields."""
        notification = Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="New document added",
            body="Document 'invoice.pdf' was added.",
        )
        self.assertIsNotNone(notification.pk)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.event_type, EVENT_DOCUMENT_ADDED)
        self.assertEqual(notification.title, "New document added")
        self.assertEqual(notification.body, "Document 'invoice.pdf' was added.")

    def test_str_representation_unread(self):
        """String representation shows [unread] for unread notifications."""
        notification = Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Test notification",
        )
        self.assertEqual(
            str(notification), "[unread] Test notification -> testuser"
        )

    def test_str_representation_read(self):
        """String representation shows [read] for read notifications."""
        notification = Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Test notification",
            read=True,
        )
        self.assertEqual(
            str(notification), "[read] Test notification -> testuser"
        )

    def test_default_read_is_false(self):
        """Notifications default to unread."""
        notification = Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Test",
        )
        self.assertFalse(notification.read)

    def test_mark_as_read(self):
        """A notification can be marked as read."""
        notification = Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Test",
        )
        self.assertFalse(notification.read)
        notification.read = True
        notification.save(update_fields=["read"])
        notification.refresh_from_db()
        self.assertTrue(notification.read)

    def test_ordering_newest_first(self):
        """Notifications are ordered newest first by default."""
        n1 = Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="First",
        )
        n2 = Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_PROCESSED,
            title="Second",
        )
        n3 = Notification.objects.create(
            user=self.user,
            event_type=EVENT_PROCESSING_FAILED,
            title="Third",
        )
        notifications = list(Notification.objects.filter(user=self.user))
        # Newest first
        self.assertEqual(notifications[0].pk, n3.pk)
        self.assertEqual(notifications[1].pk, n2.pk)
        self.assertEqual(notifications[2].pk, n1.pk)

    def test_cascade_delete_with_user(self):
        """Deleting a user cascades to delete their notifications."""
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Test",
        )
        self.assertEqual(Notification.objects.count(), 1)
        self.user.delete()
        self.assertEqual(Notification.objects.count(), 0)

    def test_notification_with_document_fk(self):
        """A notification can be linked to a document."""
        doc = Document.objects.create(
            title="Invoice",
            owner=self.user,
        )
        notification = Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Document added",
            document=doc,
        )
        self.assertEqual(notification.document, doc)
        self.assertEqual(notification.document.title, "Invoice")

    def test_notification_without_document(self):
        """A notification can exist without a linked document."""
        notification = Notification.objects.create(
            user=self.user,
            event_type=EVENT_WORKFLOW_TRANSITION,
            title="Workflow state changed",
        )
        self.assertIsNone(notification.document)

    def test_filter_by_event_type(self):
        """Notifications can be filtered by event_type."""
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Added",
        )
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_PROCESSING_FAILED,
            title="Failed",
        )
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Added 2",
        )
        added = Notification.objects.filter(event_type=EVENT_DOCUMENT_ADDED)
        self.assertEqual(added.count(), 2)
        failed = Notification.objects.filter(event_type=EVENT_PROCESSING_FAILED)
        self.assertEqual(failed.count(), 1)

    def test_filter_by_read_status(self):
        """Notifications can be filtered by read status."""
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Unread 1",
            read=False,
        )
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Read 1",
            read=True,
        )
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Unread 2",
            read=False,
        )
        unread = Notification.objects.filter(user=self.user, read=False)
        self.assertEqual(unread.count(), 2)
        read = Notification.objects.filter(user=self.user, read=True)
        self.assertEqual(read.count(), 1)


class NotificationPreferenceTest(TestCase):
    """Tests for the NotificationPreference model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123!"
        )

    def test_create_preference(self):
        """A notification preference can be created."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_IN_APP,
        )
        self.assertIsNotNone(pref.pk)
        self.assertEqual(pref.user, self.user)
        self.assertEqual(pref.event_type, EVENT_DOCUMENT_ADDED)
        self.assertEqual(pref.channel, CHANNEL_IN_APP)

    def test_unique_together_constraint(self):
        """The same user+event_type+channel combination cannot be duplicated."""
        NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_IN_APP,
        )
        with self.assertRaises(IntegrityError):
            NotificationPreference.objects.create(
                user=self.user,
                event_type=EVENT_DOCUMENT_ADDED,
                channel=CHANNEL_IN_APP,
            )

    def test_different_channel_same_event_allowed(self):
        """Same user and event_type with different channels is allowed."""
        NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_IN_APP,
        )
        pref2 = NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_EMAIL,
        )
        self.assertIsNotNone(pref2.pk)

    def test_str_representation(self):
        """String representation shows user, event, channel, and state."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_EMAIL,
            enabled=True,
        )
        self.assertEqual(
            str(pref), "testuser: document_added/email = on"
        )

    def test_str_representation_disabled(self):
        """String representation shows 'off' when disabled."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_EMAIL,
            enabled=False,
        )
        self.assertEqual(
            str(pref), "testuser: document_added/email = off"
        )

    def test_default_enabled_is_true(self):
        """Preferences default to enabled."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_IN_APP,
        )
        self.assertTrue(pref.enabled)

    def test_webhook_url_field(self):
        """Webhook URL can be set for webhook channel preferences."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_WEBHOOK,
            webhook_url="https://example.com/hook",
        )
        self.assertEqual(pref.webhook_url, "https://example.com/hook")

    def test_webhook_url_defaults_to_empty(self):
        """Webhook URL defaults to empty string."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_IN_APP,
        )
        self.assertEqual(pref.webhook_url, "")

    def test_cascade_delete_with_user(self):
        """Deleting a user cascades to delete their preferences."""
        NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_IN_APP,
        )
        NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_PROCESSED,
            channel=CHANNEL_EMAIL,
        )
        self.assertEqual(NotificationPreference.objects.count(), 2)
        self.user.delete()
        self.assertEqual(NotificationPreference.objects.count(), 0)


class QuotaModelTest(TestCase):
    """Tests for the Quota model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123!"
        )
        self.group = Group.objects.create(name="editors")

    def test_create_user_quota(self):
        """A user-specific quota can be created."""
        quota = Quota.objects.create(
            user=self.user,
            max_documents=100,
            max_storage_bytes=1_073_741_824,  # 1 GB
        )
        self.assertIsNotNone(quota.pk)
        self.assertEqual(quota.user, self.user)
        self.assertIsNone(quota.group)
        self.assertEqual(quota.max_documents, 100)
        self.assertEqual(quota.max_storage_bytes, 1_073_741_824)

    def test_create_group_quota(self):
        """A group quota can be created."""
        quota = Quota.objects.create(
            group=self.group,
            max_documents=500,
            max_storage_bytes=5_368_709_120,  # 5 GB
        )
        self.assertIsNotNone(quota.pk)
        self.assertIsNone(quota.user)
        self.assertEqual(quota.group, self.group)
        self.assertEqual(quota.max_documents, 500)

    def test_create_global_quota(self):
        """A global quota (user=None, group=None) can be created."""
        quota = Quota.objects.create(
            max_documents=1000,
            max_storage_bytes=10_737_418_240,  # 10 GB
        )
        self.assertIsNotNone(quota.pk)
        self.assertIsNone(quota.user)
        self.assertIsNone(quota.group)
        self.assertEqual(quota.max_documents, 1000)

    def test_str_representation_user_quota(self):
        """String representation for user quota."""
        quota = Quota.objects.create(
            user=self.user,
            max_documents=100,
        )
        self.assertEqual(str(quota), "Quota(User: testuser)")

    def test_str_representation_group_quota(self):
        """String representation for group quota."""
        quota = Quota.objects.create(
            group=self.group,
            max_documents=500,
        )
        self.assertEqual(str(quota), "Quota(Group: editors)")

    def test_str_representation_global_quota(self):
        """String representation for global quota."""
        quota = Quota.objects.create(
            max_documents=1000,
        )
        self.assertEqual(str(quota), "Quota(Global)")

    def test_cascade_delete_with_user(self):
        """Deleting a user cascades to delete their quotas."""
        quota = Quota.objects.create(user=self.user, max_documents=50)
        self.assertEqual(Quota.objects.filter(pk=quota.pk).count(), 1)
        self.user.delete()
        self.assertEqual(Quota.objects.filter(pk=quota.pk).count(), 0)

    def test_cascade_delete_with_group(self):
        """Deleting a group cascades to delete its quotas."""
        quota = Quota.objects.create(group=self.group, max_documents=200)
        self.assertEqual(Quota.objects.filter(pk=quota.pk).count(), 1)
        self.group.delete()
        self.assertEqual(Quota.objects.filter(pk=quota.pk).count(), 0)

    def test_null_fields_for_unlimited(self):
        """Null max_documents and max_storage_bytes mean unlimited."""
        quota = Quota.objects.create(
            user=self.user,
            max_documents=None,
            max_storage_bytes=None,
        )
        self.assertIsNone(quota.max_documents)
        self.assertIsNone(quota.max_storage_bytes)

    def test_partial_limits(self):
        """A quota can limit documents but not storage, or vice versa."""
        quota_docs_only = Quota.objects.create(
            user=self.user,
            max_documents=50,
            max_storage_bytes=None,
        )
        self.assertEqual(quota_docs_only.max_documents, 50)
        self.assertIsNone(quota_docs_only.max_storage_bytes)
