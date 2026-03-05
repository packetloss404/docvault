"""Tests for document API views."""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from documents.models import Document, DocumentType


class DocumentTypeViewSetTests(TestCase):
    """Tests for DocumentType API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123!"
        )
        self.regular = User.objects.create_user(
            username="regular", email="reg@example.com", password="regpass123!"
        )
        self.admin_token = Token.objects.create(user=self.admin)
        self.regular_token = Token.objects.create(user=self.regular)

    def test_list_document_types(self):
        DocumentType.objects.create(name="Invoice")
        DocumentType.objects.create(name="Contract")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.regular_token.key}")
        resp = self.client.get("/api/v1/document-types/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 2)

    def test_create_document_type_as_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        resp = self.client.post("/api/v1/document-types/", {
            "name": "Invoice",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(DocumentType.objects.filter(name="Invoice").exists())
        dt = DocumentType.objects.get(name="Invoice")
        self.assertEqual(dt.slug, "invoice")

    def test_create_document_type_as_regular_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.regular_token.key}")
        resp = self.client.post("/api/v1/document-types/", {
            "name": "Invoice",
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_document_type_as_admin(self):
        dt = DocumentType.objects.create(name="Invoice")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        resp = self.client.patch(f"/api/v1/document-types/{dt.pk}/", {
            "name": "Updated Invoice",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        dt.refresh_from_db()
        self.assertEqual(dt.name, "Updated Invoice")

    def test_delete_document_type_as_admin(self):
        dt = DocumentType.objects.create(name="Invoice")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        resp = self.client.delete(f"/api/v1/document-types/{dt.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DocumentType.objects.filter(pk=dt.pk).exists())

    def test_document_type_has_document_count(self):
        dt = DocumentType.objects.create(name="Invoice")
        user = User.objects.create_user("owner", password="testpass123!")
        Document.objects.create(title="Doc 1", document_type=dt, owner=user)
        Document.objects.create(title="Doc 2", document_type=dt, owner=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        resp = self.client.get(f"/api/v1/document-types/{dt.pk}/")
        self.assertEqual(resp.data["document_count"], 2)

    def test_document_type_search(self):
        DocumentType.objects.create(name="Invoice")
        DocumentType.objects.create(name="Contract")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.regular_token.key}")
        resp = self.client.get("/api/v1/document-types/", {"search": "Inv"})
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Invoice")

    def test_unauthenticated_access_denied(self):
        resp = self.client.get("/api/v1/document-types/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class DocumentViewSetTests(TestCase):
    """Tests for Document API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123!"
        )
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="userpass123!"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="userpass123!"
        )
        self.admin_token = Token.objects.create(user=self.admin)
        self.user1_token = Token.objects.create(user=self.user1)
        self.user2_token = Token.objects.create(user=self.user2)
        self.doc_type = DocumentType.objects.create(name="Invoice")

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_create_document(self):
        self._auth(self.user1_token)
        resp = self.client.post("/api/v1/documents/", {
            "title": "Test Invoice",
            "document_type": self.doc_type.pk,
            "language": "en",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        doc = Document.objects.get(title="Test Invoice")
        self.assertEqual(doc.owner, self.user1)
        self.assertEqual(doc.created_by, self.user1)
        self.assertIsNotNone(doc.uuid)

    def test_list_documents_only_own(self):
        """Regular users should only see their own documents."""
        Document.objects.create(title="User1 Doc", owner=self.user1)
        Document.objects.create(title="User2 Doc", owner=self.user2)
        self._auth(self.user1_token)
        resp = self.client.get("/api/v1/documents/")
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "User1 Doc")

    def test_list_documents_admin_sees_all(self):
        """Admin (superuser) should see all documents."""
        Document.objects.create(title="User1 Doc", owner=self.user1)
        Document.objects.create(title="User2 Doc", owner=self.user2)
        self._auth(self.admin_token)
        resp = self.client.get("/api/v1/documents/")
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 2)

    def test_retrieve_own_document(self):
        doc = Document.objects.create(title="My Doc", owner=self.user1)
        self._auth(self.user1_token)
        resp = self.client.get(f"/api/v1/documents/{doc.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["title"], "My Doc")

    def test_update_own_document(self):
        doc = Document.objects.create(title="My Doc", owner=self.user1)
        self._auth(self.user1_token)
        resp = self.client.patch(f"/api/v1/documents/{doc.pk}/", {
            "title": "Updated Doc",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertEqual(doc.title, "Updated Doc")

    def test_delete_document_soft_deletes(self):
        """DELETE should soft-delete, not hard-delete."""
        doc = Document.objects.create(title="Deletable", owner=self.user1)
        self._auth(self.user1_token)
        resp = self.client.delete(f"/api/v1/documents/{doc.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        # Should not appear in normal queryset
        self.assertFalse(Document.objects.filter(pk=doc.pk).exists())
        # Should still exist in all_objects
        self.assertTrue(Document.all_objects.filter(pk=doc.pk).exists())

    def test_restore_soft_deleted_document(self):
        doc = Document.objects.create(title="Restorable", owner=self.user1)
        doc.soft_delete()
        self._auth(self.user1_token)
        resp = self.client.post(f"/api/v1/documents/{doc.pk}/restore/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["title"], "Restorable")
        doc.refresh_from_db()
        self.assertFalse(doc.is_deleted)

    def test_deleted_documents_list(self):
        """The /deleted/ endpoint should list soft-deleted docs for the user."""
        doc1 = Document.objects.create(title="Deleted1", owner=self.user1)
        doc1.soft_delete()
        Document.objects.create(title="Active1", owner=self.user1)
        doc3 = Document.objects.create(title="Deleted2", owner=self.user2)
        doc3.soft_delete()
        self._auth(self.user1_token)
        resp = self.client.get("/api/v1/documents/deleted/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Deleted1")

    def test_filter_by_document_type(self):
        dt2 = DocumentType.objects.create(name="Contract")
        Document.objects.create(title="Inv1", document_type=self.doc_type, owner=self.user1)
        Document.objects.create(title="Con1", document_type=dt2, owner=self.user1)
        self._auth(self.user1_token)
        resp = self.client.get("/api/v1/documents/", {"document_type": self.doc_type.pk})
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Inv1")

    def test_filter_by_date_range(self):
        Document.objects.create(
            title="Old Doc", owner=self.user1, created=date(2020, 1, 1),
        )
        Document.objects.create(
            title="New Doc", owner=self.user1, created=date(2025, 6, 15),
        )
        self._auth(self.user1_token)
        resp = self.client.get("/api/v1/documents/", {
            "created_after": "2025-01-01",
            "created_before": "2025-12-31",
        })
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "New Doc")

    def test_filter_has_asn(self):
        Document.objects.create(
            title="With ASN", owner=self.user1, archive_serial_number=42,
        )
        Document.objects.create(title="No ASN", owner=self.user1)
        self._auth(self.user1_token)
        resp = self.client.get("/api/v1/documents/", {"has_asn": "true"})
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "With ASN")

    def test_search_documents(self):
        Document.objects.create(title="Annual Budget Report", owner=self.user1)
        Document.objects.create(title="Meeting Notes", owner=self.user1)
        self._auth(self.user1_token)
        resp = self.client.get("/api/v1/documents/", {"search": "budget"})
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Annual Budget Report")

    def test_ordering(self):
        Document.objects.create(
            title="B Doc", owner=self.user1, created=date(2025, 2, 1),
        )
        Document.objects.create(
            title="A Doc", owner=self.user1, created=date(2025, 1, 1),
        )
        self._auth(self.user1_token)
        resp = self.client.get("/api/v1/documents/", {"ordering": "title"})
        results = resp.data.get("results", resp.data)
        self.assertEqual(results[0]["title"], "A Doc")
        self.assertEqual(results[1]["title"], "B Doc")

    def test_pagination(self):
        for i in range(30):
            Document.objects.create(title=f"Doc {i}", owner=self.user1)
        self._auth(self.user1_token)
        resp = self.client.get("/api/v1/documents/")
        self.assertEqual(resp.data["count"], 30)
        self.assertEqual(len(resp.data["results"]), 25)  # Default page size
        self.assertIsNotNone(resp.data["next"])

    def test_pagination_custom_page_size(self):
        for i in range(10):
            Document.objects.create(title=f"Doc {i}", owner=self.user1)
        self._auth(self.user1_token)
        resp = self.client.get("/api/v1/documents/", {"page_size": 5})
        self.assertEqual(len(resp.data["results"]), 5)

    def test_unauthenticated_access_denied(self):
        resp = self.client.get("/api/v1/documents/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_access_other_users_document(self):
        """User2 should not be able to retrieve user1's document."""
        doc = Document.objects.create(title="Private", owner=self.user1)
        self._auth(self.user2_token)
        resp = self.client.get(f"/api/v1/documents/{doc.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_language(self):
        Document.objects.create(title="English Doc", owner=self.user1, language="en")
        Document.objects.create(title="German Doc", owner=self.user1, language="de")
        self._auth(self.user1_token)
        resp = self.client.get("/api/v1/documents/", {"language": "de"})
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "German Doc")

    def test_filter_by_mime_type(self):
        Document.objects.create(
            title="PDF Doc", owner=self.user1, mime_type="application/pdf",
        )
        Document.objects.create(
            title="Image Doc", owner=self.user1, mime_type="image/png",
        )
        self._auth(self.user1_token)
        resp = self.client.get("/api/v1/documents/", {"mime_type": "application/pdf"})
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "PDF Doc")


class OpenAPISchemaTests(TestCase):
    """Tests for OpenAPI schema and Swagger UI endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123!"
        )
        self.token = Token.objects.create(user=self.user)

    def test_schema_endpoint(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        resp = self.client.get("/api/schema/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_swagger_ui_endpoint(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        resp = self.client.get("/api/docs/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
