import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from guardian.shortcuts import assign_perm
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from documents.models import Document, DocumentType
from organization.models import Correspondent, Tag
from search.filter_rules import apply_filter_rules
from search.query import _prepend_pinned, build_search_query


class FilterRulesTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("filter-owner")
        self.other = User.objects.create_user("filter-other")
        self.invoice = Document.objects.create(
            title="Invoice 123", content="Paid in full", created="2026-01-15", owner=self.owner,
            document_type=DocumentType.objects.create(name="Invoices"),
            correspondent=Correspondent.objects.create(name="Acme Corp"), language="en",
        )
        self.invoice.tags.add(Tag.objects.create(name="Finance"), Tag.objects.create(name="Approved"))
        self.other_document = Document.objects.create(title="Letter", owner=self.owner, created="2025-01-01")

    def apply(self, rules):
        return list(apply_filter_rules(Document.objects.all(), json.dumps(rules)).values_list("id", flat=True))

    def test_all_text_fields_and_operators(self):
        rules = [
            {"field": "title", "operator": "starts_with", "value": "invoice"},
            {"field": "content", "operator": "contains", "value": "IN FULL"},
            {"field": "document_type", "operator": "equals", "value": "invoices"},
            {"field": "correspondent", "operator": "starts_with", "value": "acme"},
            {"field": "tags", "operator": "equals", "value": "finance"},
            {"field": "tags", "operator": "equals", "value": "approved"},
            {"field": "language", "operator": "equals", "value": "en"},
        ]
        self.assertEqual(self.apply(rules), [self.invoice.id])

    def test_date_rules_and_exclusive_boundaries(self):
        rules = [
            {"field": "created", "operator": "date_after", "value": "2026-01-01"},
            {"field": "created", "operator": "date_before", "value": "2026-02-01"},
        ]
        self.assertEqual(self.apply(rules), [self.invoice.id])
        rules[0]["value"] = "2026-01-15"
        self.assertEqual(self.apply(rules), [])

    def test_untrusted_or_malformed_rules_are_rejected(self):
        invalid = [
            "not json", "null", "{}", "[null]", "[[]]",
            json.dumps([{"field": "owner__is_superuser", "operator": "equals", "value": "true"}]),
            json.dumps([{"field": "title", "operator": "regex", "value": ".*"}]),
            json.dumps([{"field": "created", "operator": "contains", "value": "2026"}]),
            json.dumps([{"field": "created", "operator": "date_after", "value": "2026-02-30"}]),
            json.dumps([{"field": [], "operator": "equals", "value": "a"}]),
            json.dumps([{"field": "title", "operator": "equals", "value": " "}]),
            json.dumps([{"field": "title", "operator": "equals", "value": "a"}] * 21),
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                apply_filter_rules(Document.objects.all(), value)

    @patch("search.views.execute_search", return_value={"results": [], "count": 0})
    def test_api_filters_before_es_and_preserves_object_permissions(self, search):
        shared = Document.objects.create(title="Invoice shared", owner=self.other)
        assign_perm("documents.view_document", self.owner, shared)
        Document.objects.create(title="Invoice private", owner=self.other)
        client = APIClient()
        client.force_authenticate(self.owner)
        response = client.get("/api/v1/search/", {
            "filter_rules": json.dumps([{"field": "title", "operator": "starts_with", "value": "Invoice"}]),
        })
        self.assertEqual(response.status_code, 200)
        ids = search.call_args.kwargs["document_ids"]
        self.assertCountEqual(ids, [self.invoice.id, shared.id])
        body = build_search_query("", document_ids=ids)
        self.assertIn({"terms": {"id": ids}}, body["query"]["bool"]["filter"])
        pinned = _prepend_pinned({"results": [], "count": 0}, [self.other_document.id], set(), ids)
        self.assertEqual(pinned["results"], [])

    @patch("search.views.execute_search")
    def test_api_invalid_rules_return_400_instead_of_ignoring_them(self, search):
        client = APIClient()
        client.force_authenticate(self.owner)
        response = client.get("/api/v1/search/", {"filter_rules": "{invalid"})
        self.assertEqual(response.status_code, 400)
        search.assert_not_called()

    @patch("search.views.execute_search", return_value={"results": [], "count": 0})
    def test_staff_search_still_applies_rules(self, search):
        self.owner.is_staff = True
        self.owner.save(update_fields=["is_staff"])
        client = APIClient()
        client.force_authenticate(self.owner)
        response = client.get("/api/v1/search/", {
            "filter_rules": json.dumps([{"field": "title", "operator": "equals", "value": "letter"}]),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(search.call_args.kwargs["document_ids"], [self.other_document.id])
