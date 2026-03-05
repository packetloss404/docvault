"""Tests for Entity API endpoints."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from documents.models import Document
from entities.models import Entity, EntityType


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="entityadmin", password="adminpass", email="admin@test.com",
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(username="entityregular", password="testpass")


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def regular_client(regular_user):
    c = APIClient()
    c.force_authenticate(user=regular_user)
    return c


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def entity_type(db):
    return EntityType.objects.create(
        name="PERSON", label="Person", color="#0d6efd", icon="bi-person",
    )


@pytest.fixture
def entity_type_org(db):
    return EntityType.objects.create(
        name="ORGANIZATION", label="Organization", color="#6610f2", icon="bi-building",
    )


@pytest.fixture
def document(admin_user):
    return Document.objects.create(
        title="Entity View Doc",
        content="John Doe works at Acme Corp.",
        owner=admin_user,
    )


@pytest.fixture
def document2(admin_user):
    return Document.objects.create(
        title="Second Doc",
        content="Jane Smith at Beta Inc.",
        owner=admin_user,
    )


@pytest.fixture
def entity_person(document, entity_type):
    return Entity.objects.create(
        document=document,
        entity_type=entity_type,
        value="John Doe",
        raw_value="John Doe",
        confidence=0.95,
    )


@pytest.fixture
def entity_org(document, entity_type_org):
    return Entity.objects.create(
        document=document,
        entity_type=entity_type_org,
        value="ACME CORP",
        raw_value="Acme Corp",
        confidence=0.9,
    )


# ---- EntityType CRUD ----


@pytest.mark.django_db
class TestEntityTypeViewSet:
    def test_list_entity_types(self, regular_client, entity_type):
        response = regular_client.get("/api/v1/entity-types/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_retrieve_entity_type(self, regular_client, entity_type):
        response = regular_client.get(f"/api/v1/entity-types/{entity_type.pk}/")
        assert response.status_code == 200
        assert response.data["name"] == "PERSON"

    def test_create_entity_type_admin(self, admin_client):
        data = {
            "name": "LOCATION",
            "label": "Location",
            "color": "#198754",
            "icon": "bi-geo-alt",
        }
        response = admin_client.post("/api/v1/entity-types/", data, format="json")
        assert response.status_code == 201
        assert EntityType.objects.filter(name="LOCATION").exists()

    def test_create_entity_type_non_admin_forbidden(self, regular_client):
        data = {"name": "LOCATION", "label": "Location"}
        response = regular_client.post("/api/v1/entity-types/", data, format="json")
        assert response.status_code == 403

    def test_update_entity_type_admin(self, admin_client, entity_type):
        data = {"label": "Human Person"}
        response = admin_client.patch(
            f"/api/v1/entity-types/{entity_type.pk}/", data, format="json",
        )
        assert response.status_code == 200
        entity_type.refresh_from_db()
        assert entity_type.label == "Human Person"

    def test_update_entity_type_non_admin_forbidden(self, regular_client, entity_type):
        data = {"label": "Hacked"}
        response = regular_client.patch(
            f"/api/v1/entity-types/{entity_type.pk}/", data, format="json",
        )
        assert response.status_code == 403

    def test_delete_entity_type_admin(self, admin_client, entity_type):
        response = admin_client.delete(f"/api/v1/entity-types/{entity_type.pk}/")
        assert response.status_code == 204
        assert not EntityType.objects.filter(pk=entity_type.pk).exists()

    def test_delete_entity_type_non_admin_forbidden(self, regular_client, entity_type):
        response = regular_client.delete(f"/api/v1/entity-types/{entity_type.pk}/")
        assert response.status_code == 403

    def test_unauthenticated_list_denied(self, anon_client):
        response = anon_client.get("/api/v1/entity-types/")
        assert response.status_code in (401, 403)


# ---- Entity list and filtering ----


@pytest.mark.django_db
class TestEntityListView:
    def test_list_entities(self, admin_client, entity_person, entity_org):
        response = admin_client.get("/api/v1/entities/")
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        assert len(results) >= 2

    def test_filter_by_document_id(self, admin_client, entity_person, document):
        response = admin_client.get(f"/api/v1/entities/?document_id={document.pk}")
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        assert len(results) >= 1

    def test_filter_by_entity_type(self, admin_client, entity_person, entity_org):
        response = admin_client.get("/api/v1/entities/?entity_type=PERSON")
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        values = [e["value"] for e in results]
        assert "John Doe" in values
        assert "ACME CORP" not in values

    def test_filter_by_value(self, admin_client, entity_person):
        response = admin_client.get("/api/v1/entities/?value=John")
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        assert len(results) >= 1

    def test_aggregate_mode(self, admin_client, entity_person, entity_org, document2, entity_type):
        # Create another entity with same value in different doc
        Entity.objects.create(
            document=document2,
            entity_type=entity_type,
            value="John Doe",
            raw_value="John Doe",
        )
        response = admin_client.get("/api/v1/entities/?aggregate=true")
        assert response.status_code == 200
        # Aggregate mode returns raw list (not paginated)
        data = response.data
        # If paginated, get results; otherwise use data directly
        items = data.get("results", data) if isinstance(data, dict) else data
        agg = {item["value"]: item for item in items}
        assert "John Doe" in agg
        assert agg["John Doe"]["document_count"] == 2

    def test_unauthenticated_denied(self, anon_client):
        response = anon_client.get("/api/v1/entities/")
        assert response.status_code in (401, 403)


# ---- Document entity list ----


@pytest.mark.django_db
class TestDocumentEntityListView:
    def test_list_entities_for_document(self, admin_client, document, entity_person, entity_org):
        response = admin_client.get(f"/api/v1/documents/{document.pk}/entities/")
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        assert len(results) == 2

    def test_empty_for_nonexistent_document(self, admin_client):
        response = admin_client.get("/api/v1/documents/99999/entities/")
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        assert len(results) == 0


# ---- Entity documents list ----


@pytest.mark.django_db
class TestEntityDocumentsView:
    def test_list_documents_for_entity(self, admin_client, entity_person, document):
        response = admin_client.get("/api/v1/entities/PERSON/John Doe/documents/")
        assert response.status_code == 200
        assert len(response.data) >= 1

    def test_empty_for_nonexistent_entity(self, admin_client):
        response = admin_client.get("/api/v1/entities/PERSON/Nonexistent/documents/")
        assert response.status_code == 200
        assert len(response.data) == 0

    def test_non_superuser_only_sees_own_documents(
        self, regular_client, regular_user, entity_type, document,
    ):
        # Create a doc owned by regular_user
        own_doc = Document.objects.create(
            title="My Doc", content="John Doe is here", owner=regular_user,
        )
        Entity.objects.create(
            document=own_doc, entity_type=entity_type,
            value="John Doe", raw_value="John Doe",
        )
        # entity_person is in admin's document
        Entity.objects.create(
            document=document, entity_type=entity_type,
            value="John Doe", raw_value="John Doe",
        )
        response = regular_client.get("/api/v1/entities/PERSON/John Doe/documents/")
        assert response.status_code == 200
        doc_ids = [d["id"] for d in response.data]
        assert own_doc.pk in doc_ids
        assert document.pk not in doc_ids
