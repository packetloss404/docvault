"""Tests for Zone OCR API endpoints."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from documents.models import Document
from zone_ocr.constants import FIELD_DATE, FIELD_INTEGER, FIELD_STRING, PREPROCESS_NONE
from zone_ocr.models import ZoneOCRField, ZoneOCRResult, ZoneOCRTemplate


@pytest.fixture
def user(db):
    return User.objects.create_user(username="zoneapi", password="testpass")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def template(user):
    return ZoneOCRTemplate.objects.create(
        name="Invoice Template",
        description="Invoice extraction",
        page_number=1,
        is_active=True,
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def zone_field(template):
    return ZoneOCRField.objects.create(
        template=template,
        name="Invoice Number",
        field_type=FIELD_STRING,
        bounding_box={"x": 10, "y": 10, "width": 30, "height": 5},
        order=0,
    )


@pytest.fixture
def document(user):
    return Document.objects.create(
        title="Test Invoice",
        content="Invoice Number: INV-001\nInvoice Date: 2025-01-15\nTotal Amount: 1500",
        owner=user,
    )


@pytest.fixture
def result(document, template, zone_field):
    return ZoneOCRResult.objects.create(
        document=document,
        template=template,
        field=zone_field,
        extracted_value="INV-001",
        confidence=0.85,
    )


# ---- Template CRUD ----


@pytest.mark.django_db
class TestZoneOCRTemplateViewSet:
    def test_list_templates(self, client, template):
        response = client.get("/api/v1/zone-ocr-templates/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == "Invoice Template"

    def test_create_template(self, client):
        data = {
            "name": "Receipt Template",
            "description": "For receipts",
            "page_number": 1,
            "is_active": True,
        }
        response = client.post("/api/v1/zone-ocr-templates/", data, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "Receipt Template"
        assert ZoneOCRTemplate.objects.filter(name="Receipt Template").exists()

    def test_retrieve_template(self, client, template, zone_field):
        response = client.get(f"/api/v1/zone-ocr-templates/{template.pk}/")
        assert response.status_code == 200
        assert response.data["name"] == "Invoice Template"
        assert "fields" in response.data
        assert len(response.data["fields"]) == 1

    def test_update_template(self, client, template):
        data = {"name": "Updated Template", "description": "Updated"}
        response = client.patch(
            f"/api/v1/zone-ocr-templates/{template.pk}/", data, format="json",
        )
        assert response.status_code == 200
        template.refresh_from_db()
        assert template.name == "Updated Template"

    def test_delete_template(self, client, template):
        response = client.delete(f"/api/v1/zone-ocr-templates/{template.pk}/")
        assert response.status_code == 204
        assert not ZoneOCRTemplate.objects.filter(pk=template.pk).exists()

    def test_list_includes_field_count(self, client, template, zone_field):
        response = client.get("/api/v1/zone-ocr-templates/")
        assert response.data["results"][0]["field_count"] == 1

    def test_unauthenticated_access_denied(self, anon_client, template):
        response = anon_client.get("/api/v1/zone-ocr-templates/")
        assert response.status_code in (401, 403)


# ---- Field CRUD ----


@pytest.mark.django_db
class TestZoneOCRFieldViews:
    def test_list_fields(self, client, template, zone_field):
        url = f"/api/v1/zone-ocr-templates/{template.pk}/fields/"
        response = client.get(url)
        assert response.status_code == 200
        results = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        assert len(results) >= 1

    def test_create_field(self, client, template):
        url = f"/api/v1/zone-ocr-templates/{template.pk}/fields/"
        data = {
            "template": template.pk,
            "name": "Total Amount",
            "field_type": FIELD_INTEGER,
            "bounding_box": {"x": 60, "y": 80, "width": 20, "height": 5},
            "order": 2,
        }
        response = client.post(url, data, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "Total Amount"
        assert ZoneOCRField.objects.filter(template=template, name="Total Amount").exists()

    def test_retrieve_field(self, client, template, zone_field):
        url = f"/api/v1/zone-ocr-templates/{template.pk}/fields/{zone_field.pk}/"
        response = client.get(url)
        assert response.status_code == 200
        assert response.data["name"] == "Invoice Number"

    def test_update_field(self, client, template, zone_field):
        url = f"/api/v1/zone-ocr-templates/{template.pk}/fields/{zone_field.pk}/"
        data = {"name": "Inv No", "field_type": FIELD_STRING,
                "bounding_box": {"x": 10, "y": 10, "width": 30, "height": 5}}
        response = client.patch(url, data, format="json")
        assert response.status_code == 200
        zone_field.refresh_from_db()
        assert zone_field.name == "Inv No"

    def test_delete_field(self, client, template, zone_field):
        url = f"/api/v1/zone-ocr-templates/{template.pk}/fields/{zone_field.pk}/"
        response = client.delete(url)
        assert response.status_code == 204
        assert not ZoneOCRField.objects.filter(pk=zone_field.pk).exists()

    def test_invalid_bounding_box_rejected(self, client, template):
        url = f"/api/v1/zone-ocr-templates/{template.pk}/fields/"
        data = {
            "name": "Bad BB",
            "field_type": FIELD_STRING,
            "bounding_box": {"x": 10},  # missing y, width, height
            "order": 0,
        }
        response = client.post(url, data, format="json")
        assert response.status_code == 400

    def test_unauthenticated_access_denied(self, anon_client, template):
        url = f"/api/v1/zone-ocr-templates/{template.pk}/fields/"
        response = anon_client.get(url)
        assert response.status_code in (401, 403)


# ---- Result list and filtering ----


@pytest.mark.django_db
class TestZoneOCRResultListView:
    @staticmethod
    def _results(response):
        """Extract the results list from a potentially paginated response."""
        data = response.data
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return data

    def test_list_results(self, client, result):
        response = client.get("/api/v1/zone-ocr-results/")
        assert response.status_code == 200
        assert len(self._results(response)) >= 1

    def test_filter_by_document_id(self, client, result, document):
        response = client.get(f"/api/v1/zone-ocr-results/?document_id={document.pk}")
        assert response.status_code == 200
        assert len(self._results(response)) == 1

    def test_filter_by_template_id(self, client, result, template):
        response = client.get(f"/api/v1/zone-ocr-results/?template_id={template.pk}")
        assert response.status_code == 200
        assert len(self._results(response)) == 1

    def test_filter_by_confidence_lt(self, client, result):
        # result has confidence 0.85
        response = client.get("/api/v1/zone-ocr-results/?confidence__lt=0.9")
        assert response.status_code == 200
        assert len(self._results(response)) == 1

        response = client.get("/api/v1/zone-ocr-results/?confidence__lt=0.5")
        assert response.status_code == 200
        assert len(self._results(response)) == 0

    def test_filter_by_reviewed(self, client, result):
        response = client.get("/api/v1/zone-ocr-results/?reviewed=false")
        assert response.status_code == 200
        assert len(self._results(response)) == 1

        response = client.get("/api/v1/zone-ocr-results/?reviewed=true")
        assert response.status_code == 200
        assert len(self._results(response)) == 0

    def test_unauthenticated_access_denied(self, anon_client):
        response = anon_client.get("/api/v1/zone-ocr-results/")
        assert response.status_code in (401, 403)


# ---- Result correction ----


@pytest.mark.django_db
class TestZoneOCRResultCorrectionView:
    def test_retrieve_result(self, client, result):
        response = client.get(f"/api/v1/zone-ocr-results/{result.pk}/")
        assert response.status_code == 200
        assert response.data["extracted_value"] == "INV-001"
        assert response.data["effective_value"] == "INV-001"

    def test_patch_correction(self, client, result, user):
        data = {"corrected_value": "INV-002"}
        response = client.patch(
            f"/api/v1/zone-ocr-results/{result.pk}/", data, format="json",
        )
        assert response.status_code == 200
        result.refresh_from_db()
        assert result.corrected_value == "INV-002"
        assert result.reviewed is True
        assert result.reviewed_by == user

    def test_unauthenticated_correction_denied(self, anon_client, result):
        response = anon_client.patch(
            f"/api/v1/zone-ocr-results/{result.pk}/",
            {"corrected_value": "X"},
            format="json",
        )
        assert response.status_code in (401, 403)


# ---- Test template endpoint ----


@pytest.mark.django_db
class TestTestTemplateView:
    def test_test_template_success(self, client, template, zone_field, document):
        url = f"/api/v1/zone-ocr-templates/{template.pk}/test/"
        data = {"document_id": document.pk}
        response = client.post(url, data, format="json")
        assert response.status_code == 200
        assert response.data["template_id"] == template.pk
        assert response.data["document_id"] == document.pk
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["field_name"] == "Invoice Number"

    def test_test_template_not_found(self, client, document):
        url = "/api/v1/zone-ocr-templates/99999/test/"
        data = {"document_id": document.pk}
        response = client.post(url, data, format="json")
        assert response.status_code == 404

    def test_test_template_document_not_found(self, client, template, zone_field):
        url = f"/api/v1/zone-ocr-templates/{template.pk}/test/"
        data = {"document_id": 99999}
        response = client.post(url, data, format="json")
        assert response.status_code == 404

    def test_test_template_missing_document_id(self, client, template):
        url = f"/api/v1/zone-ocr-templates/{template.pk}/test/"
        response = client.post(url, {}, format="json")
        assert response.status_code == 400

    def test_test_template_unauthenticated(self, anon_client, template):
        url = f"/api/v1/zone-ocr-templates/{template.pk}/test/"
        response = anon_client.post(url, {"document_id": 1}, format="json")
        assert response.status_code in (401, 403)
