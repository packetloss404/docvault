"""Tests for Sprint 6 document view endpoints: preview, download, versions."""

import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from documents.models import Document, DocumentFile, DocumentType, DocumentVersion
from storage.backends.local import LocalStorageBackend


class DocumentPreviewTests(TestCase):
    """Tests for the preview (thumbnail) endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="user", password="pass123!"
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.temp_dir = Path(tempfile.mkdtemp())

    @override_settings(STORAGE_BACKEND="local")
    def test_preview_returns_404_when_no_thumbnail(self):
        doc = Document.objects.create(
            title="No Thumb",
            owner=self.user,
            filename="originals/abc.txt",
        )
        resp = self.client.get(f"/api/v1/documents/{doc.pk}/preview/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(STORAGE_BACKEND="local")
    def test_preview_returns_thumbnail(self):
        """Thumbnail endpoint serves a WebP image when it exists."""
        from PIL import Image

        backend = LocalStorageBackend(base_dir=self.temp_dir)
        # Create a small thumbnail
        thumb_name = "thumbnails/test-thumb.webp"
        thumb_path = self.temp_dir / thumb_name
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (100, 140), color="red")
        img.save(str(thumb_path), "WEBP")

        doc = Document.objects.create(
            title="Has Thumb",
            owner=self.user,
            filename="originals/test.pdf",
            thumbnail_path=thumb_name,
        )

        with override_settings(STORAGE_DIR=self.temp_dir):
            resp = self.client.get(f"/api/v1/documents/{doc.pk}/preview/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "image/webp")
        self.assertIn("ETag", resp)
        self.assertIn("Cache-Control", resp)

    @override_settings(STORAGE_BACKEND="local")
    def test_preview_etag_returns_304(self):
        """If ETag matches, return 304 Not Modified."""
        import hashlib
        from PIL import Image

        thumb_name = "thumbnails/etag-test.webp"
        thumb_path = self.temp_dir / thumb_name
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (50, 70), color="blue")
        img.save(str(thumb_path), "WEBP")

        doc = Document.objects.create(
            title="ETag Test",
            owner=self.user,
            filename="originals/etag.pdf",
            thumbnail_path=thumb_name,
        )
        etag = hashlib.md5(thumb_name.encode()).hexdigest()

        with override_settings(STORAGE_DIR=self.temp_dir):
            resp = self.client.get(
                f"/api/v1/documents/{doc.pk}/preview/",
                HTTP_IF_NONE_MATCH=etag,
            )
        self.assertEqual(resp.status_code, 304)


class DocumentDownloadTests(TestCase):
    """Tests for the download endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="dluser", password="pass123!"
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.temp_dir = Path(tempfile.mkdtemp())

    @override_settings(STORAGE_BACKEND="local")
    def test_download_original(self):
        """Download the original file."""
        import hashlib

        # Store a file
        orig_name = "originals/dl-test.txt"
        orig_path = self.temp_dir / orig_name
        orig_path.parent.mkdir(parents=True, exist_ok=True)
        orig_path.write_text("Hello DocVault", encoding="utf-8")

        checksum = hashlib.sha256(b"Hello DocVault").hexdigest()

        doc = Document.objects.create(
            title="Download Test",
            owner=self.user,
            filename=orig_name,
            original_filename="test.txt",
            mime_type="text/plain",
            checksum=checksum,
        )

        with override_settings(STORAGE_DIR=self.temp_dir):
            resp = self.client.get(
                f"/api/v1/documents/{doc.pk}/download/?version=original"
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    @override_settings(STORAGE_BACKEND="local")
    def test_download_archive(self):
        """Download the archive version when available."""
        import hashlib

        orig_name = "originals/arch-test.txt"
        orig_path = self.temp_dir / orig_name
        orig_path.parent.mkdir(parents=True, exist_ok=True)
        orig_path.write_text("Original", encoding="utf-8")

        archive_name = "archive/arch-test.pdf"
        archive_path = self.temp_dir / archive_name
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_content = b"Fake PDF archive"
        archive_path.write_bytes(archive_content)

        archive_checksum = hashlib.sha256(archive_content).hexdigest()

        doc = Document.objects.create(
            title="Archive Test",
            owner=self.user,
            filename=orig_name,
            archive_filename=archive_name,
            original_filename="test.txt",
            mime_type="text/plain",
            checksum="abc",
            archive_checksum=archive_checksum,
        )

        with override_settings(STORAGE_DIR=self.temp_dir):
            resp = self.client.get(
                f"/api/v1/documents/{doc.pk}/download/?version=archive"
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "application/pdf")

    @override_settings(STORAGE_BACKEND="local")
    def test_download_missing_file_returns_404(self):
        doc = Document.objects.create(
            title="Missing File",
            owner=self.user,
            filename="originals/nonexistent.txt",
            original_filename="test.txt",
        )

        with override_settings(STORAGE_DIR=self.temp_dir):
            resp = self.client.get(f"/api/v1/documents/{doc.pk}/download/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(STORAGE_BACKEND="local")
    def test_download_checksum_mismatch_returns_500(self):
        """File integrity check failure returns 500."""
        orig_name = "originals/bad-checksum.txt"
        orig_path = self.temp_dir / orig_name
        orig_path.parent.mkdir(parents=True, exist_ok=True)
        orig_path.write_text("Content", encoding="utf-8")

        doc = Document.objects.create(
            title="Bad Checksum",
            owner=self.user,
            filename=orig_name,
            original_filename="test.txt",
            checksum="0000000000000000000000000000000000000000000000000000000000000000",
        )

        with override_settings(STORAGE_DIR=self.temp_dir):
            resp = self.client.get(f"/api/v1/documents/{doc.pk}/download/")
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentVersionTests(TestCase):
    """Tests for document version management endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="veruser", password="pass123!"
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.doc = Document.objects.create(
            title="Versioned Doc",
            owner=self.user,
            filename="originals/ver.txt",
            original_filename="ver.txt",
        )

    def test_list_versions_empty(self):
        resp = self.client.get(f"/api/v1/documents/{self.doc.pk}/versions/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_list_versions_with_data(self):
        doc_file = DocumentFile.objects.create(
            document=self.doc,
            filename="ver.txt",
            mime_type="text/plain",
            checksum="abc123",
        )
        DocumentVersion.objects.create(
            document=self.doc,
            version_number=1,
            comment="Initial version",
            is_active=True,
            file=doc_file,
        )
        resp = self.client.get(f"/api/v1/documents/{self.doc.pk}/versions/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["version_number"], 1)

    def test_activate_version(self):
        doc_file = DocumentFile.objects.create(
            document=self.doc,
            filename="v1.txt",
            mime_type="text/plain",
            checksum="a",
        )
        v1 = DocumentVersion.objects.create(
            document=self.doc, version_number=1,
            is_active=True, file=doc_file,
        )
        doc_file2 = DocumentFile.objects.create(
            document=self.doc,
            filename="v2.txt",
            mime_type="text/plain",
            checksum="b",
        )
        v2 = DocumentVersion.objects.create(
            document=self.doc, version_number=2,
            is_active=False, file=doc_file2,
        )

        resp = self.client.post(
            f"/api/v1/documents/{self.doc.pk}/versions/{v2.pk}/activate/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["is_active"])

        v1.refresh_from_db()
        v2.refresh_from_db()
        self.assertFalse(v1.is_active)
        self.assertTrue(v2.is_active)

    def test_activate_nonexistent_version_returns_404(self):
        resp = self.client.post(
            f"/api/v1/documents/{self.doc.pk}/versions/99999/activate/"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_upload_new_version(self):
        """Upload a new file to create a new version."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile("v1.txt", b"version 1 content", content_type="text/plain")
        resp = self.client.post(
            f"/api/v1/documents/{self.doc.pk}/files/",
            {"document": file, "comment": "First version"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["version_number"], 1)
        self.assertEqual(resp.data["comment"], "First version")
        self.assertTrue(resp.data["is_active"])

        # Upload a second version
        file2 = SimpleUploadedFile("v2.txt", b"version 2 content", content_type="text/plain")
        resp2 = self.client.post(
            f"/api/v1/documents/{self.doc.pk}/files/",
            {"document": file2, "comment": "Second version"},
            format="multipart",
        )
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp2.data["version_number"], 2)
        self.assertTrue(resp2.data["is_active"])

        # First version should now be inactive
        versions = DocumentVersion.objects.filter(document=self.doc)
        self.assertEqual(versions.count(), 2)
        self.assertFalse(versions.get(version_number=1).is_active)
        self.assertTrue(versions.get(version_number=2).is_active)

    def test_upload_version_no_file_returns_400(self):
        resp = self.client.post(
            f"/api/v1/documents/{self.doc.pk}/files/",
            {},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class NonDestructiveStorageTests(TestCase):
    """Tests for non-destructive storage mode in the StorePlugin."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    @override_settings(STORAGE_BACKEND="local", NON_DESTRUCTIVE_MODE=True)
    def test_store_plugin_saves_archive(self):
        """When archive_path is set and non-destructive mode is on, archive is stored."""
        from processing.context import ProcessingContext
        from processing.plugins.store import StorePlugin

        user = User.objects.create_user(username="storetest", password="pass!")

        # Create source and archive files
        source = self.temp_dir / "original.txt"
        source.write_text("Original content", encoding="utf-8")

        archive = self.temp_dir / "archive.pdf"
        archive.write_bytes(b"Fake PDF archive content")

        ctx = ProcessingContext(
            source_path=source,
            original_filename="original.txt",
            mime_type="text/plain",
            title="Store Test",
            content="Original content",
            checksum="abc123unique",
            language="en",
            archive_path=archive,
            user_id=user.pk,
        )

        plugin = StorePlugin()

        with override_settings(STORAGE_DIR=self.temp_dir):
            result = plugin.process(ctx)

        self.assertTrue(result.success)
        self.assertIsNotNone(ctx.document_id)

        doc = Document.objects.get(pk=ctx.document_id)
        self.assertTrue(doc.filename.startswith("originals/"))
        self.assertTrue(doc.archive_filename.startswith("archive/"))
        self.assertNotEqual(doc.archive_checksum, "")

    @override_settings(STORAGE_BACKEND="local", NON_DESTRUCTIVE_MODE=False)
    def test_store_plugin_skips_archive_when_disabled(self):
        """When non-destructive mode is off, archive is not stored."""
        from processing.context import ProcessingContext
        from processing.plugins.store import StorePlugin

        user = User.objects.create_user(username="noarchive", password="pass!")

        source = self.temp_dir / "original2.txt"
        source.write_text("Content", encoding="utf-8")

        archive = self.temp_dir / "archive2.pdf"
        archive.write_bytes(b"Archive")

        ctx = ProcessingContext(
            source_path=source,
            original_filename="original2.txt",
            mime_type="text/plain",
            title="No Archive",
            content="Content",
            checksum="def456unique",
            language="en",
            archive_path=archive,
            user_id=user.pk,
        )

        plugin = StorePlugin()

        with override_settings(STORAGE_DIR=self.temp_dir):
            result = plugin.process(ctx)

        self.assertTrue(result.success)
        doc = Document.objects.get(pk=ctx.document_id)
        self.assertEqual(doc.archive_filename, "")
