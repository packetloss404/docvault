"""Tests for the BarcodePlugin."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from processing.context import ProcessingContext
from processing.plugins.barcode import BarcodePlugin


class BarcodePluginTest(TestCase):
    """Tests for the BarcodePlugin processing plugin."""

    def setUp(self):
        self.plugin = BarcodePlugin()

    def test_name_and_order(self):
        """Plugin should have correct name and order."""
        self.assertEqual(self.plugin.name, "BarcodePlugin")
        self.assertEqual(self.plugin.order, 20)

    def test_can_run_pdf(self):
        """Should return True for PDF mime type with valid source."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        ctx = ProcessingContext(
            source_path=mock_path,
            mime_type="application/pdf",
        )
        self.assertTrue(self.plugin.can_run(ctx))

    def test_can_run_image(self):
        """Should return True for supported image mime types."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True

        for mime in ("image/png", "image/jpeg", "image/tiff", "image/bmp", "image/gif"):
            ctx = ProcessingContext(
                source_path=mock_path,
                mime_type=mime,
            )
            self.assertTrue(
                self.plugin.can_run(ctx),
                f"can_run should be True for {mime}",
            )

    def test_can_run_non_pdf(self):
        """Should return False for unsupported mime types."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        ctx = ProcessingContext(
            source_path=mock_path,
            mime_type="text/plain",
        )
        self.assertFalse(self.plugin.can_run(ctx))

    def test_can_run_no_source(self):
        """Should return False when source_path is None."""
        ctx = ProcessingContext(
            source_path=None,
            mime_type="application/pdf",
        )
        self.assertFalse(self.plugin.can_run(ctx))

    @override_settings(BARCODE_ENABLED=False)
    def test_can_run_disabled(self):
        """Should return False when barcode processing is disabled."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        ctx = ProcessingContext(
            source_path=mock_path,
            mime_type="application/pdf",
        )
        self.assertFalse(self.plugin.can_run(ctx))

    @patch("processing.barcode_utils.scan_pdf_for_barcodes")
    def test_process_no_barcodes(self, mock_scan):
        """Should succeed with no changes when no barcodes found."""
        mock_scan.return_value = {}

        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        ctx = ProcessingContext(
            source_path=mock_path,
            mime_type="application/pdf",
        )

        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertIsNone(ctx.override_asn)
        self.assertIsNone(ctx.override_tags)

    @patch("processing.barcode_utils.scan_pdf_for_barcodes")
    def test_process_extracts_asn(self, mock_scan):
        """Should set context.override_asn when ASN barcode found."""
        mock_scan.return_value = {
            0: [{"text": "ASN42", "format": "Code128"}],
        }

        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        ctx = ProcessingContext(
            source_path=mock_path,
            mime_type="application/pdf",
        )

        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertEqual(ctx.override_asn, 42)

    @override_settings(BARCODE_TAG_MAPPING={"^TAG:(.+)$": "\\1"})
    @patch("processing.barcode_utils.scan_pdf_for_barcodes")
    def test_process_extracts_tags(self, mock_scan):
        """Should populate context.override_tags when tag barcodes found."""
        mock_scan.return_value = {
            0: [{"text": "TAG:invoice", "format": "QRCode"}],
        }

        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        ctx = ProcessingContext(
            source_path=mock_path,
            mime_type="application/pdf",
        )

        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        # Tags should have been created via Tag.objects.get_or_create
        # and their PKs added to override_tags
        self.assertIsNotNone(ctx.override_tags)
        self.assertGreater(len(ctx.override_tags), 0)

    @patch("processing.barcode_utils.scan_pdf_for_barcodes")
    def test_process_skips_duplicate_asn(self, mock_scan):
        """Should not set override_asn when the ASN already exists in the DB."""
        from django.contrib.auth.models import User
        from documents.models import Document

        user = User.objects.create_user(
            username="asnuser", email="asn@example.com", password="pass123"
        )
        Document.objects.create(
            title="Existing Doc",
            filename="existing.pdf",
            archive_serial_number=42,
            owner=user,
        )

        mock_scan.return_value = {
            0: [{"text": "ASN42", "format": "Code128"}],
        }

        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        ctx = ProcessingContext(
            source_path=mock_path,
            mime_type="application/pdf",
        )

        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        # override_asn should remain None because ASN 42 already exists
        self.assertIsNone(ctx.override_asn)

    @patch("processing.barcode_utils.scan_pdf_for_barcodes")
    def test_process_skips_existing_asn_override(self, mock_scan):
        """Should not overwrite an existing override_asn on the context."""
        mock_scan.return_value = {
            0: [{"text": "ASN99", "format": "Code128"}],
        }

        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        ctx = ProcessingContext(
            source_path=mock_path,
            mime_type="application/pdf",
            override_asn=50,  # Already set by earlier plugin or API
        )

        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        # Should keep the existing override_asn value
        self.assertEqual(ctx.override_asn, 50)
