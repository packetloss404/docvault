"""Tests for Pre/Post-Consume Hook Plugins."""

import os
import stat
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings

from processing.context import ProcessingContext
from processing.plugins.hooks import (
    PostConsumeHookPlugin,
    PreConsumeHookPlugin,
)


class PreConsumeHookPluginTest(TestCase):
    """Tests for PreConsumeHookPlugin."""

    def setUp(self):
        self.plugin = PreConsumeHookPlugin()

    def test_can_run_without_script(self):
        ctx = ProcessingContext()
        self.assertFalse(self.plugin.can_run(ctx))

    @override_settings(PRE_CONSUME_SCRIPT="/tmp/my-script.sh")
    def test_can_run_with_script(self):
        ctx = ProcessingContext()
        self.assertTrue(self.plugin.can_run(ctx))

    @override_settings(PRE_CONSUME_SCRIPT="nonexistent-script-12345")
    def test_missing_script_does_not_fail(self):
        """Missing script should not stop the pipeline."""
        ctx = ProcessingContext(
            source_path=Path("/tmp/test.txt"),
            original_filename="test.txt",
        )
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)

    @override_settings(PRE_CONSUME_SCRIPT="python -c \"pass\"", CONSUME_SCRIPT_TIMEOUT=5)
    def test_successful_script(self):
        """A simple script should execute successfully."""
        ctx = ProcessingContext(
            source_path=Path("/tmp/test.txt"),
            original_filename="test.txt",
            mime_type="text/plain",
            title="Test",
        )
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertIn("completed", result.message)


class PostConsumeHookPluginTest(TestCase):
    """Tests for PostConsumeHookPlugin."""

    def setUp(self):
        self.plugin = PostConsumeHookPlugin()

    def test_can_run_without_script(self):
        ctx = ProcessingContext()
        self.assertFalse(self.plugin.can_run(ctx))

    @override_settings(POST_CONSUME_SCRIPT="/tmp/my-post-script.sh")
    def test_can_run_with_script(self):
        ctx = ProcessingContext()
        self.assertTrue(self.plugin.can_run(ctx))

    @override_settings(POST_CONSUME_SCRIPT="python -c \"pass\"", CONSUME_SCRIPT_TIMEOUT=5)
    def test_successful_post_script(self):
        """Post-consume script should execute successfully."""
        ctx = ProcessingContext(
            source_path=Path("/tmp/test.txt"),
            original_filename="test.txt",
            document_id=42,
            task_id="abc123",
        )
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertIn("completed", result.message)

    @override_settings(POST_CONSUME_SCRIPT="python -c \"import sys; sys.exit(1)\"", CONSUME_SCRIPT_TIMEOUT=5)
    def test_failing_script_does_not_stop_pipeline(self):
        """A failing script should log a warning but not fail."""
        ctx = ProcessingContext(
            source_path=Path("/tmp/test.txt"),
            original_filename="test.txt",
        )
        result = self.plugin.process(ctx)
        self.assertTrue(result.success)
        self.assertIn("failed", result.message)
