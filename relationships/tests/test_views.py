"""Tests for the relationships app API views."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from documents.models import Document
from relationships.constants import BUILTIN_TYPES
from relationships.models import DocumentRelationship, RelationshipType

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin", password="adminpass123", email="admin@test.com"
    )


@pytest.fixture
def doc_a(user):
    return Document.objects.create(title="Document A", owner=user, created_by=user)


@pytest.fixture
def doc_b(user):
    return Document.objects.create(title="Document B", owner=user, created_by=user)


@pytest.fixture
def doc_c(user):
    return Document.objects.create(title="Document C", owner=user, created_by=user)


@pytest.fixture
def custom_type(db):
    return RelationshipType.objects.create(
        slug="custom-type",
        label="Custom Type",
        icon="bi-custom",
        is_directional=True,
        is_builtin=False,
    )


@pytest.fixture
def builtin_type(db):
    return RelationshipType.objects.create(
        slug="builtin-type",
        label="Built-in Type",
        icon="bi-builtin",
        is_directional=True,
        is_builtin=True,
    )


@pytest.fixture
def seeded_types(db):
    RelationshipType.seed_defaults()
    return list(RelationshipType.objects.all())


# ---------------------------------------------------------------------------
# Relationship Types - List / Create
# ---------------------------------------------------------------------------


class TestRelationshipTypeListCreate:
    """Tests for GET/POST /api/v1/relationship-types/"""

    URL = "/api/v1/relationship-types/"

    @pytest.mark.django_db
    def test_list_types_authenticated(self, client, user, custom_type, builtin_type):
        client.force_authenticate(user=user)
        response = client.get(self.URL)
        assert response.status_code == 200
        slugs = [t["slug"] for t in response.data]
        assert "custom-type" in slugs
        assert "builtin-type" in slugs

    @pytest.mark.django_db
    def test_list_types_unauthenticated(self, client):
        response = client.get(self.URL)
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_create_type_as_admin(self, client, admin_user):
        client.force_authenticate(user=admin_user)
        data = {
            "slug": "new-type",
            "label": "New Type",
            "icon": "bi-new",
            "is_directional": False,
            "description": "A new type",
        }
        response = client.post(self.URL, data, format="json")
        assert response.status_code == 201
        assert response.data["slug"] == "new-type"
        assert response.data["label"] == "New Type"
        assert response.data["is_builtin"] is False

    @pytest.mark.django_db
    def test_create_type_as_nonadmin_forbidden(self, client, user):
        client.force_authenticate(user=user)
        data = {"slug": "new-type", "label": "New Type"}
        response = client.post(self.URL, data, format="json")
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_create_type_unauthenticated(self, client):
        data = {"slug": "new-type", "label": "New Type"}
        response = client.post(self.URL, data, format="json")
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_create_type_is_always_non_builtin(self, client, admin_user):
        """Even if the request tries to set is_builtin=True, it should be False."""
        client.force_authenticate(user=admin_user)
        data = {
            "slug": "sneaky-type",
            "label": "Sneaky Type",
            "is_builtin": True,
        }
        response = client.post(self.URL, data, format="json")
        assert response.status_code == 201
        assert response.data["is_builtin"] is False


# ---------------------------------------------------------------------------
# Relationship Types - Detail / Update / Delete
# ---------------------------------------------------------------------------


class TestRelationshipTypeDetail:
    """Tests for GET/PATCH/DELETE /api/v1/relationship-types/<pk>/"""

    @pytest.mark.django_db
    def test_get_detail(self, client, user, custom_type):
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/relationship-types/{custom_type.pk}/")
        assert response.status_code == 200
        assert response.data["slug"] == "custom-type"

    @pytest.mark.django_db
    def test_get_detail_not_found(self, client, user):
        client.force_authenticate(user=user)
        response = client.get("/api/v1/relationship-types/99999/")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_update_type_as_admin(self, client, admin_user, custom_type):
        client.force_authenticate(user=admin_user)
        data = {"label": "Updated Label"}
        response = client.patch(
            f"/api/v1/relationship-types/{custom_type.pk}/",
            data,
            format="json",
        )
        assert response.status_code == 200
        assert response.data["label"] == "Updated Label"

    @pytest.mark.django_db
    def test_update_type_as_nonadmin_forbidden(self, client, user, custom_type):
        client.force_authenticate(user=user)
        data = {"label": "Hacked Label"}
        response = client.patch(
            f"/api/v1/relationship-types/{custom_type.pk}/",
            data,
            format="json",
        )
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_delete_custom_type_as_admin(self, client, admin_user, custom_type):
        client.force_authenticate(user=admin_user)
        response = client.delete(
            f"/api/v1/relationship-types/{custom_type.pk}/"
        )
        assert response.status_code == 204
        assert not RelationshipType.objects.filter(pk=custom_type.pk).exists()

    @pytest.mark.django_db
    def test_delete_builtin_type_returns_400(self, client, admin_user, builtin_type):
        client.force_authenticate(user=admin_user)
        response = client.delete(
            f"/api/v1/relationship-types/{builtin_type.pk}/"
        )
        assert response.status_code == 400
        assert "Built-in" in response.data["error"]
        assert RelationshipType.objects.filter(pk=builtin_type.pk).exists()

    @pytest.mark.django_db
    def test_delete_type_as_nonadmin_forbidden(self, client, user, custom_type):
        client.force_authenticate(user=user)
        response = client.delete(
            f"/api/v1/relationship-types/{custom_type.pk}/"
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Document Relationships - List / Create
# ---------------------------------------------------------------------------


class TestDocumentRelationshipListCreate:
    """Tests for GET/POST /api/v1/documents/<id>/relationships/"""

    @pytest.mark.django_db
    def test_list_relationships_both_directions(
        self, client, user, doc_a, doc_b, doc_c, custom_type
    ):
        """Listing relationships for a doc shows both incoming and outgoing."""
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=custom_type,
        )
        DocumentRelationship.objects.create(
            source_document=doc_c,
            target_document=doc_a,
            relationship_type=custom_type,
        )
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/documents/{doc_a.pk}/relationships/")
        assert response.status_code == 200
        assert len(response.data) == 2

    @pytest.mark.django_db
    def test_list_relationships_empty(self, client, user, doc_a):
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/documents/{doc_a.pk}/relationships/")
        assert response.status_code == 200
        assert len(response.data) == 0

    @pytest.mark.django_db
    def test_list_relationships_nonexistent_document(self, client, user):
        client.force_authenticate(user=user)
        response = client.get("/api/v1/documents/99999/relationships/")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_create_relationship(self, client, user, doc_a, doc_b, custom_type):
        client.force_authenticate(user=user)
        data = {
            "target_document": doc_b.pk,
            "relationship_type": custom_type.pk,
            "notes": "Test relationship",
        }
        response = client.post(
            f"/api/v1/documents/{doc_a.pk}/relationships/",
            data,
            format="json",
        )
        assert response.status_code == 201
        assert response.data["source_document"] == doc_a.pk
        assert response.data["target_document"] == doc_b.pk
        assert response.data["relationship_type"] == custom_type.pk
        assert response.data["notes"] == "Test relationship"

    @pytest.mark.django_db
    def test_create_relationship_includes_denormalized_fields(
        self, client, user, doc_a, doc_b, custom_type
    ):
        client.force_authenticate(user=user)
        data = {
            "target_document": doc_b.pk,
            "relationship_type": custom_type.pk,
        }
        response = client.post(
            f"/api/v1/documents/{doc_a.pk}/relationships/",
            data,
            format="json",
        )
        assert response.status_code == 201
        assert response.data["source_title"] == "Document A"
        assert response.data["target_title"] == "Document B"
        assert response.data["relationship_type_label"] == "Custom Type"
        assert response.data["relationship_type_icon"] == "bi-custom"

    @pytest.mark.django_db
    def test_create_self_referential_relationship_blocked(
        self, client, user, doc_a, custom_type
    ):
        client.force_authenticate(user=user)
        data = {
            "target_document": doc_a.pk,
            "relationship_type": custom_type.pk,
        }
        response = client.post(
            f"/api/v1/documents/{doc_a.pk}/relationships/",
            data,
            format="json",
        )
        assert response.status_code == 400
        assert "itself" in response.data["error"]

    @pytest.mark.django_db
    def test_create_duplicate_relationship_returns_409(
        self, client, user, doc_a, doc_b, custom_type
    ):
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=custom_type,
        )
        client.force_authenticate(user=user)
        data = {
            "target_document": doc_b.pk,
            "relationship_type": custom_type.pk,
        }
        response = client.post(
            f"/api/v1/documents/{doc_a.pk}/relationships/",
            data,
            format="json",
        )
        assert response.status_code == 409
        assert "already exists" in response.data["error"]

    @pytest.mark.django_db
    def test_create_relationship_target_not_found(
        self, client, user, doc_a, custom_type
    ):
        client.force_authenticate(user=user)
        data = {
            "target_document": 99999,
            "relationship_type": custom_type.pk,
        }
        response = client.post(
            f"/api/v1/documents/{doc_a.pk}/relationships/",
            data,
            format="json",
        )
        assert response.status_code == 400
        assert "Target document not found" in response.data["error"]

    @pytest.mark.django_db
    def test_create_relationship_type_not_found(self, client, user, doc_a, doc_b):
        client.force_authenticate(user=user)
        data = {
            "target_document": doc_b.pk,
            "relationship_type": 99999,
        }
        response = client.post(
            f"/api/v1/documents/{doc_a.pk}/relationships/",
            data,
            format="json",
        )
        assert response.status_code == 400
        assert "Relationship type not found" in response.data["error"]

    @pytest.mark.django_db
    def test_create_relationship_source_not_found(self, client, user, doc_b, custom_type):
        client.force_authenticate(user=user)
        data = {
            "target_document": doc_b.pk,
            "relationship_type": custom_type.pk,
        }
        response = client.post(
            "/api/v1/documents/99999/relationships/",
            data,
            format="json",
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_create_relationship_unauthenticated(self, client, doc_a, doc_b, custom_type):
        data = {
            "target_document": doc_b.pk,
            "relationship_type": custom_type.pk,
        }
        response = client.post(
            f"/api/v1/documents/{doc_a.pk}/relationships/",
            data,
            format="json",
        )
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_create_relationship_with_empty_notes(
        self, client, user, doc_a, doc_b, custom_type
    ):
        client.force_authenticate(user=user)
        data = {
            "target_document": doc_b.pk,
            "relationship_type": custom_type.pk,
        }
        response = client.post(
            f"/api/v1/documents/{doc_a.pk}/relationships/",
            data,
            format="json",
        )
        assert response.status_code == 201
        assert response.data["notes"] == ""


# ---------------------------------------------------------------------------
# Document Relationships - Delete
# ---------------------------------------------------------------------------


class TestDocumentRelationshipDelete:
    """Tests for DELETE /api/v1/documents/<id>/relationships/<pk>/"""

    @pytest.mark.django_db
    def test_delete_relationship_from_source_side(
        self, client, user, doc_a, doc_b, custom_type
    ):
        rel = DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=custom_type,
        )
        client.force_authenticate(user=user)
        response = client.delete(
            f"/api/v1/documents/{doc_a.pk}/relationships/{rel.pk}/"
        )
        assert response.status_code == 204
        assert not DocumentRelationship.objects.filter(pk=rel.pk).exists()

    @pytest.mark.django_db
    def test_delete_relationship_from_target_side(
        self, client, user, doc_a, doc_b, custom_type
    ):
        rel = DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=custom_type,
        )
        client.force_authenticate(user=user)
        response = client.delete(
            f"/api/v1/documents/{doc_b.pk}/relationships/{rel.pk}/"
        )
        assert response.status_code == 204
        assert not DocumentRelationship.objects.filter(pk=rel.pk).exists()

    @pytest.mark.django_db
    def test_delete_relationship_not_found(self, client, user, doc_a):
        client.force_authenticate(user=user)
        response = client.delete(
            f"/api/v1/documents/{doc_a.pk}/relationships/99999/"
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_delete_relationship_unauthenticated(
        self, client, doc_a, doc_b, custom_type
    ):
        rel = DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=custom_type,
        )
        response = client.delete(
            f"/api/v1/documents/{doc_a.pk}/relationships/{rel.pk}/"
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Relationship Graph
# ---------------------------------------------------------------------------


class TestDocumentRelationshipGraph:
    """Tests for GET /api/v1/documents/<id>/relationship-graph/"""

    @pytest.mark.django_db
    def test_graph_returns_nodes_and_edges(
        self, client, user, doc_a, doc_b, custom_type
    ):
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=custom_type,
        )
        client.force_authenticate(user=user)
        response = client.get(
            f"/api/v1/documents/{doc_a.pk}/relationship-graph/"
        )
        assert response.status_code == 200
        assert "nodes" in response.data
        assert "edges" in response.data
        assert len(response.data["nodes"]) == 2
        assert len(response.data["edges"]) == 1

    @pytest.mark.django_db
    def test_graph_node_structure(self, client, user, doc_a, doc_b, custom_type):
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=custom_type,
        )
        client.force_authenticate(user=user)
        response = client.get(
            f"/api/v1/documents/{doc_a.pk}/relationship-graph/"
        )
        node_ids = {n["id"] for n in response.data["nodes"]}
        assert doc_a.pk in node_ids
        assert doc_b.pk in node_ids
        for node in response.data["nodes"]:
            assert "id" in node
            assert "title" in node
            assert "document_type" in node

    @pytest.mark.django_db
    def test_graph_edge_structure(self, client, user, doc_a, doc_b, custom_type):
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=custom_type,
        )
        client.force_authenticate(user=user)
        response = client.get(
            f"/api/v1/documents/{doc_a.pk}/relationship-graph/"
        )
        edge = response.data["edges"][0]
        assert edge["source"] == doc_a.pk
        assert edge["target"] == doc_b.pk
        assert edge["type"] == "custom-type"
        assert edge["label"] == "Custom Type"

    @pytest.mark.django_db
    def test_graph_with_depth_1(
        self, client, user, doc_a, doc_b, doc_c, custom_type
    ):
        """With depth=1, only direct neighbors are included."""
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=custom_type,
        )
        DocumentRelationship.objects.create(
            source_document=doc_b,
            target_document=doc_c,
            relationship_type=custom_type,
        )
        client.force_authenticate(user=user)
        response = client.get(
            f"/api/v1/documents/{doc_a.pk}/relationship-graph/?depth=1"
        )
        assert response.status_code == 200
        node_ids = {n["id"] for n in response.data["nodes"]}
        assert doc_a.pk in node_ids
        assert doc_b.pk in node_ids
        assert doc_c.pk not in node_ids

    @pytest.mark.django_db
    def test_graph_with_depth_2(
        self, client, user, doc_a, doc_b, doc_c, custom_type
    ):
        """With depth=2, 2-hop neighbors are included."""
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=custom_type,
        )
        DocumentRelationship.objects.create(
            source_document=doc_b,
            target_document=doc_c,
            relationship_type=custom_type,
        )
        client.force_authenticate(user=user)
        response = client.get(
            f"/api/v1/documents/{doc_a.pk}/relationship-graph/?depth=2"
        )
        assert response.status_code == 200
        node_ids = {n["id"] for n in response.data["nodes"]}
        assert doc_a.pk in node_ids
        assert doc_b.pk in node_ids
        assert doc_c.pk in node_ids

    @pytest.mark.django_db
    def test_graph_depth_clamped_to_max_3(self, client, user, doc_a):
        """Depth > 3 should be clamped to 3."""
        client.force_authenticate(user=user)
        response = client.get(
            f"/api/v1/documents/{doc_a.pk}/relationship-graph/?depth=10"
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_graph_default_depth_is_2(
        self, client, user, doc_a, doc_b, doc_c, custom_type
    ):
        """Without explicit depth param, default is 2."""
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=custom_type,
        )
        DocumentRelationship.objects.create(
            source_document=doc_b,
            target_document=doc_c,
            relationship_type=custom_type,
        )
        client.force_authenticate(user=user)
        response = client.get(
            f"/api/v1/documents/{doc_a.pk}/relationship-graph/"
        )
        node_ids = {n["id"] for n in response.data["nodes"]}
        # Default depth=2 so doc_c (2 hops from doc_a) should be included
        assert doc_c.pk in node_ids

    @pytest.mark.django_db
    def test_graph_no_relationships(self, client, user, doc_a):
        """Document with no relationships returns only itself."""
        client.force_authenticate(user=user)
        response = client.get(
            f"/api/v1/documents/{doc_a.pk}/relationship-graph/"
        )
        assert response.status_code == 200
        assert len(response.data["nodes"]) == 1
        assert response.data["nodes"][0]["id"] == doc_a.pk
        assert len(response.data["edges"]) == 0

    @pytest.mark.django_db
    def test_graph_document_not_found(self, client, user):
        client.force_authenticate(user=user)
        response = client.get("/api/v1/documents/99999/relationship-graph/")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_graph_unauthenticated(self, client, doc_a):
        response = client.get(
            f"/api/v1/documents/{doc_a.pk}/relationship-graph/"
        )
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_graph_invalid_depth_falls_back_to_default(
        self, client, user, doc_a
    ):
        """Non-integer depth falls back to default."""
        client.force_authenticate(user=user)
        response = client.get(
            f"/api/v1/documents/{doc_a.pk}/relationship-graph/?depth=abc"
        )
        assert response.status_code == 200
