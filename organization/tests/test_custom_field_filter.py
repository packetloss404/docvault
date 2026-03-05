"""Tests for custom field filtering on documents."""

import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from documents.models import Document
from organization.models import CustomField, CustomFieldInstance
from organization.models.custom_field import FIELD_INTEGER, FIELD_STRING


class CustomFieldFilterTest(TestCase):
    """Tests for the custom field query parser in DocumentFilterSet."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="filtuser", password="pass!")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        self.doc1 = Document.objects.create(
            title="Invoice A", owner=self.user, filename="o/filt1.txt",
        )
        self.doc2 = Document.objects.create(
            title="Invoice B", owner=self.user, filename="o/filt2.txt",
        )
        self.doc3 = Document.objects.create(
            title="Contract", owner=self.user, filename="o/filt3.txt",
        )

        self.cf_invoice_num = CustomField.objects.create(
            name="invoice_number", data_type=FIELD_STRING, owner=self.user,
        )
        self.cf_amount = CustomField.objects.create(
            name="amount", data_type=FIELD_INTEGER, owner=self.user,
        )

        CustomFieldInstance.objects.create(
            document=self.doc1, field=self.cf_invoice_num, value_text="INV-2026-001",
        )
        CustomFieldInstance.objects.create(
            document=self.doc2, field=self.cf_invoice_num, value_text="INV-2026-002",
        )
        CustomFieldInstance.objects.create(
            document=self.doc1, field=self.cf_amount, value_int=500,
        )
        CustomFieldInstance.objects.create(
            document=self.doc2, field=self.cf_amount, value_int=1200,
        )

    def test_filter_by_custom_field_contains(self):
        query = json.dumps({
            "field_name": "invoice_number",
            "op": "contains",
            "value": "2026",
        })
        resp = self.client.get("/api/v1/documents/", {"custom_fields": query})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 2)

    def test_filter_by_custom_field_exact(self):
        query = json.dumps({
            "field_name": "invoice_number",
            "op": "exact",
            "value": "INV-2026-001",
        })
        resp = self.client.get("/api/v1/documents/", {"custom_fields": query})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Invoice A")

    def test_filter_by_custom_field_id(self):
        query = json.dumps({
            "field_id": self.cf_amount.pk,
            "op": "gte",
            "value": 1000,
        })
        resp = self.client.get("/api/v1/documents/", {"custom_fields": query})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Invoice B")

    def test_filter_has_custom_field(self):
        resp = self.client.get("/api/v1/documents/", {
            "has_custom_field": self.cf_invoice_num.pk,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        # doc1 and doc2 have invoice_number, doc3 does not
        self.assertEqual(len(results), 2)

    def test_filter_nonexistent_field_returns_empty(self):
        query = json.dumps({
            "field_name": "nonexistent",
            "op": "exact",
            "value": "x",
        })
        resp = self.client.get("/api/v1/documents/", {"custom_fields": query})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 0)

    def test_filter_invalid_json(self):
        resp = self.client.get("/api/v1/documents/", {
            "custom_fields": "not-json",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Should return all documents (filter is a no-op on invalid JSON)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 3)
