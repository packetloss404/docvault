"""Tests for processing context and plugin result dataclasses."""

from pathlib import Path

from django.test import TestCase

from processing.context import PluginResult, ProcessingContext


class PluginResultTest(TestCase):
    """Tests for PluginResult dataclass."""

    def test_default_values(self):
        result = PluginResult()
        self.assertTrue(result.success)
        self.assertFalse(result.should_stop)
        self.assertEqual(result.message, "")

    def test_failure_result(self):
        result = PluginResult(success=False, should_stop=True, message="Error")
        self.assertFalse(result.success)
        self.assertTrue(result.should_stop)
        self.assertEqual(result.message, "Error")


class ProcessingContextTest(TestCase):
    """Tests for ProcessingContext dataclass."""

    def test_default_values(self):
        ctx = ProcessingContext()
        self.assertIsNone(ctx.source_path)
        self.assertEqual(ctx.original_filename, "")
        self.assertEqual(ctx.errors, [])
        self.assertEqual(ctx.suggested_tags, [])
        self.assertEqual(ctx.progress, 0.0)

    def test_with_values(self):
        ctx = ProcessingContext(
            source_path=Path("/tmp/test.pdf"),
            original_filename="test.pdf",
            user_id=1,
            source_type="api",
        )
        self.assertEqual(ctx.source_path, Path("/tmp/test.pdf"))
        self.assertEqual(ctx.original_filename, "test.pdf")
        self.assertEqual(ctx.user_id, 1)

    def test_errors_are_independent(self):
        """Each context should have its own errors list."""
        ctx1 = ProcessingContext()
        ctx2 = ProcessingContext()
        ctx1.errors.append("err1")
        self.assertEqual(len(ctx2.errors), 0)
