"""Tests for notification API views."""

from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from documents.models import Document
from notifications.constants import (
    CHANNEL_EMAIL,
    CHANNEL_IN_APP,
    CHANNEL_WEBHOOK,
    EVENT_DOCUMENT_ADDED,
    EVENT_DOCUMENT_PROCESSED,
    EVENT_PROCESSING_FAILED,
)
from notifications.models import Notification, NotificationPreference, Quota


class NotificationViewTest(TestCase):
    """Tests for the Notification API endpoints."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123!"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_notifications(self):
        """GET /api/v1/notifications/ returns all notifications for user."""
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Doc 1 added",
        )
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_PROCESSED,
            title="Doc 1 processed",
        )

        resp = self.client.get("/api/v1/notifications/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 2)

    def test_list_unread_only(self):
        """GET /api/v1/notifications/?unread=true returns only unread."""
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Read one",
            read=True,
        )
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Unread one",
            read=False,
        )

        resp = self.client.get("/api/v1/notifications/", {"unread": "true"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Unread one")

    def test_mark_read(self):
        """POST /api/v1/notifications/{id}/read/ marks notification as read."""
        notification = Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="To be read",
        )
        self.assertFalse(notification.read)

        resp = self.client.post(f"/api/v1/notifications/{notification.pk}/read/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.read)

    def test_mark_all_read(self):
        """POST /api/v1/notifications/read_all/ marks all as read."""
        for i in range(3):
            Notification.objects.create(
                user=self.user,
                event_type=EVENT_DOCUMENT_ADDED,
                title=f"Notification {i}",
            )

        resp = self.client.post("/api/v1/notifications/read_all/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["marked_read"], 3)

        # Verify all are now read
        unread_count = Notification.objects.filter(
            user=self.user, read=False
        ).count()
        self.assertEqual(unread_count, 0)

    def test_unread_count(self):
        """GET /api/v1/notifications/unread_count/ returns unread count."""
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Unread 1",
            read=False,
        )
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Unread 2",
            read=False,
        )
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Read 1",
            read=True,
        )

        resp = self.client.get("/api/v1/notifications/unread_count/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)

    def test_notifications_require_auth(self):
        """Unauthenticated requests should return 401."""
        unauth_client = APIClient()
        resp = unauth_client.get("/api/v1/notifications/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_only_sees_own_notifications(self):
        """User A should not see User B's notifications."""
        user_b = User.objects.create_user(
            username="userb", password="testpass123!"
        )
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Admin notification",
        )
        Notification.objects.create(
            user=user_b,
            event_type=EVENT_DOCUMENT_ADDED,
            title="User B notification",
        )

        # Authenticate as user_b
        client_b = APIClient()
        client_b.force_authenticate(user=user_b)
        resp = client_b.get("/api/v1/notifications/")
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "User B notification")

    def test_delete_notification(self):
        """DELETE /api/v1/notifications/{id}/ removes the notification."""
        notification = Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="To delete",
        )

        resp = self.client.delete(f"/api/v1/notifications/{notification.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Notification.objects.filter(pk=notification.pk).exists())

    def test_mark_read_already_read(self):
        """Marking an already-read notification as read should be idempotent."""
        notification = Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Already read",
            read=True,
        )

        resp = self.client.post(f"/api/v1/notifications/{notification.pk}/read/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.read)

    def test_mark_all_read_when_none_unread(self):
        """read_all when no unread notifications returns marked_read=0."""
        Notification.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            title="Already read",
            read=True,
        )

        resp = self.client.post("/api/v1/notifications/read_all/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["marked_read"], 0)


class NotificationPreferenceViewTest(TestCase):
    """Tests for the NotificationPreference API endpoints."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123!"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_preferences(self):
        """GET /api/v1/notification-preferences/ returns user's preferences."""
        NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_IN_APP,
        )

        resp = self.client.get("/api/v1/notification-preferences/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)

    def test_create_preference(self):
        """POST /api/v1/notification-preferences/ creates a preference."""
        resp = self.client.post(
            "/api/v1/notification-preferences/",
            {
                "event_type": EVENT_DOCUMENT_ADDED,
                "channel": CHANNEL_EMAIL,
                "enabled": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            NotificationPreference.objects.filter(
                user=self.user,
                event_type=EVENT_DOCUMENT_ADDED,
                channel=CHANNEL_EMAIL,
            ).exists()
        )

    def test_update_preference(self):
        """PATCH /api/v1/notification-preferences/{id}/ updates enabled state."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_IN_APP,
            enabled=True,
        )

        resp = self.client.patch(
            f"/api/v1/notification-preferences/{pref.pk}/",
            {"enabled": False},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        pref.refresh_from_db()
        self.assertFalse(pref.enabled)

    def test_delete_preference(self):
        """DELETE /api/v1/notification-preferences/{id}/ removes the preference."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_IN_APP,
        )

        resp = self.client.delete(f"/api/v1/notification-preferences/{pref.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(NotificationPreference.objects.filter(pk=pref.pk).exists())

    def test_user_only_sees_own(self):
        """User A cannot see User B's preferences."""
        user_b = User.objects.create_user(
            username="userb", password="testpass123!"
        )
        NotificationPreference.objects.create(
            user=self.user,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_IN_APP,
        )
        NotificationPreference.objects.create(
            user=user_b,
            event_type=EVENT_DOCUMENT_ADDED,
            channel=CHANNEL_EMAIL,
        )

        # Authenticate as user_b
        client_b = APIClient()
        client_b.force_authenticate(user=user_b)
        resp = client_b.get("/api/v1/notification-preferences/")
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["channel"], CHANNEL_EMAIL)

    def test_create_preference_with_webhook_url(self):
        """Creating a webhook preference should store the URL."""
        resp = self.client.post(
            "/api/v1/notification-preferences/",
            {
                "event_type": EVENT_DOCUMENT_PROCESSED,
                "channel": CHANNEL_WEBHOOK,
                "enabled": True,
                "webhook_url": "https://hooks.example.com/notify",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        pref = NotificationPreference.objects.get(
            user=self.user,
            event_type=EVENT_DOCUMENT_PROCESSED,
            channel=CHANNEL_WEBHOOK,
        )
        self.assertEqual(pref.webhook_url, "https://hooks.example.com/notify")

    def test_preference_auto_assigns_user(self):
        """Created preference should automatically be assigned to the request user."""
        resp = self.client.post(
            "/api/v1/notification-preferences/",
            {
                "event_type": EVENT_PROCESSING_FAILED,
                "channel": CHANNEL_IN_APP,
                "enabled": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        pref = NotificationPreference.objects.get(
            event_type=EVENT_PROCESSING_FAILED,
            channel=CHANNEL_IN_APP,
        )
        self.assertEqual(pref.user, self.user)


class QuotaViewTest(TestCase):
    """Tests for the Quota admin API endpoints."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123!"
        )
        self.regular = User.objects.create_user(
            username="regular", email="reg@example.com", password="regpass123!"
        )
        self.client = APIClient()

    def test_list_quotas_admin(self):
        """Admin can list all quotas."""
        Quota.objects.create(max_documents=1000)
        self.client.force_authenticate(user=self.admin)

        resp = self.client.get("/api/v1/quotas/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)

    def test_list_quotas_non_admin(self):
        """Non-admin users should get 403 on quota list."""
        self.client.force_authenticate(user=self.regular)

        resp = self.client.get("/api/v1/quotas/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_quota(self):
        """Admin can create a new quota."""
        self.client.force_authenticate(user=self.admin)

        resp = self.client.post(
            "/api/v1/quotas/",
            {
                "user": self.regular.pk,
                "max_documents": 50,
                "max_storage_bytes": 1_073_741_824,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Quota.objects.filter(user=self.regular, max_documents=50).exists()
        )

    def test_create_quota_non_admin_forbidden(self):
        """Non-admin users should not be able to create quotas."""
        self.client.force_authenticate(user=self.regular)

        resp = self.client.post(
            "/api/v1/quotas/",
            {
                "max_documents": 999,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_quota_admin(self):
        """Admin can update an existing quota."""
        quota = Quota.objects.create(user=self.regular, max_documents=50)
        self.client.force_authenticate(user=self.admin)

        resp = self.client.patch(
            f"/api/v1/quotas/{quota.pk}/",
            {"max_documents": 75},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        quota.refresh_from_db()
        self.assertEqual(quota.max_documents, 75)

    def test_delete_quota_admin(self):
        """Admin can delete a quota."""
        quota = Quota.objects.create(user=self.regular, max_documents=50)
        self.client.force_authenticate(user=self.admin)

        resp = self.client.delete(f"/api/v1/quotas/{quota.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Quota.objects.filter(pk=quota.pk).exists())

    def test_quota_usage(self):
        """GET /api/v1/quotas/usage/ returns quota usage data."""
        Quota.objects.create(
            user=self.admin,
            max_documents=100,
            max_storage_bytes=10_485_760,
        )
        self.client.force_authenticate(user=self.admin)

        resp = self.client.get("/api/v1/quotas/usage/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("document_count", resp.data)
        self.assertIn("storage_bytes", resp.data)
        self.assertIn("max_documents", resp.data)
        self.assertIn("max_storage_bytes", resp.data)
        self.assertIn("documents_remaining", resp.data)
        self.assertIn("storage_remaining", resp.data)

    def test_quota_usage_requires_auth(self):
        """Unauthenticated users should get 401 on quota usage."""
        unauth_client = APIClient()
        resp = unauth_client.get("/api/v1/quotas/usage/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_global_quota(self):
        """Admin can create a global quota (no user, no group)."""
        self.client.force_authenticate(user=self.admin)

        resp = self.client.post(
            "/api/v1/quotas/",
            {
                "max_documents": 5000,
                "max_storage_bytes": 53_687_091_200,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        quota = Quota.objects.get(max_documents=5000)
        self.assertIsNone(quota.user)
        self.assertIsNone(quota.group)


class QuotaUploadEnforcementTest(TestCase):
    """Tests for quota enforcement during document upload."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="uploader", password="testpass123!"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _make_upload_file(self, filename="test.txt", content=b"Hello, World!"):
        """Create a SimpleUploadedFile for testing uploads."""
        return SimpleUploadedFile(
            filename, content, content_type="text/plain"
        )

    @patch("processing.tasks.consume_document")
    def test_upload_within_quota(self, mock_consume):
        """Upload should be accepted when user is within quota."""
        Quota.objects.create(user=self.user, max_documents=10)
        mock_consume.delay.return_value = None

        file = self._make_upload_file()
        resp = self.client.post(
            "/api/v1/documents/upload/",
            {"document": file},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", resp.data)

    def test_upload_exceeds_quota(self):
        """Upload should return 429 when user is at or over quota."""
        Quota.objects.create(user=self.user, max_documents=2)
        # Create 2 documents to fill the quota
        Document.objects.create(
            title="Doc 1",
            owner=self.user,
            filename="existing_1.pdf",
        )
        Document.objects.create(
            title="Doc 2",
            owner=self.user,
            filename="existing_2.pdf",
        )

        file = self._make_upload_file()
        resp = self.client.post(
            "/api/v1/documents/upload/",
            {"document": file},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("error", resp.data)
        self.assertIn("Document limit reached", resp.data["error"])

    @patch("processing.tasks.consume_document")
    def test_upload_no_quota_allows(self, mock_consume):
        """Upload with no quota configured should be accepted."""
        mock_consume.delay.return_value = None

        file = self._make_upload_file()
        resp = self.client.post(
            "/api/v1/documents/upload/",
            {"document": file},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)

    def test_upload_requires_auth(self):
        """Unauthenticated upload should return 401."""
        unauth_client = APIClient()
        file = self._make_upload_file()
        resp = unauth_client.post(
            "/api/v1/documents/upload/",
            {"document": file},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_no_file_returns_400(self):
        """Upload without a file should return 400."""
        resp = self.client.post(
            "/api/v1/documents/upload/",
            {},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", resp.data)
