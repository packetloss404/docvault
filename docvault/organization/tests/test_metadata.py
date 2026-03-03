"""Tests for MetadataType, DocumentMetadata, and related API endpoints."""

from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from documents.models import Document, DocumentType
from organization.models import (
    DocumentMetadata,
    DocumentTypeMetadata,
    MetadataType,
)


class MetadataTypeModelTest(TestCase):
    """Tests for the MetadataType model."""

    def setUp(self):
        self.user = User.objects.create_user(username="mtuser", password="pass!")

    def test_create_metadata_type(self):
        mt = MetadataType.objects.create(
            name="invoice_date",
            label="Invoice Date",
            owner=self.user,
        )
        self.assertEqual(mt.name, "invoice_date")
        self.assertEqual(mt.slug, "invoice_date")
        self.assertEqual(mt.get_display_label(), "Invoice Date")

    def test_display_label_fallback(self):
        mt = MetadataType(name="test")
        self.assertEqual(mt.get_display_label(), "test")

    def test_str(self):
        mt = MetadataType(name="test", label="Test Label")
        self.assertEqual(str(mt), "Test Label")

    def test_str_without_label(self):
        mt = MetadataType(name="test")
        self.assertEqual(str(mt), "test")

    def test_render_default_static(self):
        mt = MetadataType(name="t", default="hello")
        self.assertEqual(mt.render_default(), "hello")

    def test_render_default_template(self):
        mt = MetadataType(name="t", default="{{ year }}-01-01")
        self.assertEqual(mt.render_default({"year": "2026"}), "2026-01-01")

    def test_render_default_empty(self):
        mt = MetadataType(name="t")
        self.assertEqual(mt.render_default(), "")

    def test_render_default_invalid_template(self):
        mt = MetadataType(name="t", default="{{ unclosed")
        # Should return the raw template on error
        self.assertEqual(mt.render_default(), "{{ unclosed")

    def test_render_lookup(self):
        mt = MetadataType(name="t", lookup="Option A\nOption B\nOption C")
        self.assertEqual(mt.render_lookup(), ["Option A", "Option B", "Option C"])

    def test_render_lookup_template(self):
        mt = MetadataType(
            name="t",
            lookup="{% for i in range(3) %}Item {{ i }}\n{% endfor %}",
        )
        opts = mt.render_lookup()
        self.assertIn("Item 0", opts)
        self.assertIn("Item 2", opts)

    def test_render_lookup_empty(self):
        mt = MetadataType(name="t")
        self.assertEqual(mt.render_lookup(), [])

    def test_builtin_required_validator(self):
        mt = MetadataType(name="t", validation="required")
        mt.validate_value("hello")  # should not raise
        with self.assertRaises(ValidationError):
            mt.validate_value("")

    def test_builtin_date_format_validator(self):
        mt = MetadataType(name="t", validation="date_format", default="%Y-%m-%d")
        mt.validate_value("2026-01-15")  # should not raise
        with self.assertRaises(ValidationError):
            mt.validate_value("not-a-date")

    def test_builtin_numeric_range_validator(self):
        mt = MetadataType(name="t", validation="numeric_range", default="1,100")
        mt.validate_value("50")  # should not raise
        with self.assertRaises(ValidationError):
            mt.validate_value("200")
        with self.assertRaises(ValidationError):
            mt.validate_value("abc")

    def test_builtin_integer_parser(self):
        mt = MetadataType(name="t", parser="integer")
        self.assertEqual(mt.parse_value("42"), 42)

    def test_builtin_float_parser(self):
        mt = MetadataType(name="t", parser="float")
        self.assertAlmostEqual(mt.parse_value("3.14"), 3.14)

    def test_builtin_date_parser(self):
        mt = MetadataType(name="t", parser="date", default="%Y-%m-%d")
        result = mt.parse_value("2026-03-01")
        self.assertEqual(result, date(2026, 3, 1))

    def test_no_validator(self):
        mt = MetadataType(name="t")
        mt.validate_value("anything")  # should not raise

    def test_no_parser(self):
        mt = MetadataType(name="t")
        self.assertEqual(mt.parse_value("raw"), "raw")

    def test_invalid_validator_path(self):
        mt = MetadataType(name="t", validation="nonexistent.module.func")
        # Should not raise — just returns None validator
        mt.validate_value("anything")

    def test_unique_name_per_owner(self):
        MetadataType.objects.create(name="test", owner=self.user)
        with self.assertRaises(Exception):
            MetadataType.objects.create(name="test", owner=self.user)


class DocumentMetadataModelTest(TestCase):
    """Tests for the DocumentMetadata model."""

    def setUp(self):
        self.user = User.objects.create_user(username="dmuser", password="pass!")
        self.doc = Document.objects.create(
            title="Test", owner=self.user, filename="o/dm1.txt",
        )

    def test_create_metadata_instance(self):
        mt = MetadataType.objects.create(name="date", owner=self.user)
        dm = DocumentMetadata.objects.create(
            document=self.doc, metadata_type=mt, value="2026-01-15",
        )
        self.assertEqual(str(dm), "date: 2026-01-15")

    def test_metadata_validation_on_save(self):
        mt = MetadataType.objects.create(
            name="required_field",
            validation="required",
            owner=self.user,
        )
        with self.assertRaises(ValidationError):
            DocumentMetadata.objects.create(
                document=self.doc, metadata_type=mt, value="",
            )

    def test_parsed_value(self):
        mt = MetadataType.objects.create(
            name="count", parser="integer", owner=self.user,
        )
        dm = DocumentMetadata.objects.create(
            document=self.doc, metadata_type=mt, value="42",
        )
        self.assertEqual(dm.parsed_value, 42)

    def test_unique_per_document(self):
        mt = MetadataType.objects.create(name="x", owner=self.user)
        DocumentMetadata.objects.create(
            document=self.doc, metadata_type=mt, value="a",
        )
        with self.assertRaises(Exception):
            DocumentMetadata.objects.create(
                document=self.doc, metadata_type=mt, value="b",
            )


class DocumentTypeMetadataTest(TestCase):
    """Tests for DocumentType <-> MetadataType assignment."""

    def setUp(self):
        self.user = User.objects.create_user(username="dtmuser", password="pass!")
        self.dt = DocumentType.objects.create(name="Invoice", owner=self.user)
        self.mt = MetadataType.objects.create(
            name="invoice_date", label="Invoice Date", owner=self.user,
        )

    def test_assign_metadata_to_doctype(self):
        assignment = DocumentTypeMetadata.objects.create(
            document_type=self.dt, metadata_type=self.mt, required=True,
        )
        self.assertEqual(str(assignment), "Invoice -> Invoice Date")
        self.assertTrue(assignment.required)

    def test_unique_assignment(self):
        DocumentTypeMetadata.objects.create(
            document_type=self.dt, metadata_type=self.mt,
        )
        with self.assertRaises(Exception):
            DocumentTypeMetadata.objects.create(
                document_type=self.dt, metadata_type=self.mt,
            )


class MetadataAPITest(TestCase):
    """Tests for MetadataType and DocumentMetadata API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="mtapi", password="pass!")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_list_metadata_types(self):
        MetadataType.objects.create(name="mt1", owner=self.user)
        resp = self.client.get("/api/v1/metadata-types/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)

    def test_create_metadata_type(self):
        resp = self.client.post("/api/v1/metadata-types/", {
            "name": "invoice_date",
            "label": "Invoice Date",
            "validation": "date_format",
            "default": "%Y-%m-%d",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "invoice_date")
        self.assertEqual(resp.data["validation"], "date_format")

    def test_update_metadata_type(self):
        mt = MetadataType.objects.create(name="old", owner=self.user)
        resp = self.client.patch(f"/api/v1/metadata-types/{mt.pk}/", {
            "label": "New Label",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["label"], "New Label")

    def test_delete_metadata_type(self):
        mt = MetadataType.objects.create(name="del", owner=self.user)
        resp = self.client.delete(f"/api/v1/metadata-types/{mt.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_lookup_options(self):
        mt = MetadataType.objects.create(
            name="status",
            lookup="Draft\nReview\nFinal",
            owner=self.user,
        )
        resp = self.client.get(f"/api/v1/metadata-types/{mt.pk}/lookup-options/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["options"], ["Draft", "Review", "Final"])

    def test_document_metadata_nested_list(self):
        doc = Document.objects.create(
            title="Test", owner=self.user, filename="o/mapi1.txt",
        )
        mt = MetadataType.objects.create(
            name="date", label="Date", owner=self.user,
        )
        DocumentMetadata.objects.create(
            document=doc, metadata_type=mt, value="2026-01-15",
        )
        resp = self.client.get(f"/api/v1/documents/{doc.pk}/metadata/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["value"], "2026-01-15")
        self.assertEqual(resp.data[0]["metadata_type_label"], "Date")

    def test_document_metadata_nested_create(self):
        doc = Document.objects.create(
            title="Test", owner=self.user, filename="o/mapi2.txt",
        )
        mt = MetadataType.objects.create(name="note", owner=self.user)
        resp = self.client.post(f"/api/v1/documents/{doc.pk}/metadata/", {
            "document": doc.pk,
            "metadata_type": mt.pk,
            "value": "Important",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            DocumentMetadata.objects.get(document=doc, metadata_type=mt).value,
            "Important",
        )

    def test_document_metadata_nested_delete(self):
        doc = Document.objects.create(
            title="Test", owner=self.user, filename="o/mapi3.txt",
        )
        mt = MetadataType.objects.create(name="x", owner=self.user)
        dm = DocumentMetadata.objects.create(
            document=doc, metadata_type=mt, value="bye",
        )
        resp = self.client.delete(
            f"/api/v1/documents/{doc.pk}/metadata/{dm.pk}/",
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_doctype_metadata_assignment_api(self):
        dt = DocumentType.objects.create(name="Invoice", owner=self.user)
        mt = MetadataType.objects.create(
            name="date", label="Invoice Date", owner=self.user,
        )
        resp = self.client.post(
            f"/api/v1/document-types/{dt.pk}/metadata-types/",
            {"document_type": dt.pk, "metadata_type": mt.pk, "required": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["metadata_type_name"], "date")
        self.assertTrue(resp.data["required"])

        resp = self.client.get(f"/api/v1/document-types/{dt.pk}/metadata-types/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
