"""Tests for CustomField, CustomFieldInstance, and related API endpoints."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from documents.models import Document, DocumentType
from organization.models import (
    CustomField,
    CustomFieldInstance,
    DocumentTypeCustomField,
)
from organization.models.custom_field import (
    FIELD_BOOLEAN,
    FIELD_DATE,
    FIELD_DATETIME,
    FIELD_DOCUMENTLINK,
    FIELD_FLOAT,
    FIELD_INTEGER,
    FIELD_LONGTEXT,
    FIELD_MONETARY,
    FIELD_MULTISELECT,
    FIELD_SELECT,
    FIELD_STRING,
    FIELD_URL,
)


class CustomFieldModelTest(TestCase):
    """Tests for the CustomField model."""

    def setUp(self):
        self.user = User.objects.create_user(username="cfuser", password="pass!")

    def test_create_string_field(self):
        cf = CustomField.objects.create(
            name="Invoice Number", data_type=FIELD_STRING, owner=self.user,
        )
        self.assertEqual(cf.name, "Invoice Number")
        self.assertEqual(cf.slug, "invoice-number")
        self.assertEqual(cf.data_type, FIELD_STRING)

    def test_create_select_field_with_options(self):
        cf = CustomField.objects.create(
            name="Priority",
            data_type=FIELD_SELECT,
            extra_data={"options": ["Low", "Medium", "High"]},
            owner=self.user,
        )
        self.assertEqual(cf.get_select_options(), ["Low", "Medium", "High"])

    def test_value_column_mapping(self):
        cases = [
            (FIELD_STRING, "value_text"),
            (FIELD_LONGTEXT, "value_text"),
            (FIELD_URL, "value_url"),
            (FIELD_DATE, "value_date"),
            (FIELD_DATETIME, "value_datetime"),
            (FIELD_BOOLEAN, "value_bool"),
            (FIELD_INTEGER, "value_int"),
            (FIELD_FLOAT, "value_float"),
            (FIELD_MONETARY, "value_monetary"),
            (FIELD_DOCUMENTLINK, "value_document_ids"),
            (FIELD_SELECT, "value_select"),
            (FIELD_MULTISELECT, "value_select"),
        ]
        for data_type, expected_column in cases:
            cf = CustomField(name="test", data_type=data_type)
            self.assertEqual(cf.value_column, expected_column, f"Failed for {data_type}")

    def test_str(self):
        cf = CustomField(name="Test Field")
        self.assertEqual(str(cf), "Test Field")

    def test_unique_name_per_owner(self):
        CustomField.objects.create(
            name="Amount", data_type=FIELD_FLOAT, owner=self.user,
        )
        with self.assertRaises(Exception):
            CustomField.objects.create(
                name="Amount", data_type=FIELD_INTEGER, owner=self.user,
            )


class CustomFieldInstanceModelTest(TestCase):
    """Tests for the CustomFieldInstance model."""

    def setUp(self):
        self.user = User.objects.create_user(username="cfiuser", password="pass!")
        self.doc = Document.objects.create(
            title="Test Doc", owner=self.user, filename="o/cf1.txt",
        )

    def test_set_string_value(self):
        cf = CustomField.objects.create(
            name="Note", data_type=FIELD_STRING, owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = "Hello world"
        inst.save()
        self.assertEqual(inst.value, "Hello world")
        self.assertEqual(inst.value_text, "Hello world")

    def test_set_integer_value(self):
        cf = CustomField.objects.create(
            name="Count", data_type=FIELD_INTEGER, owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = 42
        inst.save()
        self.assertEqual(inst.value, 42)
        self.assertEqual(inst.value_int, 42)

    def test_set_boolean_value(self):
        cf = CustomField.objects.create(
            name="Approved", data_type=FIELD_BOOLEAN, owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = True
        inst.save()
        self.assertTrue(inst.value)

    def test_set_float_value(self):
        cf = CustomField.objects.create(
            name="Amount", data_type=FIELD_FLOAT, owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = 99.95
        inst.save()
        self.assertAlmostEqual(inst.value, 99.95)

    def test_set_monetary_value(self):
        cf = CustomField.objects.create(
            name="Price", data_type=FIELD_MONETARY, owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = Decimal("149.9900")
        inst.save()
        self.assertEqual(inst.value, Decimal("149.9900"))

    def test_set_url_value(self):
        cf = CustomField.objects.create(
            name="Link", data_type=FIELD_URL, owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = "https://example.com"
        inst.save()
        self.assertEqual(inst.value, "https://example.com")

    def test_set_document_link_value(self):
        cf = CustomField.objects.create(
            name="Related", data_type=FIELD_DOCUMENTLINK, owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = [1, 2, 3]
        inst.save()
        self.assertEqual(inst.value, [1, 2, 3])

    def test_set_select_value(self):
        cf = CustomField.objects.create(
            name="Status",
            data_type=FIELD_SELECT,
            extra_data={"options": ["Draft", "Final", "Archived"]},
            owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = "Final"
        inst.save()
        self.assertEqual(inst.value, "Final")

    def test_select_invalid_option_raises_error(self):
        cf = CustomField.objects.create(
            name="Status",
            data_type=FIELD_SELECT,
            extra_data={"options": ["Draft", "Final"]},
            owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = "Invalid"
        with self.assertRaises(ValidationError):
            inst.save()

    def test_multiselect_invalid_option_raises_error(self):
        cf = CustomField.objects.create(
            name="Tags",
            data_type=FIELD_MULTISELECT,
            extra_data={"options": ["A", "B", "C"]},
            owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = ["A", "Z"]
        with self.assertRaises(ValidationError):
            inst.save()

    def test_multiselect_valid_options(self):
        cf = CustomField.objects.create(
            name="Tags",
            data_type=FIELD_MULTISELECT,
            extra_data={"options": ["A", "B", "C"]},
            owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = ["A", "C"]
        inst.save()
        self.assertEqual(inst.value, ["A", "C"])

    def test_string_max_length_validation(self):
        cf = CustomField.objects.create(
            name="Short",
            data_type=FIELD_STRING,
            extra_data={"max_length": 5},
            owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = "toolong"
        with self.assertRaises(ValidationError):
            inst.save()

    def test_url_validation(self):
        cf = CustomField.objects.create(
            name="Link", data_type=FIELD_URL, owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = "not-a-url"
        with self.assertRaises(ValidationError):
            inst.save()

    def test_document_link_must_be_list(self):
        cf = CustomField.objects.create(
            name="Links", data_type=FIELD_DOCUMENTLINK, owner=self.user,
        )
        inst = CustomFieldInstance(document=self.doc, field=cf)
        inst.value = "not-a-list"
        with self.assertRaises(ValidationError):
            inst.save()

    def test_unique_per_document(self):
        cf = CustomField.objects.create(
            name="Note", data_type=FIELD_STRING, owner=self.user,
        )
        CustomFieldInstance.objects.create(
            document=self.doc, field=cf, value_text="first",
        )
        with self.assertRaises(Exception):
            CustomFieldInstance.objects.create(
                document=self.doc, field=cf, value_text="second",
            )


class DocumentTypeCustomFieldTest(TestCase):
    """Tests for DocumentType <-> CustomField assignment."""

    def setUp(self):
        self.user = User.objects.create_user(username="dtcfuser", password="pass!")
        self.dt = DocumentType.objects.create(name="Invoice", owner=self.user)
        self.cf = CustomField.objects.create(
            name="Amount", data_type=FIELD_MONETARY, owner=self.user,
        )

    def test_assign_field_to_doctype(self):
        assignment = DocumentTypeCustomField.objects.create(
            document_type=self.dt,
            custom_field=self.cf,
            required=True,
        )
        self.assertEqual(str(assignment), "Invoice -> Amount")
        self.assertTrue(assignment.required)

    def test_unique_assignment(self):
        DocumentTypeCustomField.objects.create(
            document_type=self.dt, custom_field=self.cf,
        )
        with self.assertRaises(Exception):
            DocumentTypeCustomField.objects.create(
                document_type=self.dt, custom_field=self.cf,
            )


class CustomFieldAPITest(TestCase):
    """Tests for CustomField and CustomFieldInstance API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="cfapi", password="pass!")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_list_custom_fields(self):
        CustomField.objects.create(
            name="F1", data_type=FIELD_STRING, owner=self.user,
        )
        resp = self.client.get("/api/v1/custom-fields/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)

    def test_create_custom_field(self):
        resp = self.client.post("/api/v1/custom-fields/", {
            "name": "Invoice Amount",
            "data_type": "monetary",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "Invoice Amount")
        self.assertEqual(resp.data["data_type"], "monetary")

    def test_create_select_field_with_options(self):
        resp = self.client.post("/api/v1/custom-fields/", {
            "name": "Priority",
            "data_type": "select",
            "extra_data": {"options": ["Low", "Medium", "High"]},
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["extra_data"]["options"], ["Low", "Medium", "High"])

    def test_update_custom_field(self):
        cf = CustomField.objects.create(
            name="Old", data_type=FIELD_STRING, owner=self.user,
        )
        resp = self.client.patch(f"/api/v1/custom-fields/{cf.pk}/", {
            "name": "New",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "New")

    def test_delete_custom_field(self):
        cf = CustomField.objects.create(
            name="Del", data_type=FIELD_STRING, owner=self.user,
        )
        resp = self.client.delete(f"/api/v1/custom-fields/{cf.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_document_custom_fields_nested_list(self):
        doc = Document.objects.create(
            title="Test", owner=self.user, filename="o/cfapi1.txt",
        )
        cf = CustomField.objects.create(
            name="Note", data_type=FIELD_STRING, owner=self.user,
        )
        CustomFieldInstance.objects.create(
            document=doc, field=cf, value_text="hello",
        )
        resp = self.client.get(f"/api/v1/documents/{doc.pk}/custom-fields/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["field_name"], "Note")
        self.assertEqual(resp.data[0]["value"], "hello")

    def test_document_custom_fields_nested_create(self):
        doc = Document.objects.create(
            title="Test", owner=self.user, filename="o/cfapi2.txt",
        )
        cf = CustomField.objects.create(
            name="Count", data_type=FIELD_INTEGER, owner=self.user,
        )
        resp = self.client.post(f"/api/v1/documents/{doc.pk}/custom-fields/", {
            "document": doc.pk,
            "field": cf.pk,
            "value": 42,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            CustomFieldInstance.objects.get(document=doc, field=cf).value_int,
            42,
        )

    def test_document_custom_fields_nested_delete(self):
        doc = Document.objects.create(
            title="Test", owner=self.user, filename="o/cfapi3.txt",
        )
        cf = CustomField.objects.create(
            name="X", data_type=FIELD_STRING, owner=self.user,
        )
        inst = CustomFieldInstance.objects.create(
            document=doc, field=cf, value_text="bye",
        )
        resp = self.client.delete(
            f"/api/v1/documents/{doc.pk}/custom-fields/{inst.pk}/",
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomFieldInstance.objects.filter(pk=inst.pk).exists())

    def test_bulk_set_custom_fields(self):
        doc1 = Document.objects.create(
            title="D1", owner=self.user, filename="o/bulk_cf1.txt",
        )
        doc2 = Document.objects.create(
            title="D2", owner=self.user, filename="o/bulk_cf2.txt",
        )
        cf = CustomField.objects.create(
            name="Status", data_type=FIELD_STRING, owner=self.user,
        )
        resp = self.client.post("/api/v1/bulk-set-custom-fields/", {
            "document_ids": [doc1.pk, doc2.pk],
            "field_id": cf.pk,
            "value": "reviewed",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["updated"], 2)
        self.assertEqual(
            CustomFieldInstance.objects.get(document=doc1, field=cf).value_text,
            "reviewed",
        )
        self.assertEqual(
            CustomFieldInstance.objects.get(document=doc2, field=cf).value_text,
            "reviewed",
        )

    def test_doctype_custom_field_assignment_api(self):
        dt = DocumentType.objects.create(name="Invoice", owner=self.user)
        cf = CustomField.objects.create(
            name="Amount", data_type=FIELD_MONETARY, owner=self.user,
        )
        resp = self.client.post(
            f"/api/v1/document-types/{dt.pk}/custom-fields/",
            {"document_type": dt.pk, "custom_field": cf.pk, "required": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["field_name"], "Amount")
        self.assertTrue(resp.data["required"])

        # List assignments
        resp = self.client.get(f"/api/v1/document-types/{dt.pk}/custom-fields/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
