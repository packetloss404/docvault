"""Tests for processing API views."""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from processing.models import ProcessingTask


class ProcessingTaskViewSetTest(TestCase):
    """Tests for processing task API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username="user1", email="u1@example.com", password="pass123!"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="u2@example.com", password="pass123!"
        )
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="pass123!"
        )
        self.token1 = Token.objects.create(user=self.user1)
        self.token2 = Token.objects.create(user=self.user2)
        self.admin_token = Token.objects.create(user=self.admin)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_list_tasks_own_only(self):
        ProcessingTask.objects.create(task_name="t1", owner=self.user1)
        ProcessingTask.objects.create(task_name="t2", owner=self.user2)
        self._auth(self.token1)
        resp = self.client.get("/api/v1/tasks/")
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["task_name"], "t1")

    def test_list_tasks_admin_sees_all(self):
        ProcessingTask.objects.create(task_name="t1", owner=self.user1)
        ProcessingTask.objects.create(task_name="t2", owner=self.user2)
        self._auth(self.admin_token)
        resp = self.client.get("/api/v1/tasks/")
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 2)

    def test_retrieve_task(self):
        task = ProcessingTask.objects.create(
            task_name="detail_test", owner=self.user1,
            status=ProcessingTask.Status.SUCCESS,
            progress=1.0,
        )
        self._auth(self.token1)
        resp = self.client.get(f"/api/v1/tasks/{task.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["task_name"], "detail_test")
        self.assertEqual(resp.data["status"], "success")

    def test_acknowledge_task(self):
        task = ProcessingTask.objects.create(task_name="ack", owner=self.user1)
        self._auth(self.token1)
        resp = self.client.post(f"/api/v1/tasks/{task.pk}/acknowledge/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["acknowledged"])
        task.refresh_from_db()
        self.assertTrue(task.acknowledged)

    def test_pending_tasks(self):
        ProcessingTask.objects.create(
            task_name="acked", owner=self.user1, acknowledged=True,
        )
        ProcessingTask.objects.create(
            task_name="unacked", owner=self.user1, acknowledged=False,
        )
        self._auth(self.token1)
        resp = self.client.get("/api/v1/tasks/pending/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # pending endpoint doesn't paginate by default (it's an action returning a list)
        data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["task_name"], "unacked")

    def test_cannot_access_other_users_task(self):
        task = ProcessingTask.objects.create(task_name="private", owner=self.user1)
        self._auth(self.token2)
        resp = self.client.get(f"/api/v1/tasks/{task.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_access_denied(self):
        resp = self.client.get("/api/v1/tasks/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read_only_viewset(self):
        """Tasks should not be creatable via API."""
        self._auth(self.token1)
        resp = self.client.post("/api/v1/tasks/", {"task_name": "hack"})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class DocumentUploadViewTest(TestCase):
    """Tests for the document upload endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="uploader", email="up@example.com", password="pass123!"
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_upload_no_file_returns_400(self):
        resp = self.client.post("/api/v1/documents/upload/", {}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", resp.data)

    def test_upload_creates_task(self):
        """Uploading a file should create a ProcessingTask and return 202."""
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile("test.txt", b"file contents", content_type="text/plain")
        resp = self.client.post(
            "/api/v1/documents/upload/",
            {"document": file},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", resp.data)
        self.assertEqual(resp.data["status"], "queued")

        # Verify task was created and processed (tasks run eagerly in tests)
        task = ProcessingTask.objects.get(task_id=resp.data["task_id"])
        self.assertEqual(task.owner, self.user)
        # In eager mode, the task completes synchronously
        self.assertEqual(task.status, ProcessingTask.Status.SUCCESS)

    def test_upload_unauthenticated(self):
        self.client.credentials()  # Clear auth
        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile("test.txt", b"data", content_type="text/plain")
        resp = self.client.post(
            "/api/v1/documents/upload/",
            {"document": file},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
