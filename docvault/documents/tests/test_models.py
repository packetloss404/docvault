"""Tests for document models."""

import uuid
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from documents.models import (
    Document,
    DocumentFile,
    DocumentPage,
    DocumentType,
    DocumentVersion,
)


class DocumentTypeModelTest(TestCase):
    """Tests for DocumentType model."""

    def test_create_document_type(self):
        dt = DocumentType.objects.create(name="Invoice")
        self.assertEqual(dt.name, "Invoice")
        self.assertEqual(dt.slug, "invoice")

    def test_auto_slug_generation(self):
        dt = DocumentType.objects.create(name="Tax Return 2024")
        self.assertEqual(dt.slug, "tax-return-2024")

    def test_explicit_slug(self):
        dt = DocumentType.objects.create(name="Invoice", slug="inv")
        self.assertEqual(dt.slug, "inv")

    def test_unique_name(self):
        DocumentType.objects.create(name="Invoice")
        with self.assertRaises(IntegrityError):
            DocumentType.objects.create(name="Invoice", slug="invoice-2")

    def test_unique_slug(self):
        DocumentType.objects.create(name="Invoice", slug="invoice")
        with self.assertRaises(IntegrityError):
            DocumentType.objects.create(name="Invoice 2", slug="invoice")

    def test_str(self):
        dt = DocumentType.objects.create(name="Invoice")
        self.assertEqual(str(dt), "Invoice")

    def test_retention_fields(self):
        dt = DocumentType.objects.create(
            name="Temp",
            trash_time_period=30,
            trash_time_unit="days",
            delete_time_period=90,
            delete_time_unit="days",
        )
        self.assertEqual(dt.trash_time_period, 30)
        self.assertEqual(dt.delete_time_unit, "days")

    def test_matching_defaults(self):
        dt = DocumentType.objects.create(name="Test")
        self.assertEqual(dt.matching_algorithm, 0)  # MATCH_NONE
        self.assertTrue(dt.is_insensitive)
        self.assertEqual(dt.match, "")

    def test_ordering(self):
        DocumentType.objects.create(name="Zeta")
        DocumentType.objects.create(name="Alpha")
        types = list(DocumentType.objects.values_list("name", flat=True))
        self.assertEqual(types, ["Alpha", "Zeta"])


class DocumentModelTest(TestCase):
    """Tests for Document model."""

    def setUp(self):
        self.user = User.objects.create_user("testuser", password="testpass")
        self.doc_type = DocumentType.objects.create(name="Invoice")

    def test_create_document(self):
        doc = Document.objects.create(
            title="Test Invoice",
            filename="test_invoice.pdf",
            owner=self.user,
        )
        self.assertEqual(doc.title, "Test Invoice")
        self.assertIsNotNone(doc.uuid)
        self.assertIsInstance(doc.uuid, uuid.UUID)

    def test_uuid_unique(self):
        doc1 = Document.objects.create(title="Doc 1", filename="d1.pdf")
        doc2 = Document.objects.create(title="Doc 2", filename="d2.pdf")
        self.assertNotEqual(doc1.uuid, doc2.uuid)

    def test_default_dates(self):
        doc = Document.objects.create(title="Test", filename="test.pdf")
        self.assertEqual(doc.created, date.today())
        self.assertIsNotNone(doc.added)

    def test_document_type_relationship(self):
        doc = Document.objects.create(
            title="Test Invoice",
            filename="inv.pdf",
            document_type=self.doc_type,
        )
        self.assertEqual(doc.document_type, self.doc_type)
        self.assertIn(doc, self.doc_type.documents.all())

    def test_document_type_nullification(self):
        doc = Document.objects.create(
            title="Test",
            filename="test.pdf",
            document_type=self.doc_type,
        )
        self.doc_type.delete()
        doc.refresh_from_db()
        self.assertIsNone(doc.document_type)

    def test_archive_serial_number_unique(self):
        Document.objects.create(title="Doc 1", filename="d1.pdf", archive_serial_number=1)
        with self.assertRaises(IntegrityError):
            Document.objects.create(title="Doc 2", filename="d2.pdf", archive_serial_number=1)

    def test_archive_serial_number_null_allowed(self):
        doc1 = Document.objects.create(title="Doc 1", filename="d1.pdf")
        doc2 = Document.objects.create(title="Doc 2", filename="d2.pdf")
        self.assertIsNone(doc1.archive_serial_number)
        self.assertIsNone(doc2.archive_serial_number)

    def test_filename_unique(self):
        Document.objects.create(title="Doc 1", filename="same.pdf")
        with self.assertRaises(IntegrityError):
            Document.objects.create(title="Doc 2", filename="same.pdf")

    def test_soft_delete_inherited(self):
        doc = Document.objects.create(title="Test", filename="test.pdf")
        doc.soft_delete()
        self.assertTrue(doc.is_deleted)
        self.assertEqual(Document.objects.count(), 0)
        self.assertEqual(Document.all_objects.count(), 1)

    def test_ordering(self):
        Document.objects.create(
            title="Old", filename="old.pdf", created=date(2024, 1, 1)
        )
        Document.objects.create(
            title="New", filename="new.pdf", created=date(2024, 12, 1)
        )
        docs = list(Document.objects.values_list("title", flat=True))
        self.assertEqual(docs, ["New", "Old"])

    def test_str(self):
        doc = Document.objects.create(title="My Document", filename="my.pdf")
        self.assertEqual(str(doc), "My Document")

    def test_content_default_empty(self):
        doc = Document.objects.create(title="Test", filename="test.pdf")
        self.assertEqual(doc.content, "")

    def test_language_default(self):
        doc = Document.objects.create(title="Test", filename="test.pdf")
        self.assertEqual(doc.language, "en")


class DocumentFileModelTest(TestCase):
    """Tests for DocumentFile model."""

    def setUp(self):
        self.doc = Document.objects.create(title="Test", filename="test.pdf")

    def test_create_document_file(self):
        f = SimpleUploadedFile("test.pdf", b"fake pdf content", content_type="application/pdf")
        df = DocumentFile.objects.create(
            document=self.doc,
            file=f,
            filename="test.pdf",
            mime_type="application/pdf",
            checksum="abc123",
            size=100,
        )
        self.assertEqual(df.filename, "test.pdf")
        self.assertEqual(df.document, self.doc)

    def test_cascade_delete(self):
        f = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        DocumentFile.objects.create(
            document=self.doc,
            file=f,
            filename="test.pdf",
            mime_type="application/pdf",
            checksum="abc123",
        )
        self.doc.hard_delete()
        self.assertEqual(DocumentFile.objects.count(), 0)

    def test_str(self):
        f = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        df = DocumentFile.objects.create(
            document=self.doc,
            file=f,
            filename="report.pdf",
            mime_type="application/pdf",
            checksum="abc123",
        )
        self.assertEqual(str(df), "Test - report.pdf")

    def test_related_name(self):
        f = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        df = DocumentFile.objects.create(
            document=self.doc,
            file=f,
            filename="test.pdf",
            mime_type="application/pdf",
            checksum="abc123",
        )
        self.assertIn(df, self.doc.files.all())


class DocumentVersionModelTest(TestCase):
    """Tests for DocumentVersion model."""

    def setUp(self):
        self.doc = Document.objects.create(title="Test", filename="test.pdf")

    def test_create_version(self):
        v = DocumentVersion.objects.create(
            document=self.doc,
            version_number=1,
            comment="Initial version",
            is_active=True,
        )
        self.assertEqual(v.version_number, 1)
        self.assertTrue(v.is_active)

    def test_unique_version_number_per_document(self):
        DocumentVersion.objects.create(document=self.doc, version_number=1)
        with self.assertRaises(IntegrityError):
            DocumentVersion.objects.create(document=self.doc, version_number=1)

    def test_different_documents_same_version_number(self):
        doc2 = Document.objects.create(title="Test 2", filename="test2.pdf")
        DocumentVersion.objects.create(document=self.doc, version_number=1)
        DocumentVersion.objects.create(document=doc2, version_number=1)
        self.assertEqual(DocumentVersion.objects.count(), 2)

    def test_ordering(self):
        DocumentVersion.objects.create(document=self.doc, version_number=1)
        DocumentVersion.objects.create(document=self.doc, version_number=2)
        DocumentVersion.objects.create(document=self.doc, version_number=3)
        versions = list(
            self.doc.version_history.values_list("version_number", flat=True)
        )
        self.assertEqual(versions, [3, 2, 1])

    def test_str(self):
        v = DocumentVersion.objects.create(document=self.doc, version_number=1)
        self.assertEqual(str(v), "Test v1")

    def test_cascade_delete(self):
        DocumentVersion.objects.create(document=self.doc, version_number=1)
        self.doc.hard_delete()
        self.assertEqual(DocumentVersion.objects.count(), 0)


class DocumentPageModelTest(TestCase):
    """Tests for DocumentPage model."""

    def setUp(self):
        self.doc = Document.objects.create(title="Test", filename="test.pdf")

    def test_create_page(self):
        page = DocumentPage.objects.create(
            document=self.doc,
            page_number=1,
            content="Page 1 OCR text",
        )
        self.assertEqual(page.page_number, 1)
        self.assertEqual(page.content, "Page 1 OCR text")

    def test_unique_page_number_per_document(self):
        DocumentPage.objects.create(document=self.doc, page_number=1)
        with self.assertRaises(IntegrityError):
            DocumentPage.objects.create(document=self.doc, page_number=1)

    def test_ordering(self):
        DocumentPage.objects.create(document=self.doc, page_number=3)
        DocumentPage.objects.create(document=self.doc, page_number=1)
        DocumentPage.objects.create(document=self.doc, page_number=2)
        pages = list(self.doc.pages.values_list("page_number", flat=True))
        self.assertEqual(pages, [1, 2, 3])

    def test_str(self):
        page = DocumentPage.objects.create(document=self.doc, page_number=5)
        self.assertEqual(str(page), "Test - Page 5")

    def test_cascade_delete(self):
        DocumentPage.objects.create(document=self.doc, page_number=1)
        self.doc.hard_delete()
        self.assertEqual(DocumentPage.objects.count(), 0)

    def test_related_name(self):
        page = DocumentPage.objects.create(document=self.doc, page_number=1)
        self.assertIn(page, self.doc.pages.all())
