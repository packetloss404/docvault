"""Tests for search indexing (ES mocked)."""

from datetime import date
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from documents.models import Document, DocumentType
from organization.models import Correspondent, Tag

from search.client import reset_client
from search.indexing import document_to_index_body


class DocumentToIndexBodyTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="indexer", password="pass!")
        self.corr = Correspondent.objects.create(name="Acme Corp", owner=self.user)
        self.dtype = DocumentType.objects.create(name="Invoice", owner=self.user)
        self.tag1 = Tag.objects.create(name="Finance", owner=self.user)
        self.tag2 = Tag.objects.create(name="Urgent", owner=self.user)

    def test_basic_fields(self):
        doc = Document.objects.create(
            title="Test Invoice",
            content="This is the content of the invoice.",
            owner=self.user,
            filename="o/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf",
            checksum="abc123",
            page_count=3,
            language="en",
            created=date(2025, 6, 15),
        )
        body = document_to_index_body(doc)
        self.assertEqual(body["id"], doc.pk)
        self.assertEqual(body["title"], "Test Invoice")
        self.assertEqual(body["content"], "This is the content of the invoice.")
        self.assertEqual(body["original_filename"], "test.pdf")
        self.assertEqual(body["mime_type"], "application/pdf")
        self.assertEqual(body["checksum"], "abc123")
        self.assertEqual(body["page_count"], 3)
        self.assertEqual(body["language"], "en")
        self.assertEqual(body["owner_id"], self.user.pk)

    def test_correspondent_field(self):
        doc = Document.objects.create(
            title="With Correspondent",
            owner=self.user,
            filename="o/corr.pdf",
            correspondent=self.corr,
        )
        body = document_to_index_body(doc)
        self.assertEqual(body["correspondent"], "Acme Corp")
        self.assertEqual(body["correspondent_id"], self.corr.pk)

    def test_no_correspondent(self):
        doc = Document.objects.create(
            title="No Correspondent",
            owner=self.user,
            filename="o/nocorr.pdf",
        )
        body = document_to_index_body(doc)
        self.assertIsNone(body["correspondent"])
        self.assertIsNone(body["correspondent_id"])

    def test_document_type_field(self):
        doc = Document.objects.create(
            title="Typed Doc",
            owner=self.user,
            filename="o/typed.pdf",
            document_type=self.dtype,
        )
        body = document_to_index_body(doc)
        self.assertEqual(body["document_type"], "Invoice")
        self.assertEqual(body["document_type_id"], self.dtype.pk)

    def test_tags_field(self):
        doc = Document.objects.create(
            title="Tagged Doc",
            owner=self.user,
            filename="o/tagged.pdf",
        )
        doc.tags.add(self.tag1, self.tag2)
        body = document_to_index_body(doc)
        self.assertEqual(set(body["tags"]), {"Finance", "Urgent"})
        self.assertEqual(set(body["tag_ids"]), {self.tag1.pk, self.tag2.pk})

    def test_empty_content(self):
        doc = Document.objects.create(
            title="Empty Content",
            owner=self.user,
            filename="o/empty.pdf",
            content="",
        )
        body = document_to_index_body(doc)
        self.assertEqual(body["content"], "")

    def test_asn_field(self):
        doc = Document.objects.create(
            title="ASN Doc",
            owner=self.user,
            filename="o/asn.pdf",
            archive_serial_number=42,
        )
        body = document_to_index_body(doc)
        self.assertEqual(body["asn"], 42)

    def test_no_asn(self):
        doc = Document.objects.create(
            title="No ASN",
            owner=self.user,
            filename="o/noasn.pdf",
        )
        body = document_to_index_body(doc)
        self.assertIsNone(body["asn"])

    def test_custom_fields_empty(self):
        doc = Document.objects.create(
            title="No Custom Fields",
            owner=self.user,
            filename="o/nocf.pdf",
        )
        body = document_to_index_body(doc)
        self.assertEqual(body["custom_fields"], {})


class ClientConfigTest(TestCase):
    def setUp(self):
        reset_client()

    def tearDown(self):
        reset_client()

    @override_settings(ELASTICSEARCH_ENABLED=False)
    def test_get_client_disabled(self):
        from search.client import get_client
        client = get_client()
        self.assertIsNone(client)

    def test_get_index_name_default(self):
        from search.client import get_index_name
        name = get_index_name()
        self.assertEqual(name, "docvault")

    @override_settings(ELASTICSEARCH_INDEX="custom_index")
    def test_get_index_name_custom(self):
        from search.client import get_index_name
        name = get_index_name()
        self.assertEqual(name, "custom_index")

    @override_settings(ELASTICSEARCH_ENABLED=False)
    def test_create_index_when_disabled(self):
        from search.client import create_index
        result = create_index()
        self.assertFalse(result)

    @override_settings(ELASTICSEARCH_ENABLED=False)
    def test_delete_index_when_disabled(self):
        from search.client import delete_index
        result = delete_index()
        self.assertFalse(result)

    @override_settings(ELASTICSEARCH_ENABLED=False)
    def test_index_document_when_disabled(self):
        from search.indexing import index_document
        doc = MagicMock()
        result = index_document(doc)
        self.assertFalse(result)

    @override_settings(ELASTICSEARCH_ENABLED=False)
    def test_remove_document_when_disabled(self):
        from search.indexing import remove_document
        result = remove_document(1)
        self.assertFalse(result)

    @override_settings(ELASTICSEARCH_ENABLED=False)
    def test_bulk_index_when_disabled(self):
        from search.indexing import bulk_index_documents
        result = bulk_index_documents([])
        self.assertEqual(result, 0)
