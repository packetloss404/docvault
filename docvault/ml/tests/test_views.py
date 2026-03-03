"""Tests for ML API views."""

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from documents.models import Document


class SuggestionsViewTest(TestCase):
    """Tests for the DocumentSuggestionsView at /api/v1/documents/{id}/suggestions/."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            "admin", "admin@test.com", "adminpass123"
        )
        self.regular_user = User.objects.create_user(
            "regular", password="userpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.superuser)

        self.document = Document.objects.create(
            title="Test Invoice",
            content="invoice payment billing total amount due",
            filename="test_suggestions.pdf",
            owner=self.superuser,
        )

    @patch("ml.views.get_suggestions_for_document")
    def test_get_suggestions(self, mock_get_suggestions):
        """GET returns suggestions for the given document."""
        mock_get_suggestions.return_value = {
            "tags": [{"id": 1, "confidence": 0.9}],
            "correspondent": [{"id": 2, "confidence": 0.8}],
            "document_type": [{"id": 3, "confidence": 0.95}],
            "storage_path": [{"id": 4, "confidence": 0.7}],
        }

        url = f"/api/v1/documents/{self.document.pk}/suggestions/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("tags", data)
        self.assertIn("correspondent", data)
        self.assertIn("document_type", data)
        self.assertIn("storage_path", data)

    def test_suggestions_not_found(self):
        """GET with nonexistent document ID returns 404."""
        url = "/api/v1/documents/99999/suggestions/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_suggestions_require_auth(self):
        """Unauthenticated requests return 401."""
        unauthenticated_client = APIClient()
        url = f"/api/v1/documents/{self.document.pk}/suggestions/"
        response = unauthenticated_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("ml.views.get_suggestions_for_document")
    def test_suggestions_empty_when_no_classifier(self, mock_get_suggestions):
        """When no classifier is available, empty suggestions are returned."""
        mock_get_suggestions.return_value = {
            "tags": [],
            "correspondent": [],
            "document_type": [],
            "storage_path": [],
        }

        url = f"/api/v1/documents/{self.document.pk}/suggestions/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["tags"], [])
        self.assertEqual(data["correspondent"], [])
        self.assertEqual(data["document_type"], [])
        self.assertEqual(data["storage_path"], [])


class ClassifierStatusViewTest(TestCase):
    """Tests for the ClassifierStatusView at /api/v1/classifier/status/."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            "statusadmin", "statusadmin@test.com", "adminpass123"
        )
        self.regular_user = User.objects.create_user(
            "statususer", password="userpass123"
        )
        self.url = "/api/v1/classifier/status/"

    @patch("ml.views.get_classifier")
    def test_status_no_classifier(self, mock_get_classifier):
        """GET returns available=False when no classifier is loaded."""
        mock_get_classifier.return_value = None

        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["available"])
        self.assertFalse(data["tags_trained"])
        self.assertFalse(data["correspondent_trained"])
        self.assertFalse(data["document_type_trained"])
        self.assertFalse(data["storage_path_trained"])

    @patch("ml.views.get_classifier")
    def test_status_with_classifier(self, mock_get_classifier):
        """GET returns detailed status when a classifier is available."""
        mock_classifier = MagicMock()
        mock_classifier.format_version = 1
        mock_classifier.tags_classifier = MagicMock()
        mock_classifier.correspondent_classifier = None
        mock_classifier.document_type_classifier = MagicMock()
        mock_classifier.storage_path_classifier = None
        mock_classifier.tags_data_hash = "abc123"
        mock_classifier.correspondent_data_hash = ""
        mock_classifier.document_type_data_hash = "def456"
        mock_classifier.storage_path_data_hash = ""
        mock_get_classifier.return_value = mock_classifier

        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["available"])
        self.assertTrue(data["tags_trained"])
        self.assertFalse(data["correspondent_trained"])
        self.assertTrue(data["document_type_trained"])
        self.assertFalse(data["storage_path_trained"])

    def test_status_admin_only(self):
        """Non-admin users get 403."""
        client = APIClient()
        client.force_authenticate(user=self.regular_user)
        response = client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_status_require_auth(self):
        """Unauthenticated requests return 401."""
        client = APIClient()
        response = client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ClassifierTrainViewTest(TestCase):
    """Tests for the ClassifierTrainView at /api/v1/classifier/train/."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            "trainadmin", "trainadmin@test.com", "adminpass123"
        )
        self.regular_user = User.objects.create_user(
            "trainuser", password="userpass123"
        )
        self.url = "/api/v1/classifier/train/"

    @patch("ml.tasks.train_classifier")
    def test_trigger_training(self, mock_train_task):
        """POST triggers classifier training and returns 202."""
        mock_train_task.delay.return_value = MagicMock()

        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.post(self.url, format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        data = response.json()
        self.assertEqual(data["status"], "training_queued")
        mock_train_task.delay.assert_called_once()

    def test_train_admin_only(self):
        """Non-admin users get 403."""
        client = APIClient()
        client.force_authenticate(user=self.regular_user)
        response = client.post(self.url, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_train_require_auth(self):
        """Unauthenticated requests return 401."""
        client = APIClient()
        response = client.post(self.url, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("ml.tasks.train_classifier")
    def test_train_get_method_not_allowed(self, mock_train_task):
        """GET method is not allowed on the train endpoint."""
        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
