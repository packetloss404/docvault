"""Tests for barcode and ASN API views."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from documents.models import Document


class NextAsnViewTest(TestCase):
    """Tests for the NextAsnView API endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass123!"
        )
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="pass123!"
        )
        self.token = Token.objects.create(user=self.user)
        self.admin_token = Token.objects.create(user=self.admin)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_next_asn_empty(self):
        """Should return next_asn=1 when no documents exist."""
        self._auth(self.token)
        resp = self.client.get("/api/v1/asn/next/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["next_asn"], 1)

    def test_next_asn_after_existing(self):
        """Should return max ASN + 1."""
        Document.objects.create(
            title="Doc",
            filename="doc.pdf",
            archive_serial_number=10,
            owner=self.user,
        )
        self._auth(self.token)
        resp = self.client.get("/api/v1/asn/next/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["next_asn"], 11)

    def test_next_asn_requires_auth(self):
        """Unauthenticated request should return 401."""
        resp = self.client.get("/api/v1/asn/next/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_next_asn_multiple_docs(self):
        """Should return max ASN + 1 across multiple documents."""
        Document.objects.create(
            title="Doc A",
            filename="doca.pdf",
            archive_serial_number=5,
            owner=self.user,
        )
        Document.objects.create(
            title="Doc B",
            filename="docb.pdf",
            archive_serial_number=10,
            owner=self.user,
        )
        Document.objects.create(
            title="Doc C",
            filename="docc.pdf",
            archive_serial_number=3,
            owner=self.user,
        )
        self._auth(self.token)
        resp = self.client.get("/api/v1/asn/next/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["next_asn"], 11)


class BulkAsnAssignViewTest(TestCase):
    """Tests for the BulkAsnAssignView API endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="regular", email="regular@example.com", password="pass123!"
        )
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="pass123!"
        )
        self.user_token = Token.objects.create(user=self.user)
        self.admin_token = Token.objects.create(user=self.admin)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_bulk_assign(self):
        """Should assign sequential ASNs to documents without one."""
        doc1 = Document.objects.create(
            title="Doc 1", filename="d1.pdf", owner=self.admin,
        )
        doc2 = Document.objects.create(
            title="Doc 2", filename="d2.pdf", owner=self.admin,
        )
        doc3 = Document.objects.create(
            title="Doc 3", filename="d3.pdf", owner=self.admin,
        )

        self._auth(self.admin_token)
        resp = self.client.post(
            "/api/v1/asn/bulk-assign/",
            {"document_ids": [doc1.pk, doc2.pk, doc3.pk]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 3)

        # Verify sequential assignment starting from 1
        doc1.refresh_from_db()
        doc2.refresh_from_db()
        doc3.refresh_from_db()
        self.assertEqual(doc1.archive_serial_number, 1)
        self.assertEqual(doc2.archive_serial_number, 2)
        self.assertEqual(doc3.archive_serial_number, 3)

    def test_bulk_assign_skips_existing(self):
        """Should skip documents that already have an ASN."""
        doc_with_asn = Document.objects.create(
            title="Has ASN",
            filename="has_asn.pdf",
            archive_serial_number=5,
            owner=self.admin,
        )
        doc_without_asn = Document.objects.create(
            title="No ASN",
            filename="no_asn.pdf",
            owner=self.admin,
        )

        self._auth(self.admin_token)
        resp = self.client.post(
            "/api/v1/asn/bulk-assign/",
            {"document_ids": [doc_with_asn.pk, doc_without_asn.pk]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Only 1 should be assigned (the one without ASN)
        self.assertEqual(resp.data["count"], 1)

        # The existing ASN should be unchanged
        doc_with_asn.refresh_from_db()
        self.assertEqual(doc_with_asn.archive_serial_number, 5)

        # The new assignment should start from max(5) + 1 = 6
        doc_without_asn.refresh_from_db()
        self.assertEqual(doc_without_asn.archive_serial_number, 6)

    def test_bulk_assign_empty_list(self):
        """Should return error for empty document_ids."""
        self._auth(self.admin_token)
        resp = self.client.post(
            "/api/v1/asn/bulk-assign/",
            {"document_ids": []},
            format="json",
        )
        # The view treats empty list as an error (returns 400)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_assign_nonexistent_doc(self):
        """Should skip nonexistent document IDs gracefully."""
        doc = Document.objects.create(
            title="Real Doc", filename="real.pdf", owner=self.admin,
        )

        self._auth(self.admin_token)
        resp = self.client.post(
            "/api/v1/asn/bulk-assign/",
            {"document_ids": [doc.pk, 99999]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Only the real doc should be assigned
        self.assertEqual(resp.data["count"], 1)

        doc.refresh_from_db()
        self.assertIsNotNone(doc.archive_serial_number)

    def test_bulk_assign_requires_admin(self):
        """Regular (non-admin) user should get 403."""
        self._auth(self.user_token)
        resp = self.client.post(
            "/api/v1/asn/bulk-assign/",
            {"document_ids": [1]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_bulk_assign_requires_auth(self):
        """Unauthenticated request should return 401."""
        resp = self.client.post(
            "/api/v1/asn/bulk-assign/",
            {"document_ids": [1]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class BarcodeConfigViewTest(TestCase):
    """Tests for the BarcodeConfigView API endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="regular", email="regular@example.com", password="pass123!"
        )
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="pass123!"
        )
        self.user_token = Token.objects.create(user=self.user)
        self.admin_token = Token.objects.create(user=self.admin)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_get_config(self):
        """Should return barcode configuration values."""
        self._auth(self.admin_token)
        resp = self.client.get("/api/v1/barcode/config/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Verify expected keys are present
        self.assertIn("separator_barcode", resp.data)
        self.assertIn("asn_prefix", resp.data)
        self.assertIn("dpi", resp.data)
        self.assertIn("max_pages", resp.data)
        self.assertIn("tag_mapping", resp.data)
        self.assertIn("retain_separator_pages", resp.data)
        self.assertIn("enabled", resp.data)
        # Verify default values
        self.assertEqual(resp.data["separator_barcode"], "PATCH T")
        self.assertEqual(resp.data["asn_prefix"], "ASN")
        self.assertEqual(resp.data["dpi"], 300)
        self.assertTrue(resp.data["enabled"])

    def test_config_requires_admin(self):
        """Regular (non-admin) user should get 403."""
        self._auth(self.user_token)
        resp = self.client.get("/api/v1/barcode/config/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_config_requires_auth(self):
        """Unauthenticated request should return 401."""
        resp = self.client.get("/api/v1/barcode/config/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
