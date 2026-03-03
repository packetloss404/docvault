"""Tests for the processing pipeline (consumer and plugins)."""

import hashlib
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase

from documents.models import Document
from processing.consumer import DocumentConsumer
from processing.context import PluginResult, ProcessingContext
from processing.plugins.base import ProcessingPlugin
from processing.plugins.preflight import PreflightPlugin


class PreflightPluginTest(TestCase):
    """Tests for the PreflightPlugin."""

    def setUp(self):
        self.plugin = PreflightPlugin()
        self.temp_dir = Path(tempfile.mkdtemp())

    def _create_temp_file(self, content=b"test content", name="test.txt"):
        path = self.temp_dir / name
        path.write_bytes(content)
        return path

    def test_can_run_with_source_path(self):
        ctx = ProcessingContext(source_path=Path("/tmp/test.txt"))
        self.assertTrue(self.plugin.can_run(ctx))

    def test_can_run_without_source_path(self):
        ctx = ProcessingContext()
        self.assertFalse(self.plugin.can_run(ctx))

    def test_process_calculates_checksum(self):
        path = self._create_temp_file(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        ctx = ProcessingContext(source_path=path, original_filename="test.txt")
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertEqual(ctx.checksum, expected)

    def test_process_detects_mime_type(self):
        path = self._create_temp_file(b"test content")
        ctx = ProcessingContext(source_path=path, original_filename="test.txt")
        self.plugin.process(ctx)
        self.assertNotEqual(ctx.mime_type, "")

    def test_process_sets_title_from_filename(self):
        path = self._create_temp_file()
        ctx = ProcessingContext(source_path=path, original_filename="my_document.pdf")
        self.plugin.process(ctx)
        self.assertEqual(ctx.title, "my_document")

    def test_process_respects_override_title(self):
        path = self._create_temp_file()
        ctx = ProcessingContext(
            source_path=path,
            original_filename="original.pdf",
            override_title="Custom Title",
        )
        self.plugin.process(ctx)
        self.assertEqual(ctx.title, "Custom Title")

    def test_process_detects_duplicate(self):
        path = self._create_temp_file(b"duplicate content")
        checksum = hashlib.sha256(b"duplicate content").hexdigest()
        user = User.objects.create_user("owner", password="test123!")
        Document.objects.create(title="Existing", checksum=checksum, owner=user)

        ctx = ProcessingContext(source_path=path, original_filename="dup.txt")
        result = self.plugin.process(ctx)
        self.assertFalse(result.success)
        self.assertTrue(result.should_stop)
        self.assertIn("Duplicate", result.message)

    def test_process_missing_file(self):
        ctx = ProcessingContext(
            source_path=Path("/nonexistent/file.txt"),
            original_filename="file.txt",
        )
        result = self.plugin.process(ctx)
        self.assertFalse(result.success)
        self.assertTrue(result.should_stop)

    def test_process_sets_file_size(self):
        content = b"x" * 512
        path = self._create_temp_file(content)
        ctx = ProcessingContext(source_path=path, original_filename="sized.bin")
        self.plugin.process(ctx)
        self.assertEqual(ctx.file_size, 512)


class DocumentConsumerTest(TestCase):
    """Tests for the DocumentConsumer orchestrator."""

    def test_discover_plugins(self):
        consumer = DocumentConsumer()
        self.assertGreater(len(consumer.plugins), 0)

    def test_plugins_sorted_by_order(self):
        consumer = DocumentConsumer()
        orders = [cls.order for cls in consumer.plugins]
        self.assertEqual(orders, sorted(orders))

    def test_consume_runs_preflight(self):
        temp_file = Path(tempfile.mktemp(suffix=".txt"))
        temp_file.write_bytes(b"test content for pipeline")
        user = User.objects.create_user("pipeuser", password="test123!")

        ctx = ProcessingContext(
            source_path=temp_file,
            original_filename="pipeline_test.txt",
            user_id=user.pk,
        )
        result_ctx = DocumentConsumer().consume(ctx)

        # Preflight should have set checksum and title
        self.assertNotEqual(result_ctx.checksum, "")
        self.assertEqual(result_ctx.title, "pipeline_test")
        # Store plugin should have created a document
        self.assertIsNotNone(result_ctx.document_id)
        doc = Document.objects.get(pk=result_ctx.document_id)
        self.assertEqual(doc.title, "pipeline_test")
        self.assertEqual(doc.owner, user)

        # Cleanup
        temp_file.unlink(missing_ok=True)

    def test_consume_stops_on_duplicate(self):
        content = b"duplicate pipeline content"
        checksum = hashlib.sha256(content).hexdigest()
        user = User.objects.create_user("dupuser", password="test123!")
        Document.objects.create(title="First", checksum=checksum, owner=user)

        temp_file = Path(tempfile.mktemp(suffix=".txt"))
        temp_file.write_bytes(content)

        ctx = ProcessingContext(
            source_path=temp_file,
            original_filename="dup.txt",
            user_id=user.pk,
        )
        result_ctx = DocumentConsumer().consume(ctx)

        self.assertGreater(len(result_ctx.errors), 0)
        self.assertIn("Duplicate", result_ctx.errors[0])
        self.assertIsNone(result_ctx.document_id)

        temp_file.unlink(missing_ok=True)


class CustomPluginTest(TestCase):
    """Tests for custom plugin behavior."""

    def test_custom_plugin_interface(self):
        """Verify the plugin ABC contract works."""

        class TestPlugin(ProcessingPlugin):
            name = "TestPlugin"
            order = 50

            def can_run(self, context):
                return True

            def process(self, context):
                context.content = "processed"
                return PluginResult(success=True)

        plugin = TestPlugin()
        ctx = ProcessingContext()
        self.assertTrue(plugin.can_run(ctx))
        result = plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertEqual(ctx.content, "processed")
