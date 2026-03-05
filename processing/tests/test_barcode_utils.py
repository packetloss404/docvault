"""Tests for barcode scanning and processing utilities."""

from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from documents.models import Document
from processing.barcode_utils import (
    extract_asn,
    extract_tags,
    find_separator_pages,
    get_barcode_settings,
    get_next_asn,
    scan_page_for_barcodes,
    split_pdf_at_separators,
)


class GetBarcodeSettingsTest(TestCase):
    """Tests for the get_barcode_settings function."""

    def test_default_settings(self):
        """Default settings should return expected values."""
        conf = get_barcode_settings()
        self.assertEqual(conf["separator_barcode"], "PATCH T")
        self.assertEqual(conf["asn_prefix"], "ASN")
        self.assertEqual(conf["dpi"], 300)
        self.assertEqual(conf["max_pages"], 5)
        self.assertEqual(conf["tag_mapping"], {})
        self.assertFalse(conf["retain_separator_pages"])
        self.assertTrue(conf["enabled"])

    @override_settings(
        BARCODE_SEPARATOR="CUSTOM_SEP",
        BARCODE_ASN_PREFIX="DOC",
        BARCODE_DPI=150,
        BARCODE_MAX_PAGES=10,
        BARCODE_TAG_MAPPING={"^TAG:(.+)$": "\\1"},
        BARCODE_RETAIN_SEPARATOR_PAGES=True,
        BARCODE_ENABLED=True,
    )
    def test_custom_settings(self):
        """Custom settings should override defaults."""
        conf = get_barcode_settings()
        self.assertEqual(conf["separator_barcode"], "CUSTOM_SEP")
        self.assertEqual(conf["asn_prefix"], "DOC")
        self.assertEqual(conf["dpi"], 150)
        self.assertEqual(conf["max_pages"], 10)
        self.assertEqual(conf["tag_mapping"], {"^TAG:(.+)$": "\\1"})
        self.assertTrue(conf["retain_separator_pages"])
        self.assertTrue(conf["enabled"])

    @override_settings(BARCODE_ENABLED=False)
    def test_disabled(self):
        """When BARCODE_ENABLED is False, enabled key should be False."""
        conf = get_barcode_settings()
        self.assertFalse(conf["enabled"])


class ExtractAsnTest(TestCase):
    """Tests for the extract_asn function."""

    def test_extract_asn_basic(self):
        """Should extract numeric ASN from barcode with ASN prefix."""
        page_barcodes = {0: [{"text": "ASN123", "format": "Code128"}]}
        result = extract_asn(page_barcodes)
        self.assertEqual(result, 123)

    def test_extract_asn_with_space(self):
        """Should extract ASN when there is a space after the prefix."""
        page_barcodes = {0: [{"text": "ASN 456", "format": "Code128"}]}
        result = extract_asn(page_barcodes)
        self.assertEqual(result, 456)

    @override_settings(BARCODE_ASN_PREFIX="DOC")
    def test_extract_asn_custom_prefix(self):
        """Should use custom ASN prefix from settings."""
        page_barcodes = {0: [{"text": "DOC789", "format": "Code128"}]}
        result = extract_asn(page_barcodes, asn_prefix="DOC")
        self.assertEqual(result, 789)

    def test_extract_asn_no_match(self):
        """Should return None when no barcodes match the ASN pattern."""
        page_barcodes = {
            0: [
                {"text": "PATCH T", "format": "Code128"},
                {"text": "TAG:invoice", "format": "QRCode"},
            ]
        }
        result = extract_asn(page_barcodes)
        self.assertIsNone(result)

    def test_extract_asn_empty(self):
        """Should return None for empty page_barcodes."""
        result = extract_asn({})
        self.assertIsNone(result)

    def test_extract_asn_first_match(self):
        """Should return the first ASN found when scanning pages in order."""
        page_barcodes = {
            0: [{"text": "ASN100", "format": "Code128"}],
            1: [{"text": "ASN200", "format": "Code128"}],
        }
        result = extract_asn(page_barcodes)
        self.assertEqual(result, 100)


class ExtractTagsTest(TestCase):
    """Tests for the extract_tags function."""

    def test_extract_tags_basic(self):
        """Should extract tag name using capture group replacement."""
        page_barcodes = {0: [{"text": "TAG:invoice", "format": "QRCode"}]}
        mapping = {"^TAG:(.+)$": "\\1"}
        result = extract_tags(page_barcodes, tag_mapping=mapping)
        self.assertEqual(result, {"invoice"})

    def test_extract_tags_multiple(self):
        """Should extract multiple tags from multiple barcodes."""
        page_barcodes = {
            0: [
                {"text": "TAG:invoice", "format": "QRCode"},
                {"text": "TAG:receipt", "format": "QRCode"},
            ],
            1: [
                {"text": "TAG:urgent", "format": "Code128"},
            ],
        }
        mapping = {"^TAG:(.+)$": "\\1"}
        result = extract_tags(page_barcodes, tag_mapping=mapping)
        self.assertEqual(result, {"invoice", "receipt", "urgent"})

    def test_extract_tags_no_mapping(self):
        """Should return empty set when tag mapping is empty."""
        page_barcodes = {0: [{"text": "TAG:invoice", "format": "QRCode"}]}
        result = extract_tags(page_barcodes, tag_mapping={})
        self.assertEqual(result, set())

    def test_extract_tags_no_match(self):
        """Should return empty set when barcodes don't match any patterns."""
        page_barcodes = {0: [{"text": "RANDOM_DATA", "format": "Code128"}]}
        mapping = {"^TAG:(.+)$": "\\1"}
        result = extract_tags(page_barcodes, tag_mapping=mapping)
        self.assertEqual(result, set())

    def test_extract_tags_fixed_mapping(self):
        """Should support fixed tag names (no capture group replacement)."""
        page_barcodes = {
            0: [{"text": "INVOICE", "format": "Code128"}],
        }
        mapping = {"^INVOICE$": "invoice"}
        result = extract_tags(page_barcodes, tag_mapping=mapping)
        self.assertEqual(result, {"invoice"})


class FindSeparatorPagesTest(TestCase):
    """Tests for the find_separator_pages function."""

    def test_find_separators(self):
        """Should find pages containing separator barcodes."""
        page_barcodes = {
            0: [{"text": "ASN123", "format": "Code128"}],
            1: [{"text": "PATCH T", "format": "Code128"}],
            2: [{"text": "Some data", "format": "QRCode"}],
            3: [{"text": "PATCH T", "format": "Code128"}],
        }
        result = find_separator_pages(page_barcodes)
        self.assertEqual(result, [1, 3])

    def test_find_separators_none(self):
        """Should return empty list when no separator barcodes exist."""
        page_barcodes = {
            0: [{"text": "ASN123", "format": "Code128"}],
            1: [{"text": "Some data", "format": "QRCode"}],
        }
        result = find_separator_pages(page_barcodes)
        self.assertEqual(result, [])

    def test_find_separators_custom_string(self):
        """Should support custom separator strings."""
        page_barcodes = {
            0: [{"text": "SPLIT_HERE", "format": "Code128"}],
            1: [{"text": "content", "format": "Code128"}],
        }
        result = find_separator_pages(page_barcodes, separator_string="SPLIT_HERE")
        self.assertEqual(result, [0])

    def test_find_separators_sorted(self):
        """Should return page numbers in sorted order."""
        page_barcodes = {
            5: [{"text": "PATCH T", "format": "Code128"}],
            2: [{"text": "PATCH T", "format": "Code128"}],
            8: [{"text": "PATCH T", "format": "Code128"}],
        }
        result = find_separator_pages(page_barcodes)
        self.assertEqual(result, [2, 5, 8])


class SplitPdfAtSeparatorsTest(TestCase):
    """Tests for the split_pdf_at_separators function."""

    def test_no_separators(self):
        """Should return the original path when there are no separators."""
        pdf_path = Path("/tmp/test.pdf")
        result = split_pdf_at_separators(pdf_path, [])
        self.assertEqual(result, [pdf_path])

    def test_split_with_mock(self):
        """Should split PDF into segments at separator pages."""
        import sys

        # Create a mock pikepdf module
        mock_pikepdf = MagicMock()

        # Simulate a 5-page PDF: pages 0,1,2,3,4 with separator at page 2
        mock_src_pdf = MagicMock()
        mock_pages = [MagicMock(name=f"page_{i}") for i in range(5)]
        mock_src_pdf.pages = mock_pages

        mock_out_pdf = MagicMock()
        mock_out_pdf.pages = []

        mock_pikepdf.open.return_value = mock_src_pdf
        mock_pikepdf.new.return_value = mock_out_pdf

        # Remove pikepdf from module cache to force re-import inside function
        saved = sys.modules.pop("pikepdf", None)
        try:
            with patch.dict("sys.modules", {"pikepdf": mock_pikepdf}):
                pdf_path = Path("/tmp/test.pdf")
                # With separator at page 2, we expect segments:
                # [0,1] and [3,4] (separator page 2 excluded)
                result = split_pdf_at_separators(pdf_path, [2])

                # pikepdf.open should have been called
                mock_pikepdf.open.assert_called_once_with(str(pdf_path))
                # Should return output paths (not just the original)
                self.assertGreater(len(result), 0)
        finally:
            if saved is not None:
                sys.modules["pikepdf"] = saved

    def test_split_without_pikepdf(self):
        """Should return original path when pikepdf is not installed."""
        import sys

        # Setting a module to None in sys.modules causes ImportError on import
        saved = sys.modules.pop("pikepdf", None)
        try:
            with patch.dict("sys.modules", {"pikepdf": None}):
                pdf_path = Path("/tmp/test.pdf")
                result = split_pdf_at_separators(pdf_path, [2])
            self.assertEqual(result, [pdf_path])
        finally:
            if saved is not None:
                sys.modules["pikepdf"] = saved

    def test_retain_separator_pages(self):
        """When retain_separator_pages is True, separator pages are kept in output."""
        import sys

        # Create a mock pikepdf module
        mock_pikepdf = MagicMock()

        # Simulate a 4-page PDF with separator at page 1
        mock_src_pdf = MagicMock()
        mock_pages = [MagicMock(name=f"page_{i}") for i in range(4)]
        mock_src_pdf.pages = mock_pages

        mock_out_pdf = MagicMock()
        mock_out_pdf.pages = []

        mock_pikepdf.open.return_value = mock_src_pdf
        mock_pikepdf.new.return_value = mock_out_pdf

        saved = sys.modules.pop("pikepdf", None)
        try:
            with patch.dict("sys.modules", {"pikepdf": mock_pikepdf}):
                pdf_path = Path("/tmp/test.pdf")
                result = split_pdf_at_separators(
                    pdf_path, [1], retain_separators=True
                )
                # With retain_separators=True and separator at page 1 on a 4-page doc:
                # Segments: (0,1), (1,2) for separator retained, (2,4)
                # This should produce output files (not just the original)
                self.assertIsInstance(result, list)
                self.assertGreater(len(result), 0)
                # pikepdf.new should have been called for each segment
                self.assertTrue(mock_pikepdf.new.called)
        finally:
            if saved is not None:
                sys.modules["pikepdf"] = saved


class GetNextAsnTest(TestCase):
    """Tests for the get_next_asn function."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_first_asn(self):
        """Should return 1 when no documents exist."""
        result = get_next_asn()
        self.assertEqual(result, 1)

    def test_next_after_existing(self):
        """Should return max ASN + 1."""
        Document.objects.create(
            title="Doc 1",
            filename="doc1.pdf",
            archive_serial_number=5,
            owner=self.user,
        )
        Document.objects.create(
            title="Doc 2",
            filename="doc2.pdf",
            archive_serial_number=10,
            owner=self.user,
        )
        result = get_next_asn()
        self.assertEqual(result, 11)

    def test_includes_soft_deleted(self):
        """Should include soft-deleted documents when finding max ASN."""
        doc = Document.objects.create(
            title="Doc Deleted",
            filename="doc_deleted.pdf",
            archive_serial_number=20,
            owner=self.user,
        )
        doc.soft_delete()

        # Active doc with lower ASN
        Document.objects.create(
            title="Doc Active",
            filename="doc_active.pdf",
            archive_serial_number=5,
            owner=self.user,
        )

        result = get_next_asn()
        # Should be 21 because soft-deleted doc with ASN 20 is included
        self.assertEqual(result, 21)


class ScanPageForBarcodesTest(TestCase):
    """Tests for the scan_page_for_barcodes function."""

    def test_scan_with_mock_zxing(self):
        """Should return barcode results from zxing-cpp."""
        mock_result_1 = MagicMock()
        mock_result_1.text = "ASN123"
        mock_result_1.format.name = "Code128"

        mock_result_2 = MagicMock()
        mock_result_2.text = "PATCH T"
        mock_result_2.format.name = "Code128"

        mock_zxingcpp = MagicMock()
        mock_zxingcpp.read_barcodes.return_value = [mock_result_1, mock_result_2]

        mock_image = MagicMock()

        with patch.dict("sys.modules", {"zxingcpp": mock_zxingcpp}):
            result = scan_page_for_barcodes(mock_image)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"], "ASN123")
        self.assertEqual(result[0]["format"], "Code128")
        self.assertEqual(result[1]["text"], "PATCH T")

    def test_scan_no_zxing(self):
        """Should return empty list when zxing-cpp is not installed."""
        mock_image = MagicMock()

        # Remove zxingcpp from sys.modules if it exists and make import fail
        with patch.dict("sys.modules", {"zxingcpp": None}):
            # When a module is set to None in sys.modules, import raises ImportError
            result = scan_page_for_barcodes(mock_image)

        self.assertEqual(result, [])

    def test_scan_exception(self):
        """Should return empty list when scanning raises an exception."""
        mock_zxingcpp = MagicMock()
        mock_zxingcpp.read_barcodes.side_effect = RuntimeError("Scan failed")

        mock_image = MagicMock()

        with patch.dict("sys.modules", {"zxingcpp": mock_zxingcpp}):
            result = scan_page_for_barcodes(mock_image)

        self.assertEqual(result, [])
