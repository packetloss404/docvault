"""Tests for document parsers and parser registry."""

import tempfile
from pathlib import Path

from django.test import TestCase

from processing.parsers.base import (
    DocumentParser,
    ParseResult,
    clear_registry,
    get_parser_for_mime_type,
    get_supported_mime_types,
    register_parser,
)
from processing.parsers.email_parser import EmailParser
from processing.parsers.image import ImageParser
from processing.parsers.office import OfficeParser
from processing.parsers.pdf import PDFParser
from processing.parsers.text import TextParser


class ParserRegistryTest(TestCase):
    """Tests for the parser registry."""

    def setUp(self):
        clear_registry()

    def tearDown(self):
        clear_registry()
        # Re-register parsers (normally done in app.ready())
        for cls in [PDFParser, ImageParser, OfficeParser, TextParser, EmailParser]:
            register_parser(cls)

    def test_register_and_retrieve(self):
        register_parser(TextParser)
        parser = get_parser_for_mime_type("text/plain")
        self.assertIsInstance(parser, TextParser)

    def test_unknown_mime_type_returns_none(self):
        self.assertIsNone(get_parser_for_mime_type("application/unknown"))

    def test_get_supported_mime_types(self):
        register_parser(TextParser)
        register_parser(PDFParser)
        types = get_supported_mime_types()
        self.assertIn("text/plain", types)
        self.assertIn("application/pdf", types)

    def test_multiple_parsers_same_mime(self):
        """First registered parser wins."""

        class CustomTextParser(DocumentParser):
            supported_mime_types = ["text/plain"]

            def parse(self, source_path, mime_type, language="eng"):
                return ParseResult(content="custom")

        register_parser(TextParser)
        register_parser(CustomTextParser)
        parser = get_parser_for_mime_type("text/plain")
        self.assertIsInstance(parser, TextParser)

    def test_clear_registry(self):
        register_parser(TextParser)
        self.assertIsNotNone(get_parser_for_mime_type("text/plain"))
        clear_registry()
        self.assertIsNone(get_parser_for_mime_type("text/plain"))

    def test_all_parsers_registered_on_startup(self):
        """App ready() should have registered all parsers."""
        # Re-register
        for cls in [PDFParser, ImageParser, OfficeParser, TextParser, EmailParser]:
            register_parser(cls)

        self.assertIsNotNone(get_parser_for_mime_type("application/pdf"))
        self.assertIsNotNone(get_parser_for_mime_type("image/jpeg"))
        self.assertIsNotNone(get_parser_for_mime_type("text/plain"))
        self.assertIsNotNone(get_parser_for_mime_type("text/html"))
        self.assertIsNotNone(get_parser_for_mime_type("message/rfc822"))
        self.assertIsNotNone(get_parser_for_mime_type(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ))


class TextParserTest(TestCase):
    """Tests for the TextParser."""

    def setUp(self):
        self.parser = TextParser()
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_parse_plain_text(self):
        path = self.temp_dir / "test.txt"
        path.write_text("Hello, World!", encoding="utf-8")
        result = self.parser.parse(path, "text/plain")
        self.assertEqual(result.content, "Hello, World!")
        self.assertEqual(result.page_count, 1)

    def test_parse_html_strips_tags(self):
        path = self.temp_dir / "test.html"
        path.write_text(
            "<html><body><h1>Title</h1><p>Content</p></body></html>",
            encoding="utf-8",
        )
        result = self.parser.parse(path, "text/html")
        self.assertIn("Title", result.content)
        self.assertIn("Content", result.content)
        self.assertNotIn("<h1>", result.content)

    def test_parse_html_removes_script_and_style(self):
        path = self.temp_dir / "test.html"
        path.write_text(
            "<html><head><style>body{}</style></head>"
            "<body><script>alert(1)</script><p>Safe content</p></body></html>",
            encoding="utf-8",
        )
        result = self.parser.parse(path, "text/html")
        self.assertIn("Safe content", result.content)
        self.assertNotIn("alert", result.content)
        self.assertNotIn("body{}", result.content)

    def test_parse_csv(self):
        path = self.temp_dir / "test.csv"
        path.write_text("name,age\nAlice,30\nBob,25", encoding="utf-8")
        result = self.parser.parse(path, "text/csv")
        self.assertIn("Alice", result.content)
        self.assertIn("Bob", result.content)

    def test_parse_json(self):
        path = self.temp_dir / "test.json"
        path.write_text('{"name": "DocVault"}', encoding="utf-8")
        result = self.parser.parse(path, "application/json")
        self.assertIn("DocVault", result.content)


class EmailParserTest(TestCase):
    """Tests for the EmailParser."""

    def setUp(self):
        self.parser = EmailParser()
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_parse_eml(self):
        eml_content = (
            "From: sender@example.com\r\n"
            "To: recipient@example.com\r\n"
            "Subject: Test Email\r\n"
            "Date: Mon, 01 Jan 2025 12:00:00 +0000\r\n"
            "Content-Type: text/plain\r\n"
            "\r\n"
            "This is the email body."
        )
        path = self.temp_dir / "test.eml"
        path.write_bytes(eml_content.encode("utf-8"))

        result = self.parser.parse(path, "message/rfc822")
        self.assertIn("sender@example.com", result.content)
        self.assertIn("Test Email", result.content)
        self.assertIn("email body", result.content)
        self.assertEqual(result.metadata["subject"], "Test Email")
        self.assertEqual(result.page_count, 1)

    def test_parse_eml_extracts_date(self):
        eml_content = (
            "From: a@b.com\r\n"
            "Date: Wed, 15 Jan 2025 10:30:00 +0000\r\n"
            "Subject: Dated\r\n"
            "Content-Type: text/plain\r\n"
            "\r\n"
            "Body."
        )
        path = self.temp_dir / "dated.eml"
        path.write_bytes(eml_content.encode("utf-8"))
        result = self.parser.parse(path, "message/rfc822")
        self.assertIsNotNone(result.date)
        self.assertEqual(result.date.year, 2025)
        self.assertEqual(result.date.month, 1)
        self.assertEqual(result.date.day, 15)


class OfficeParserTest(TestCase):
    """Tests for the OfficeParser fallback text extraction."""

    def setUp(self):
        self.parser = OfficeParser()
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_docx_fallback_extraction(self):
        """Test DOCX text extraction via zipfile (no LibreOffice needed)."""
        import zipfile
        from xml.etree.ElementTree import Element, SubElement, tostring

        # Create a minimal DOCX
        docx_path = self.temp_dir / "test.docx"
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

        body = Element(f"{{{ns}}}document")
        body_el = SubElement(body, f"{{{ns}}}body")
        para = SubElement(body_el, f"{{{ns}}}p")
        run = SubElement(para, f"{{{ns}}}r")
        text = SubElement(run, f"{{{ns}}}t")
        text.text = "Hello from DOCX"

        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", tostring(body, encoding="unicode"))
            zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')

        result = self.parser.parse(
            docx_path,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertIn("Hello from DOCX", result.content)


class ImageParserTest(TestCase):
    """Tests for the ImageParser."""

    def setUp(self):
        self.parser = ImageParser()
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_image_to_pdf_conversion(self):
        """Test that images can be converted to PDF."""
        from PIL import Image

        # Create a simple test image
        img_path = self.temp_dir / "test.png"
        img = Image.new("RGB", (100, 100), color="white")
        img.save(str(img_path))

        pdf_path = self.parser._image_to_pdf(img_path)
        self.assertIsNotNone(pdf_path)
        self.assertTrue(pdf_path.exists())

    def test_rgba_image_conversion(self):
        """RGBA images should be converted to RGB before PDF conversion."""
        from PIL import Image

        img_path = self.temp_dir / "rgba.png"
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        img.save(str(img_path))

        pdf_path = self.parser._image_to_pdf(img_path)
        self.assertIsNotNone(pdf_path)


class PDFParserTest(TestCase):
    """Tests for the PDFParser text extraction (no OCR required)."""

    def setUp(self):
        self.parser = PDFParser()
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_create_and_extract_text_from_pdf(self):
        """Create a simple text PDF and extract text."""
        try:
            from fpdf import FPDF
        except ImportError:
            self.skipTest("fpdf2 not available")

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(text="Hello DocVault PDF")
        pdf_path = self.temp_dir / "test.pdf"
        pdf.output(str(pdf_path))

        content = self.parser._extract_text(pdf_path)
        self.assertIn("Hello DocVault PDF", content)

    def test_get_page_count(self):
        """Test page count extraction."""
        try:
            from fpdf import FPDF
        except ImportError:
            self.skipTest("fpdf2 not available")

        pdf = FPDF()
        pdf.add_page()
        pdf.add_page()
        pdf.add_page()
        pdf_path = self.temp_dir / "multi.pdf"
        pdf.output(str(pdf_path))

        count = self.parser._get_page_count(pdf_path)
        self.assertEqual(count, 3)
