"""Tests for the ClassificationPlugin."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from ml.plugin import ClassificationPlugin
from processing.context import PluginResult, ProcessingContext


class ClassificationPluginTest(TestCase):
    """Tests for the ClassificationPlugin."""

    def setUp(self):
        self.plugin = ClassificationPlugin()

    def test_name_and_order(self):
        """Plugin has the expected name and order."""
        self.assertEqual(self.plugin.name, "ClassificationPlugin")
        self.assertEqual(self.plugin.order, 100)

    def test_can_run_with_content(self):
        """can_run returns True when context has non-empty content."""
        context = ProcessingContext(content="This is a test document.")
        self.assertTrue(self.plugin.can_run(context))

    def test_can_run_without_content(self):
        """can_run returns False when content is empty."""
        context = ProcessingContext(content="")
        self.assertFalse(self.plugin.can_run(context))

    def test_can_run_whitespace_only(self):
        """can_run returns False when content is only whitespace."""
        context = ProcessingContext(content="   \n\t  ")
        self.assertFalse(self.plugin.can_run(context))

    @patch("ml.classifier.get_classifier")
    def test_process_no_classifier(self, mock_get_classifier):
        """With no trained classifier, process succeeds with a message."""
        mock_get_classifier.return_value = None
        context = ProcessingContext(content="Some document content.")

        result = self.plugin.process(context)

        self.assertIsInstance(result, PluginResult)
        self.assertTrue(result.success)
        self.assertIn("No classifier", result.message)
        # Suggestions should remain at defaults
        self.assertEqual(context.suggested_tags, [])
        self.assertIsNone(context.suggested_correspondent)
        self.assertIsNone(context.suggested_document_type)
        self.assertIsNone(context.suggested_storage_path)

    @patch("ml.classifier.get_classifier")
    def test_process_with_classifier(self, mock_get_classifier):
        """When classifier returns predictions, context gets populated."""
        mock_classifier = MagicMock()
        mock_classifier.predict_tags.return_value = [(10, 0.9), (20, 0.7)]
        mock_classifier.predict_correspondent.return_value = [(30, 0.85)]
        mock_classifier.predict_document_type.return_value = [(40, 0.95)]
        mock_classifier.predict_storage_path.return_value = [(50, 0.8)]
        mock_get_classifier.return_value = mock_classifier

        context = ProcessingContext(content="Invoice payment billing total amount due.")

        result = self.plugin.process(context)

        self.assertIsInstance(result, PluginResult)
        self.assertTrue(result.success)
        self.assertIn("complete", result.message.lower())

        # Tags should be extracted as IDs
        self.assertEqual(context.suggested_tags, [10, 20])
        # Single-label predictions use the first (highest confidence) result
        self.assertEqual(context.suggested_correspondent, 30)
        self.assertEqual(context.suggested_document_type, 40)
        self.assertEqual(context.suggested_storage_path, 50)

    @patch("ml.classifier.get_classifier")
    def test_process_no_predictions(self, mock_get_classifier):
        """When classifier returns empty predictions, context stays at defaults."""
        mock_classifier = MagicMock()
        mock_classifier.predict_tags.return_value = []
        mock_classifier.predict_correspondent.return_value = []
        mock_classifier.predict_document_type.return_value = []
        mock_classifier.predict_storage_path.return_value = []
        mock_get_classifier.return_value = mock_classifier

        context = ProcessingContext(content="Something weird and unrecognized.")

        result = self.plugin.process(context)

        self.assertTrue(result.success)
        self.assertEqual(context.suggested_tags, [])
        self.assertIsNone(context.suggested_correspondent)
        self.assertIsNone(context.suggested_document_type)
        # Storage path gets set even without override check
        self.assertIsNone(context.suggested_storage_path)

    @patch("ml.classifier.get_classifier")
    def test_process_respects_override_tags(self, mock_get_classifier):
        """When override_tags is set, tag suggestions are not applied."""
        mock_classifier = MagicMock()
        mock_classifier.predict_tags.return_value = [(10, 0.9)]
        mock_classifier.predict_correspondent.return_value = []
        mock_classifier.predict_document_type.return_value = []
        mock_classifier.predict_storage_path.return_value = []
        mock_get_classifier.return_value = mock_classifier

        context = ProcessingContext(
            content="Invoice payment billing.",
            override_tags=[99],  # User provided explicit tags
        )

        self.plugin.process(context)

        # Tag suggestions should NOT be overwritten when override_tags is set
        self.assertEqual(context.suggested_tags, [])

    @patch("ml.classifier.get_classifier")
    def test_process_respects_override_correspondent(self, mock_get_classifier):
        """When override_correspondent is set, correspondent is not overwritten."""
        mock_classifier = MagicMock()
        mock_classifier.predict_tags.return_value = []
        mock_classifier.predict_correspondent.return_value = [(30, 0.85)]
        mock_classifier.predict_document_type.return_value = []
        mock_classifier.predict_storage_path.return_value = []
        mock_get_classifier.return_value = mock_classifier

        context = ProcessingContext(
            content="Invoice from Acme.",
            override_correspondent=77,
        )

        self.plugin.process(context)

        # Correspondent suggestion should NOT be applied
        self.assertIsNone(context.suggested_correspondent)

    @patch("ml.classifier.get_classifier")
    def test_process_respects_override_document_type(self, mock_get_classifier):
        """When override_document_type is set, doc type is not overwritten."""
        mock_classifier = MagicMock()
        mock_classifier.predict_tags.return_value = []
        mock_classifier.predict_correspondent.return_value = []
        mock_classifier.predict_document_type.return_value = [(40, 0.95)]
        mock_classifier.predict_storage_path.return_value = []
        mock_get_classifier.return_value = mock_classifier

        context = ProcessingContext(
            content="Contract agreement terms.",
            override_document_type=88,
        )

        self.plugin.process(context)

        # Document type suggestion should NOT be applied
        self.assertIsNone(context.suggested_document_type)
