"""Tests for organization API views."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from documents.models import Document
from organization.models import Cabinet, Correspondent, StoragePath, Tag


class TagViewSetTest(TestCase):
    """Tests for the Tag API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="taguser", password="pass!")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_list_tags(self):
        Tag.objects.create(name="Finance", owner=self.user)
        Tag.objects.create(name="Legal", owner=self.user)
        resp = self.client.get("/api/v1/tags/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 2)

    def test_create_tag(self):
        resp = self.client.post("/api/v1/tags/", {
            "name": "New Tag",
            "color": "#ff0000",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "New Tag")
        self.assertEqual(resp.data["color"], "#ff0000")
        self.assertEqual(resp.data["owner"], self.user.id)

    def test_update_tag(self):
        tag = Tag.objects.create(name="Old Name", owner=self.user)
        resp = self.client.patch(f"/api/v1/tags/{tag.pk}/", {
            "name": "New Name",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "New Name")

    def test_delete_tag(self):
        tag = Tag.objects.create(name="Delete Me", owner=self.user)
        resp = self.client.delete(f"/api/v1/tags/{tag.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(pk=tag.pk).exists())

    def test_tag_tree(self):
        parent = Tag.objects.create(name="Parent", owner=self.user)
        Tag.objects.create(name="Child", parent=parent, owner=self.user)
        resp = self.client.get("/api/v1/tags/tree/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(len(resp.data[0]["children"]), 1)

    def test_tag_autocomplete(self):
        Tag.objects.create(name="Invoice", owner=self.user)
        Tag.objects.create(name="Inventory", owner=self.user)
        Tag.objects.create(name="Contract", owner=self.user)
        resp = self.client.get("/api/v1/tags/autocomplete/?q=inv")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_tag_document_count(self):
        tag = Tag.objects.create(name="Counted", owner=self.user)
        doc = Document.objects.create(title="Test", owner=self.user, filename="o/1.txt")
        doc.tags.add(tag)
        resp = self.client.get(f"/api/v1/tags/{tag.pk}/")
        self.assertEqual(resp.data["document_count"], 1)


class CorrespondentViewSetTest(TestCase):
    """Tests for the Correspondent API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="corruser", password="pass!")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_list_correspondents(self):
        Correspondent.objects.create(name="ACME", owner=self.user)
        resp = self.client.get("/api/v1/correspondents/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_create_correspondent(self):
        resp = self.client.post("/api/v1/correspondents/", {
            "name": "New Corp",
            "match": "new corp",
            "matching_algorithm": 3,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "New Corp")

    def test_delete_correspondent(self):
        corr = Correspondent.objects.create(name="Del", owner=self.user)
        resp = self.client.delete(f"/api/v1/correspondents/{corr.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_autocomplete_correspondent(self):
        Correspondent.objects.create(name="Alpha Corp", owner=self.user)
        Correspondent.objects.create(name="Beta Corp", owner=self.user)
        resp = self.client.get("/api/v1/correspondents/autocomplete/?q=alph")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)


class CabinetViewSetTest(TestCase):
    """Tests for the Cabinet API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="cabuser", password="pass!")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_list_cabinets(self):
        Cabinet.objects.create(name="Archive", owner=self.user)
        resp = self.client.get("/api/v1/cabinets/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_create_cabinet(self):
        resp = self.client.post("/api/v1/cabinets/", {"name": "New Cabinet"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_cabinet_tree(self):
        root = Cabinet.objects.create(name="Root", owner=self.user)
        Cabinet.objects.create(name="Sub", parent=root, owner=self.user)
        resp = self.client.get("/api/v1/cabinets/tree/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(len(resp.data[0]["children"]), 1)

    def test_delete_cabinet(self):
        cab = Cabinet.objects.create(name="Del", owner=self.user)
        resp = self.client.delete(f"/api/v1/cabinets/{cab.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


class StoragePathViewSetTest(TestCase):
    """Tests for the StoragePath API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="spuser", password="pass!")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_list_storage_paths(self):
        StoragePath.objects.create(
            name="By Year", path="{{ created_year }}", owner=self.user,
        )
        resp = self.client.get("/api/v1/storage-paths/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_create_storage_path(self):
        resp = self.client.post("/api/v1/storage-paths/", {
            "name": "Custom",
            "path": "{{ created_year }}/{{ title }}",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class BulkAssignTest(TestCase):
    """Tests for bulk assign operations."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="bulkuser", password="pass!")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.doc1 = Document.objects.create(
            title="Doc 1", owner=self.user, filename="o/bulk1.txt",
        )
        self.doc2 = Document.objects.create(
            title="Doc 2", owner=self.user, filename="o/bulk2.txt",
        )

    def test_bulk_add_tags(self):
        tag1 = Tag.objects.create(name="Finance", owner=self.user)
        tag2 = Tag.objects.create(name="Important", owner=self.user)

        resp = self.client.post("/api/v1/bulk-assign/", {
            "document_ids": [self.doc1.pk, self.doc2.pk],
            "tag_ids": [tag1.pk, tag2.pk],
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["updated"], 2)
        self.assertEqual(self.doc1.tags.count(), 2)
        self.assertEqual(self.doc2.tags.count(), 2)

    def test_bulk_remove_tags(self):
        tag = Tag.objects.create(name="Remove Me", owner=self.user)
        self.doc1.tags.add(tag)
        self.doc2.tags.add(tag)

        resp = self.client.post("/api/v1/bulk-assign/", {
            "document_ids": [self.doc1.pk, self.doc2.pk],
            "remove_tag_ids": [tag.pk],
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(self.doc1.tags.count(), 0)

    def test_bulk_set_correspondent(self):
        corr = Correspondent.objects.create(name="Corp", owner=self.user)
        resp = self.client.post("/api/v1/bulk-assign/", {
            "document_ids": [self.doc1.pk, self.doc2.pk],
            "correspondent_id": corr.pk,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.doc1.refresh_from_db()
        self.assertEqual(self.doc1.correspondent, corr)

    def test_bulk_set_cabinet(self):
        cab = Cabinet.objects.create(name="Archive", owner=self.user)
        resp = self.client.post("/api/v1/bulk-assign/", {
            "document_ids": [self.doc1.pk],
            "cabinet_id": cab.pk,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.doc1.refresh_from_db()
        self.assertEqual(self.doc1.cabinet, cab)

    def test_bulk_no_documents_returns_404(self):
        resp = self.client.post("/api/v1/bulk-assign/", {
            "document_ids": [99999],
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
