"""Tests for MATCH_AUTO integration with the ML classifier."""

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase

from documents.constants import MATCH_AUTO
from documents.models.document_type import DocumentType
from organization.matching import _match_auto, matches
from organization.models import Correspondent, StoragePath, Tag


class MatchAutoTest(TestCase):
    """Tests for the _match_auto function in organization.matching."""

    def setUp(self):
        self.user = User.objects.create_user("matchauto_user", password="testpass123")

        self.tag = Tag.objects.create(
            name="AutoTag",
            slug="autotag",
            matching_algorithm=MATCH_AUTO,
            color="#ff0000",
            owner=self.user,
        )
        self.correspondent = Correspondent.objects.create(
            name="AutoCorr",
            slug="autocorr",
            matching_algorithm=MATCH_AUTO,
            owner=self.user,
        )
        self.document_type = DocumentType.objects.create(
            name="AutoDocType",
            slug="autodoctype",
            matching_algorithm=MATCH_AUTO,
        )
        self.storage_path = StoragePath.objects.create(
            name="AutoPath",
            slug="autopath",
            path="/auto/",
            matching_algorithm=MATCH_AUTO,
            owner=self.user,
        )

    @patch("ml.classifier.get_classifier")
    def test_match_auto_no_classifier(self, mock_get_classifier):
        """Returns False when no classifier is available."""
        mock_get_classifier.return_value = None
        result = _match_auto(self.tag, "Some document content")
        self.assertFalse(result)

    @patch("ml.classifier.get_classifier")
    def test_match_auto_tag_match(self, mock_get_classifier):
        """Returns True when classifier predicts the tag."""
        mock_classifier = MagicMock()
        mock_classifier.predict_tags.return_value = [
            (self.tag.pk, 0.9),
            (999, 0.5),
        ]
        mock_get_classifier.return_value = mock_classifier

        result = _match_auto(self.tag, "Invoice content here")

        self.assertTrue(result)
        mock_classifier.predict_tags.assert_called_once_with("Invoice content here")

    @patch("ml.classifier.get_classifier")
    def test_match_auto_tag_no_match(self, mock_get_classifier):
        """Returns False when tag is not in predictions."""
        mock_classifier = MagicMock()
        mock_classifier.predict_tags.return_value = [
            (999, 0.9),  # Different tag ID
        ]
        mock_get_classifier.return_value = mock_classifier

        result = _match_auto(self.tag, "Some unrelated content")
        self.assertFalse(result)

    @patch("ml.classifier.get_classifier")
    def test_match_auto_tag_empty_predictions(self, mock_get_classifier):
        """Returns False when classifier returns no tag predictions."""
        mock_classifier = MagicMock()
        mock_classifier.predict_tags.return_value = []
        mock_get_classifier.return_value = mock_classifier

        result = _match_auto(self.tag, "Some content")
        self.assertFalse(result)

    @patch("ml.classifier.get_classifier")
    def test_match_auto_correspondent_match(self, mock_get_classifier):
        """Returns True when classifier predicts the correspondent with confidence >= 0.5."""
        mock_classifier = MagicMock()
        mock_classifier.predict_correspondent.return_value = [
            (self.correspondent.pk, 0.85),
        ]
        mock_get_classifier.return_value = mock_classifier

        result = _match_auto(self.correspondent, "Invoice from AutoCorr")

        self.assertTrue(result)
        mock_classifier.predict_correspondent.assert_called_once()

    @patch("ml.classifier.get_classifier")
    def test_match_auto_correspondent_low_confidence(self, mock_get_classifier):
        """Returns False when correspondent prediction confidence is below 0.5."""
        mock_classifier = MagicMock()
        mock_classifier.predict_correspondent.return_value = [
            (self.correspondent.pk, 0.3),  # Below threshold
        ]
        mock_get_classifier.return_value = mock_classifier

        result = _match_auto(self.correspondent, "Some content")
        self.assertFalse(result)

    @patch("ml.classifier.get_classifier")
    def test_match_auto_correspondent_no_match(self, mock_get_classifier):
        """Returns False when correspondent ID is not in predictions."""
        mock_classifier = MagicMock()
        mock_classifier.predict_correspondent.return_value = [
            (999, 0.9),  # Different correspondent ID
        ]
        mock_get_classifier.return_value = mock_classifier

        result = _match_auto(self.correspondent, "Some content")
        self.assertFalse(result)

    @patch("ml.classifier.get_classifier")
    def test_match_auto_document_type(self, mock_get_classifier):
        """Returns True when classifier predicts the document type."""
        mock_classifier = MagicMock()
        mock_classifier.predict_document_type.return_value = [
            (self.document_type.pk, 0.92),
        ]
        mock_get_classifier.return_value = mock_classifier

        result = _match_auto(self.document_type, "Contract agreement terms")

        self.assertTrue(result)
        mock_classifier.predict_document_type.assert_called_once()

    @patch("ml.classifier.get_classifier")
    def test_match_auto_document_type_low_confidence(self, mock_get_classifier):
        """Returns False when document type prediction confidence is below 0.5."""
        mock_classifier = MagicMock()
        mock_classifier.predict_document_type.return_value = [
            (self.document_type.pk, 0.2),
        ]
        mock_get_classifier.return_value = mock_classifier

        result = _match_auto(self.document_type, "Some content")
        self.assertFalse(result)

    @patch("ml.classifier.get_classifier")
    def test_match_auto_storage_path(self, mock_get_classifier):
        """Returns True when classifier predicts the storage path."""
        mock_classifier = MagicMock()
        mock_classifier.predict_storage_path.return_value = [
            (self.storage_path.pk, 0.75),
        ]
        mock_get_classifier.return_value = mock_classifier

        result = _match_auto(self.storage_path, "Invoice from storage path")

        self.assertTrue(result)
        mock_classifier.predict_storage_path.assert_called_once()

    @patch("ml.classifier.get_classifier")
    def test_match_auto_storage_path_low_confidence(self, mock_get_classifier):
        """Returns False when storage path prediction confidence is below 0.5."""
        mock_classifier = MagicMock()
        mock_classifier.predict_storage_path.return_value = [
            (self.storage_path.pk, 0.1),
        ]
        mock_get_classifier.return_value = mock_classifier

        result = _match_auto(self.storage_path, "Some content")
        self.assertFalse(result)


class MatchAutoIntegrationTest(TestCase):
    """Tests that the matches() dispatcher routes MATCH_AUTO correctly."""

    def setUp(self):
        self.user = User.objects.create_user("matchauto_int", password="testpass123")

    @patch("ml.classifier.get_classifier")
    def test_matches_dispatches_to_match_auto(self, mock_get_classifier):
        """The top-level matches() function routes MATCH_AUTO to _match_auto."""
        mock_classifier = MagicMock()
        mock_classifier.predict_tags.return_value = []
        mock_get_classifier.return_value = mock_classifier

        tag = Tag.objects.create(
            name="DispatchTag",
            slug="dispatchtag",
            matching_algorithm=MATCH_AUTO,
            match="anything",
            color="#123456",
            owner=self.user,
        )

        # Should route to _match_auto, not any string-matching algorithm
        result = matches(tag, "Some content")
        self.assertFalse(result)
        # Verify the classifier was consulted
        mock_classifier.predict_tags.assert_called_once()

    @patch("ml.classifier.get_classifier")
    def test_matches_returns_false_no_classifier(self, mock_get_classifier):
        """matches() returns False for MATCH_AUTO when no classifier is loaded."""
        mock_get_classifier.return_value = None

        tag = Tag.objects.create(
            name="NoClf",
            slug="noclf",
            matching_algorithm=MATCH_AUTO,
            match="anything",
            color="#654321",
            owner=self.user,
        )

        result = matches(tag, "Some content")
        self.assertFalse(result)
