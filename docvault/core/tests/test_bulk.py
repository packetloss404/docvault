"""Tests for BulkOperationView."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from documents.models import Document, DocumentType
from organization.models import Correspondent, Tag


@pytest.fixture
def user(db):
    return User.objects.create_user("testuser", "test@example.com", "pass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def documents(user):
    """Create three test documents."""
    docs = []
    for i in range(3):
        doc = Document.objects.create(
            title=f"Doc {i}",
            filename=f"doc{i}.pdf",
            mime_type="application/pdf",
            owner=user,
        )
        docs.append(doc)
    return docs


class TestBulkOperationValidation:
    """Tests for request validation in the bulk endpoint."""

    @pytest.mark.django_db
    def test_missing_action_returns_400(self, auth_client, documents):
        response = auth_client.post(
            "/api/v1/bulk/",
            {"document_ids": [documents[0].pk]},
            format="json",
        )
        assert response.status_code == 400
        assert "error" in response.data

    @pytest.mark.django_db
    def test_missing_document_ids_returns_400(self, auth_client):
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "delete"},
            format="json",
        )
        assert response.status_code == 400
        assert "error" in response.data

    @pytest.mark.django_db
    def test_empty_document_ids_returns_400(self, auth_client):
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "delete", "document_ids": []},
            format="json",
        )
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_unknown_action_returns_400(self, auth_client, documents):
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "explode", "document_ids": [documents[0].pk]},
            format="json",
        )
        assert response.status_code == 400
        assert "Unknown action" in response.data["error"]

    @pytest.mark.django_db
    def test_no_matching_documents_returns_404(self, auth_client):
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "delete", "document_ids": [99999]},
            format="json",
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_unauthenticated_returns_401_or_403(self, documents):
        client = APIClient()
        response = client.post(
            "/api/v1/bulk/",
            {"action": "delete", "document_ids": [documents[0].pk]},
            format="json",
        )
        assert response.status_code in (401, 403)


class TestBulkDelete:
    """Tests for the bulk delete action."""

    @pytest.mark.django_db
    def test_bulk_delete_all(self, auth_client, documents):
        ids = [d.pk for d in documents]
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "delete", "document_ids": ids},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["action"] == "delete"
        assert response.data["affected"] == 3

    @pytest.mark.django_db
    def test_bulk_delete_soft_deletes(self, auth_client, documents):
        """Verify that bulk delete performs soft deletion."""
        ids = [d.pk for d in documents]
        auth_client.post(
            "/api/v1/bulk/",
            {"action": "delete", "document_ids": ids},
            format="json",
        )
        # Default manager should exclude soft-deleted documents
        assert Document.objects.filter(pk__in=ids).count() == 0
        # all_objects should still find them
        assert Document.all_objects.filter(pk__in=ids).count() == 3

    @pytest.mark.django_db
    def test_bulk_delete_subset(self, auth_client, documents):
        ids = [documents[0].pk, documents[1].pk]
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "delete", "document_ids": ids},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["affected"] == 2
        # Third document should still exist
        assert Document.objects.filter(pk=documents[2].pk).exists()


class TestBulkAddTags:
    """Tests for the bulk add_tags action."""

    @pytest.mark.django_db
    def test_bulk_add_single_tag(self, auth_client, documents):
        tag = Tag.objects.create(name="Important", color="#ff0000")
        ids = [d.pk for d in documents]
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "add_tags", "document_ids": ids, "tag_ids": [tag.pk]},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["action"] == "add_tags"
        assert response.data["affected"] == 3
        # Verify tags were actually added
        for doc in documents:
            doc.refresh_from_db()
            assert tag in doc.tags.all()

    @pytest.mark.django_db
    def test_bulk_add_multiple_tags(self, auth_client, documents):
        tag1 = Tag.objects.create(name="Urgent", color="#ff0000")
        tag2 = Tag.objects.create(name="Review", color="#00ff00")
        ids = [d.pk for d in documents]
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "add_tags", "document_ids": ids, "tag_ids": [tag1.pk, tag2.pk]},
            format="json",
        )
        assert response.status_code == 200
        for doc in documents:
            doc.refresh_from_db()
            assert set(doc.tags.values_list("pk", flat=True)) == {tag1.pk, tag2.pk}

    @pytest.mark.django_db
    def test_bulk_add_tags_missing_tag_ids_returns_400(self, auth_client, documents):
        ids = [d.pk for d in documents]
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "add_tags", "document_ids": ids},
            format="json",
        )
        assert response.status_code == 400
        assert "tag_ids" in response.data["error"]

    @pytest.mark.django_db
    def test_bulk_add_tags_empty_tag_ids_returns_400(self, auth_client, documents):
        ids = [d.pk for d in documents]
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "add_tags", "document_ids": ids, "tag_ids": []},
            format="json",
        )
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_bulk_add_tags_idempotent(self, auth_client, documents):
        """Adding the same tag twice should not create duplicates."""
        tag = Tag.objects.create(name="Important", color="#ff0000")
        ids = [d.pk for d in documents]
        auth_client.post(
            "/api/v1/bulk/",
            {"action": "add_tags", "document_ids": ids, "tag_ids": [tag.pk]},
            format="json",
        )
        # Add the same tag again
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "add_tags", "document_ids": ids, "tag_ids": [tag.pk]},
            format="json",
        )
        assert response.status_code == 200
        for doc in documents:
            doc.refresh_from_db()
            assert doc.tags.filter(pk=tag.pk).count() == 1


class TestBulkRemoveTags:
    """Tests for the bulk remove_tags action."""

    @pytest.mark.django_db
    def test_bulk_remove_tags(self, auth_client, documents):
        tag = Tag.objects.create(name="Remove-Me", color="#00ff00")
        for doc in documents:
            doc.tags.add(tag)
        ids = [d.pk for d in documents]
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "remove_tags", "document_ids": ids, "tag_ids": [tag.pk]},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["action"] == "remove_tags"
        assert response.data["affected"] == 3
        # Verify tags were actually removed
        for doc in documents:
            doc.refresh_from_db()
            assert tag not in doc.tags.all()

    @pytest.mark.django_db
    def test_bulk_remove_tags_leaves_other_tags(self, auth_client, documents):
        tag_keep = Tag.objects.create(name="Keep", color="#0000ff")
        tag_remove = Tag.objects.create(name="Remove", color="#ff0000")
        for doc in documents:
            doc.tags.add(tag_keep, tag_remove)
        ids = [d.pk for d in documents]
        auth_client.post(
            "/api/v1/bulk/",
            {"action": "remove_tags", "document_ids": ids, "tag_ids": [tag_remove.pk]},
            format="json",
        )
        for doc in documents:
            doc.refresh_from_db()
            assert tag_keep in doc.tags.all()
            assert tag_remove not in doc.tags.all()

    @pytest.mark.django_db
    def test_bulk_remove_tags_nonexistent_tag_is_no_op(self, auth_client, documents):
        """Removing a tag that was never added should succeed without error."""
        tag = Tag.objects.create(name="Never-Added", color="#aaaaaa")
        ids = [d.pk for d in documents]
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "remove_tags", "document_ids": ids, "tag_ids": [tag.pk]},
            format="json",
        )
        assert response.status_code == 200


class TestBulkSetCorrespondent:
    """Tests for the bulk set_correspondent action."""

    @pytest.mark.django_db
    def test_bulk_set_correspondent(self, auth_client, documents):
        corr = Correspondent.objects.create(name="ACME Corp")
        ids = [d.pk for d in documents]
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "set_correspondent", "document_ids": ids, "correspondent_id": corr.pk},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["action"] == "set_correspondent"
        assert response.data["affected"] == 3
        # Verify correspondent was actually set
        for doc in documents:
            doc.refresh_from_db()
            assert doc.correspondent_id == corr.pk

    @pytest.mark.django_db
    def test_bulk_set_correspondent_overwrites_existing(self, auth_client, documents):
        corr1 = Correspondent.objects.create(name="Old Corp")
        corr2 = Correspondent.objects.create(name="New Corp")
        for doc in documents:
            doc.correspondent = corr1
            doc.save()
        ids = [d.pk for d in documents]
        auth_client.post(
            "/api/v1/bulk/",
            {"action": "set_correspondent", "document_ids": ids, "correspondent_id": corr2.pk},
            format="json",
        )
        for doc in documents:
            doc.refresh_from_db()
            assert doc.correspondent_id == corr2.pk

    @pytest.mark.django_db
    def test_bulk_clear_correspondent(self, auth_client, documents):
        """Setting correspondent_id to None should clear the correspondent."""
        corr = Correspondent.objects.create(name="ACME Corp")
        for doc in documents:
            doc.correspondent = corr
            doc.save()
        ids = [d.pk for d in documents]
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "set_correspondent", "document_ids": ids, "correspondent_id": None},
            format="json",
        )
        assert response.status_code == 200
        for doc in documents:
            doc.refresh_from_db()
            assert doc.correspondent is None


class TestBulkSetDocumentType:
    """Tests for the bulk set_document_type action."""

    @pytest.mark.django_db
    def test_bulk_set_document_type(self, auth_client, documents):
        dt = DocumentType.objects.create(name="Invoice")
        ids = [d.pk for d in documents]
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "set_document_type", "document_ids": ids, "document_type_id": dt.pk},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["action"] == "set_document_type"
        assert response.data["affected"] == 3
        # Verify document_type was actually set
        for doc in documents:
            doc.refresh_from_db()
            assert doc.document_type_id == dt.pk

    @pytest.mark.django_db
    def test_bulk_set_document_type_overwrites_existing(self, auth_client, documents):
        dt1 = DocumentType.objects.create(name="Invoice")
        dt2 = DocumentType.objects.create(name="Contract")
        for doc in documents:
            doc.document_type = dt1
            doc.save()
        ids = [d.pk for d in documents]
        auth_client.post(
            "/api/v1/bulk/",
            {"action": "set_document_type", "document_ids": ids, "document_type_id": dt2.pk},
            format="json",
        )
        for doc in documents:
            doc.refresh_from_db()
            assert doc.document_type_id == dt2.pk

    @pytest.mark.django_db
    def test_bulk_clear_document_type(self, auth_client, documents):
        """Setting document_type_id to None should clear the document type."""
        dt = DocumentType.objects.create(name="Invoice")
        for doc in documents:
            doc.document_type = dt
            doc.save()
        ids = [d.pk for d in documents]
        response = auth_client.post(
            "/api/v1/bulk/",
            {"action": "set_document_type", "document_ids": ids, "document_type_id": None},
            format="json",
        )
        assert response.status_code == 200
        for doc in documents:
            doc.refresh_from_db()
            assert doc.document_type is None
