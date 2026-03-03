"""Tests for Zone OCR models (ZoneOCRTemplate, ZoneOCRField, ZoneOCRResult)."""

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError

from documents.models import Document
from zone_ocr.constants import FIELD_DATE, FIELD_INTEGER, FIELD_STRING, PREPROCESS_NONE
from zone_ocr.models import ZoneOCRField, ZoneOCRResult, ZoneOCRTemplate


@pytest.fixture
def user(db):
    return User.objects.create_user(username="zoneuser", password="testpass")


@pytest.fixture
def template(user):
    return ZoneOCRTemplate.objects.create(
        name="Invoice Template",
        description="Extracts fields from invoices",
        page_number=1,
        is_active=True,
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def field_a(template):
    return ZoneOCRField.objects.create(
        template=template,
        name="Invoice Number",
        field_type=FIELD_STRING,
        bounding_box={"x": 10, "y": 10, "width": 30, "height": 5},
        order=0,
        preprocessing=PREPROCESS_NONE,
    )


@pytest.fixture
def field_b(template):
    return ZoneOCRField.objects.create(
        template=template,
        name="Invoice Date",
        field_type=FIELD_DATE,
        bounding_box={"x": 50, "y": 10, "width": 30, "height": 5},
        order=1,
        preprocessing=PREPROCESS_NONE,
    )


@pytest.fixture
def document(user):
    return Document.objects.create(
        title="Test Invoice",
        content="Invoice Number: INV-001\nInvoice Date: 2025-01-15",
        owner=user,
    )


@pytest.mark.django_db
class TestZoneOCRTemplate:
    def test_create_template(self, template):
        assert template.pk is not None
        assert template.name == "Invoice Template"
        assert template.page_number == 1
        assert template.is_active is True
        assert template.created_at is not None
        assert template.updated_at is not None

    def test_str_representation(self, template):
        assert str(template) == "Invoice Template"

    def test_ordering_by_name(self, user):
        ZoneOCRTemplate.objects.create(name="Zebra", created_by=user, updated_by=user)
        ZoneOCRTemplate.objects.create(name="Alpha", created_by=user, updated_by=user)
        ZoneOCRTemplate.objects.create(name="Middle", created_by=user, updated_by=user)
        names = list(ZoneOCRTemplate.objects.values_list("name", flat=True))
        assert names == sorted(names)

    def test_default_values(self, user):
        t = ZoneOCRTemplate.objects.create(name="Minimal", created_by=user, updated_by=user)
        assert t.page_number == 1
        assert t.is_active is True
        assert t.description == ""


@pytest.mark.django_db
class TestZoneOCRField:
    def test_create_field(self, field_a, template):
        assert field_a.pk is not None
        assert field_a.template == template
        assert field_a.name == "Invoice Number"
        assert field_a.field_type == FIELD_STRING

    def test_str_representation(self, field_a):
        assert "Invoice Template" in str(field_a)
        assert "Invoice Number" in str(field_a)

    def test_ordering_by_order(self, field_a, field_b):
        fields = list(
            ZoneOCRField.objects.filter(template=field_a.template).values_list("name", flat=True)
        )
        assert fields == ["Invoice Number", "Invoice Date"]

    def test_unique_constraint_template_name(self, template):
        ZoneOCRField.objects.create(
            template=template,
            name="Amount",
            field_type=FIELD_INTEGER,
            bounding_box={"x": 0, "y": 0, "width": 10, "height": 10},
        )
        with pytest.raises(IntegrityError):
            ZoneOCRField.objects.create(
                template=template,
                name="Amount",
                field_type=FIELD_STRING,
                bounding_box={"x": 20, "y": 20, "width": 10, "height": 10},
            )

    def test_cascade_delete_template_deletes_fields(self, template, field_a, field_b):
        assert ZoneOCRField.objects.filter(template=template).count() == 2
        template.delete()
        assert ZoneOCRField.objects.filter(template_id=template.pk).count() == 0

    def test_default_values(self, template):
        f = ZoneOCRField.objects.create(
            template=template,
            name="Basic",
            field_type=FIELD_STRING,
            bounding_box={"x": 0, "y": 0, "width": 10, "height": 10},
        )
        assert f.order == 0
        assert f.preprocessing == PREPROCESS_NONE
        assert f.validation_regex == ""
        assert f.custom_field is None


@pytest.mark.django_db
class TestZoneOCRResult:
    def test_create_result(self, document, template, field_a, user):
        result = ZoneOCRResult.objects.create(
            document=document,
            template=template,
            field=field_a,
            extracted_value="INV-001",
            confidence=0.95,
        )
        assert result.pk is not None
        assert result.extracted_value == "INV-001"
        assert result.confidence == 0.95
        assert result.reviewed is False
        assert result.corrected_value == ""

    def test_effective_value_returns_extracted_when_no_correction(self, document, template, field_a):
        result = ZoneOCRResult.objects.create(
            document=document,
            template=template,
            field=field_a,
            extracted_value="INV-001",
            confidence=0.9,
        )
        assert result.effective_value == "INV-001"

    def test_effective_value_returns_corrected_when_set(self, document, template, field_a):
        result = ZoneOCRResult.objects.create(
            document=document,
            template=template,
            field=field_a,
            extracted_value="INV-001",
            corrected_value="INV-002",
            confidence=0.9,
        )
        assert result.effective_value == "INV-002"

    def test_effective_value_empty_corrected_falls_back(self, document, template, field_a):
        result = ZoneOCRResult.objects.create(
            document=document,
            template=template,
            field=field_a,
            extracted_value="INV-001",
            corrected_value="",
            confidence=0.9,
        )
        assert result.effective_value == "INV-001"

    def test_unique_constraint_document_template_field(self, document, template, field_a):
        ZoneOCRResult.objects.create(
            document=document,
            template=template,
            field=field_a,
            extracted_value="first",
        )
        with pytest.raises(IntegrityError):
            ZoneOCRResult.objects.create(
                document=document,
                template=template,
                field=field_a,
                extracted_value="second",
            )

    def test_cascade_delete_document_deletes_results(self, document, template, field_a):
        ZoneOCRResult.objects.create(
            document=document, template=template, field=field_a, extracted_value="val",
        )
        assert ZoneOCRResult.objects.count() == 1
        document.hard_delete()
        assert ZoneOCRResult.objects.count() == 0

    def test_cascade_delete_template_deletes_results(self, document, template, field_a):
        ZoneOCRResult.objects.create(
            document=document, template=template, field=field_a, extracted_value="val",
        )
        template.delete()
        assert ZoneOCRResult.objects.count() == 0

    def test_cascade_delete_field_deletes_results(self, document, template, field_a):
        ZoneOCRResult.objects.create(
            document=document, template=template, field=field_a, extracted_value="val",
        )
        field_a.delete()
        assert ZoneOCRResult.objects.count() == 0

    def test_str_representation(self, document, template, field_a):
        result = ZoneOCRResult.objects.create(
            document=document,
            template=template,
            field=field_a,
            extracted_value="INV-001",
        )
        s = str(result)
        assert "INV-001" in s
        assert "Invoice Number" in s

    def test_reviewed_by_user(self, document, template, field_a, user):
        result = ZoneOCRResult.objects.create(
            document=document,
            template=template,
            field=field_a,
            extracted_value="INV-001",
            reviewed=True,
            reviewed_by=user,
            corrected_value="INV-002",
        )
        assert result.reviewed is True
        assert result.reviewed_by == user
