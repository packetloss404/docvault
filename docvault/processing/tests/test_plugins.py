"""Tests for the ParserPlugin, LanguageDetectionPlugin, and DateExtractionPlugin."""

import tempfile
from datetime import date
from pathlib import Path

from django.test import TestCase

from processing.context import ProcessingContext
from processing.parsers.base import clear_registry, register_parser
from processing.parsers.text import TextParser
from processing.plugins.date_extraction import DateExtractionPlugin
from processing.plugins.language import LanguageDetectionPlugin
from processing.plugins.parser import ParserPlugin


class ParserPluginTest(TestCase):
    """Tests for the ParserPlugin."""

    def setUp(self):
        self.plugin = ParserPlugin()
        self.temp_dir = Path(tempfile.mkdtemp())
        # Ensure text parser is registered
        register_parser(TextParser)

    def test_can_run_with_mime_type(self):
        ctx = ProcessingContext(mime_type="text/plain")
        self.assertTrue(self.plugin.can_run(ctx))

    def test_can_run_without_mime_type(self):
        ctx = ProcessingContext()
        self.assertFalse(self.plugin.can_run(ctx))

    def test_process_text_file(self):
        path = self.temp_dir / "test.txt"
        path.write_text("Parser plugin test content", encoding="utf-8")
        ctx = ProcessingContext(
            source_path=path,
            mime_type="text/plain",
            original_filename="test.txt",
        )
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertEqual(ctx.content, "Parser plugin test content")
        self.assertEqual(ctx.page_count, 1)

    def test_process_unknown_mime_type(self):
        ctx = ProcessingContext(
            source_path=Path("/tmp/fake"),
            mime_type="application/x-unknown-format",
            original_filename="fake.xyz",
        )
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)  # Gracefully skips
        self.assertEqual(ctx.content, "")


class LanguageDetectionPluginTest(TestCase):
    """Tests for the LanguageDetectionPlugin."""

    def setUp(self):
        self.plugin = LanguageDetectionPlugin()

    def test_can_run_with_content(self):
        ctx = ProcessingContext(content="Some text", language="")
        self.assertTrue(self.plugin.can_run(ctx))

    def test_can_run_without_content(self):
        ctx = ProcessingContext(content="")
        self.assertFalse(self.plugin.can_run(ctx))

    def test_can_run_already_detected(self):
        ctx = ProcessingContext(content="Some text", language="en")
        self.assertFalse(self.plugin.can_run(ctx))

    def test_detect_english(self):
        ctx = ProcessingContext(
            content="This is a relatively long English text that should be "
                    "detected as English by the language detection library. "
                    "The document management system processes many documents.",
        )
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertEqual(ctx.language, "en")

    def test_detect_german(self):
        ctx = ProcessingContext(
            content="Dies ist ein langer deutscher Text, der als Deutsch "
                    "erkannt werden sollte. Das Dokumentenmanagementsystem "
                    "verarbeitet viele verschiedene Dokumente jeden Tag.",
        )
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertEqual(ctx.language, "de")

    def test_fallback_on_short_content(self):
        """Very short content might fail detection; should default to 'en'."""
        ctx = ProcessingContext(content="x")
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertIsNotNone(ctx.language)


class DateExtractionPluginTest(TestCase):
    """Tests for the DateExtractionPlugin."""

    def setUp(self):
        self.plugin = DateExtractionPlugin()

    def test_can_run_with_content_no_date(self):
        ctx = ProcessingContext(content="Some text")
        self.assertTrue(self.plugin.can_run(ctx))

    def test_can_run_already_has_date(self):
        ctx = ProcessingContext(content="text", date_created=date.today())
        self.assertFalse(self.plugin.can_run(ctx))

    def test_extract_iso_date(self):
        ctx = ProcessingContext(
            content="Document dated 2025-03-15 for review.",
        )
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertEqual(ctx.date_created, date(2025, 3, 15))

    def test_extract_slash_date(self):
        ctx = ProcessingContext(
            content="Invoice date: 01/15/2025. Amount due.",
        )
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertIsNotNone(ctx.date_created)
        self.assertEqual(ctx.date_created.year, 2025)

    def test_extract_written_date(self):
        ctx = ProcessingContext(
            content="Signed on January 20, 2025 by the undersigned.",
        )
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertIsNotNone(ctx.date_created)
        self.assertEqual(ctx.date_created.year, 2025)

    def test_fallback_to_today(self):
        ctx = ProcessingContext(content="No date patterns in this text at all.")
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertEqual(ctx.date_created, date.today())

    def test_no_content(self):
        ctx = ProcessingContext(content="")
        self.assertFalse(self.plugin.can_run(ctx))
