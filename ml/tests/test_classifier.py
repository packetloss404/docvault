"""Tests for the DocumentClassifier."""

import os
import pickle
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from documents.constants import MATCH_AUTO, MATCH_NONE
from documents.models import Document
from documents.models.document_type import DocumentType
from ml.classifier import (
    MODEL_FORMAT_VERSION,
    DocumentClassifier,
    _compute_hash,
)
from organization.models import Correspondent, StoragePath, Tag

# Varied invoice content samples for realistic training data
INVOICE_CONTENTS = [
    "invoice payment billing total amount due receipt company account financial transaction",
    "monthly invoice statement billing period accounts receivable payment terms net thirty",
    "purchase order invoice vendor supplier payment remittance advice banking details",
    "billing summary total charges taxes shipping handling payment processing merchant",
    "accounts payable invoice approval workflow payment schedule budget allocation fiscal",
    "overdue invoice reminder balance outstanding payment required immediate attention",
    "credit memo invoice adjustment refund processing accounts receivable department",
    "recurring billing subscription invoice automatic payment renewal annual license",
    "expense report reimbursement invoice employee travel accommodation receipts",
    "wholesale distributor invoice bulk order shipping manifest delivery confirmation",
    "utility invoice electricity water gas service charges consumption billing meter",
    "medical billing invoice insurance claim copayment deductible healthcare provider",
]

# Varied contract content samples
CONTRACT_CONTENTS = [
    "contract agreement terms conditions signature legal binding party clause obligation",
    "warranty liability indemnification jurisdiction governing law arbitration dispute",
    "employment contract salary benefits termination notice period probationary clause",
    "lease agreement rental property landlord tenant deposit maintenance responsibility",
    "service level agreement performance metrics uptime guarantee penalty remediation",
    "non disclosure agreement confidential information proprietary trade secret protection",
    "partnership agreement profit sharing governance decision authority contribution",
    "licensing agreement intellectual property royalty sublicense territory exclusivity",
    "merger acquisition agreement due diligence representations warranties closing conditions",
    "vendor contract procurement deliverables milestones acceptance criteria penalties",
    "consulting agreement scope engagement fees retainer independent contractor relationship",
    "franchise agreement territory operations standards marketing fees ongoing royalties",
]


def _create_training_data(user, tag_inv, tag_con, corr_acme, corr_globex,
                          dt_inv, dt_con, sp_inv, sp_con):
    """Create a sufficient number of varied training documents."""
    for i, content in enumerate(INVOICE_CONTENTS):
        doc = Document.objects.create(
            title=f"Invoice {i}",
            content=content,
            document_type=dt_inv,
            correspondent=corr_acme,
            storage_path=sp_inv,
            filename=f"invoice_{i}.pdf",
            owner=user,
        )
        doc.tags.add(tag_inv)

    for i, content in enumerate(CONTRACT_CONTENTS):
        doc = Document.objects.create(
            title=f"Contract {i}",
            content=content,
            document_type=dt_con,
            correspondent=corr_globex,
            storage_path=sp_con,
            filename=f"contract_{i}.pdf",
            owner=user,
        )
        doc.tags.add(tag_con)


class ComputeHashTest(TestCase):
    """Tests for the _compute_hash utility function."""

    def test_same_data_same_hash(self):
        """Identical inputs produce the same hash."""
        contents = ["hello world", "foo bar"]
        labels = [1, 2]
        hash1 = _compute_hash(contents, labels)
        hash2 = _compute_hash(contents, labels)
        self.assertEqual(hash1, hash2)

    def test_different_data_different_hash(self):
        """Different inputs produce different hashes."""
        hash1 = _compute_hash(["hello"], [1])
        hash2 = _compute_hash(["goodbye"], [2])
        self.assertNotEqual(hash1, hash2)

    def test_empty_data_hash(self):
        """Empty inputs still produce a valid hash string."""
        result = _compute_hash([], [])
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 64)  # SHA-256 hex digest length


class DocumentClassifierTrainingTest(TestCase):
    """Tests for DocumentClassifier training and prediction.

    Uses 12 invoice docs + 12 contract docs with varied content to satisfy
    scikit-learn's MLPClassifier(early_stopping=True) validation split requirement
    and CountVectorizer's min_df/max_df pruning thresholds.
    """

    def setUp(self):
        self.user = User.objects.create_user("mluser", password="testpass123")

        # Tags with MATCH_AUTO
        self.tag_invoice = Tag.objects.create(
            name="Invoice", slug="invoice",
            matching_algorithm=MATCH_AUTO, color="#ff0000",
        )
        self.tag_contract = Tag.objects.create(
            name="Contract", slug="contract",
            matching_algorithm=MATCH_AUTO, color="#00ff00",
        )

        # Correspondents with MATCH_AUTO (need at least 2)
        self.corr_acme = Correspondent.objects.create(
            name="Acme Corp", slug="acme-corp",
            matching_algorithm=MATCH_AUTO,
        )
        self.corr_globex = Correspondent.objects.create(
            name="Globex Inc", slug="globex-inc",
            matching_algorithm=MATCH_AUTO,
        )

        # DocumentTypes with MATCH_AUTO (need at least 2)
        self.dt_invoice = DocumentType.objects.create(
            name="Invoice", slug="invoice",
            matching_algorithm=MATCH_AUTO,
        )
        self.dt_contract = DocumentType.objects.create(
            name="Contract", slug="contract",
            matching_algorithm=MATCH_AUTO,
        )

        # StoragePaths with MATCH_AUTO (need at least 2)
        self.sp_invoices = StoragePath.objects.create(
            name="Invoices", slug="invoices",
            path="/invoices/", matching_algorithm=MATCH_AUTO,
        )
        self.sp_contracts = StoragePath.objects.create(
            name="Contracts", slug="contracts",
            path="/contracts/", matching_algorithm=MATCH_AUTO,
        )

        _create_training_data(
            self.user,
            self.tag_invoice, self.tag_contract,
            self.corr_acme, self.corr_globex,
            self.dt_invoice, self.dt_contract,
            self.sp_invoices, self.sp_contracts,
        )

    def _train_classifier(self):
        """Helper to train a classifier and return it with metrics."""
        classifier = DocumentClassifier()
        metrics = classifier.train()
        return classifier, metrics

    def test_train_tags_classifier(self):
        """train() succeeds and tags_classifier is not None."""
        classifier, metrics = self._train_classifier()
        self.assertIsNotNone(classifier.tags_classifier)
        self.assertIsNotNone(classifier.tags_vectorizer)
        self.assertIsNotNone(classifier.tags_binarizer)

    def test_train_correspondent_classifier(self):
        """Correspondent classifier is trained when sufficient data exists."""
        classifier, metrics = self._train_classifier()
        self.assertIsNotNone(classifier.correspondent_classifier)
        self.assertIsNotNone(classifier.correspondent_vectorizer)

    def test_train_document_type_classifier(self):
        """Document type classifier is trained when sufficient data exists."""
        classifier, metrics = self._train_classifier()
        self.assertIsNotNone(classifier.document_type_classifier)
        self.assertIsNotNone(classifier.document_type_vectorizer)

    def test_train_storage_path_classifier(self):
        """Storage path classifier is trained when sufficient data exists."""
        classifier, metrics = self._train_classifier()
        self.assertIsNotNone(classifier.storage_path_classifier)
        self.assertIsNotNone(classifier.storage_path_vectorizer)

    def test_train_returns_metrics(self):
        """Metrics dict has document count, features, and labels for each classifier."""
        classifier, metrics = self._train_classifier()
        self.assertIsInstance(metrics, dict)
        self.assertIn("tags", metrics)
        self.assertIn("correspondent", metrics)
        self.assertIn("document_type", metrics)
        self.assertIn("storage_path", metrics)

        # At least one classifier should have returned metrics
        trained_metrics = {k: v for k, v in metrics.items() if v is not None}
        self.assertGreater(len(trained_metrics), 0)

        # Check structure of trained metrics
        for name, m in trained_metrics.items():
            self.assertIn("documents", m)
            self.assertIn("features", m)
            self.assertIn("labels", m)
            self.assertGreater(m["documents"], 0)

    def test_skip_retraining_unchanged(self):
        """Second call to train() returns None metrics (no changes)."""
        classifier, first_metrics = self._train_classifier()
        # Train again with the same data — hashes should match
        second_metrics = classifier.train()
        for key, value in second_metrics.items():
            self.assertIsNone(
                value,
                f"Expected None for '{key}' on retrain, got {value}",
            )

    def test_predict_tags(self):
        """predict_tags returns a list of (tag_id, confidence) tuples."""
        classifier, _ = self._train_classifier()
        predictions = classifier.predict_tags(
            "invoice payment billing total amount due"
        )
        self.assertIsInstance(predictions, list)
        if predictions:
            tag_id, confidence = predictions[0]
            self.assertIsInstance(tag_id, int)
            self.assertIsInstance(confidence, float)

    def test_predict_correspondent(self):
        """predict_correspondent returns list of (id, confidence) tuples."""
        classifier, _ = self._train_classifier()
        predictions = classifier.predict_correspondent(
            "invoice payment billing total amount due receipt company"
        )
        self.assertIsInstance(predictions, list)
        if predictions:
            corr_id, confidence = predictions[0]
            self.assertIsInstance(corr_id, int)
            self.assertIsInstance(confidence, float)

    def test_predict_document_type(self):
        """predict_document_type returns list of (id, confidence) tuples."""
        classifier, _ = self._train_classifier()
        predictions = classifier.predict_document_type(
            "contract agreement terms conditions signature legal"
        )
        self.assertIsInstance(predictions, list)
        if predictions:
            dt_id, confidence = predictions[0]
            self.assertIsInstance(dt_id, int)
            self.assertIsInstance(confidence, float)

    def test_predict_storage_path(self):
        """predict_storage_path returns list of (id, confidence) tuples."""
        classifier, _ = self._train_classifier()
        predictions = classifier.predict_storage_path(
            "invoice payment billing total amount"
        )
        self.assertIsInstance(predictions, list)
        if predictions:
            sp_id, confidence = predictions[0]
            self.assertIsInstance(sp_id, int)
            self.assertIsInstance(confidence, float)

    def test_predict_empty_content(self):
        """Predicting with empty content returns an empty list."""
        classifier, _ = self._train_classifier()
        self.assertEqual(classifier.predict_tags(""), [])
        self.assertEqual(classifier.predict_correspondent(""), [])
        self.assertEqual(classifier.predict_document_type(""), [])
        self.assertEqual(classifier.predict_storage_path(""), [])

    def test_predict_whitespace_only_content(self):
        """Predicting with whitespace-only content returns empty list."""
        classifier, _ = self._train_classifier()
        self.assertEqual(classifier.predict_tags("   "), [])
        self.assertEqual(classifier.predict_correspondent("   \n\t  "), [])

    def test_no_classifier_returns_empty(self):
        """Before training, predictions return empty lists."""
        classifier = DocumentClassifier()
        self.assertEqual(classifier.predict_tags("invoice payment"), [])
        self.assertEqual(classifier.predict_correspondent("invoice payment"), [])
        self.assertEqual(classifier.predict_document_type("invoice payment"), [])
        self.assertEqual(classifier.predict_storage_path("invoice payment"), [])


class DocumentClassifierInsufficientDataTest(TestCase):
    """Tests for classifier behavior with insufficient training data."""

    def setUp(self):
        self.user = User.objects.create_user("mluser2", password="testpass123")

    def test_no_auto_objects_no_training(self):
        """Without MATCH_AUTO objects, no classifiers are trained."""
        corr = Correspondent.objects.create(
            name="Test Corp", slug="test-corp",
            matching_algorithm=MATCH_NONE,
        )
        for i in range(6):
            Document.objects.create(
                title=f"Doc {i}",
                content="some content here for testing purposes and more words",
                correspondent=corr,
                filename=f"doc_{i}.pdf",
                owner=self.user,
            )

        classifier = DocumentClassifier()
        metrics = classifier.train()

        self.assertIsNone(classifier.tags_classifier)
        self.assertIsNone(classifier.correspondent_classifier)
        self.assertIsNone(metrics["correspondent"])

    def test_single_label_value_no_training(self):
        """Single-label classifiers need at least 2 unique labels."""
        corr = Correspondent.objects.create(
            name="Only Corp", slug="only-corp",
            matching_algorithm=MATCH_AUTO,
        )
        # Use varied content so CountVectorizer doesn't prune all terms,
        # but assign all documents to the same correspondent (single label)
        varied_contents = [
            "invoice payment billing total amount due receipt company account",
            "monthly statement billing period accounts receivable payment net",
            "purchase order vendor supplier payment remittance banking details",
            "billing summary charges taxes shipping handling merchant processing",
            "accounts payable approval workflow payment schedule budget fiscal",
            "overdue reminder balance outstanding payment required immediate",
        ]
        for i, content in enumerate(varied_contents):
            Document.objects.create(
                title=f"Doc {i}",
                content=content,
                correspondent=corr,
                filename=f"single_label_doc_{i}.pdf",
                owner=self.user,
            )

        classifier = DocumentClassifier()
        metrics = classifier.train()
        self.assertIsNone(classifier.correspondent_classifier)


class ClassifierSerializationTest(TestCase):
    """Tests for classifier save/load serialization."""

    def setUp(self):
        self.user = User.objects.create_user("mlseruser", password="testpass123")
        self.temp_dir = tempfile.mkdtemp()

        # Create training data using the same varied content
        self.tag = Tag.objects.create(
            name="SerTag", slug="sertag",
            matching_algorithm=MATCH_AUTO, color="#abcdef",
        )
        tag2 = Tag.objects.create(
            name="SerTag2", slug="sertag2",
            matching_algorithm=MATCH_AUTO, color="#fedcba",
        )
        corr1 = Correspondent.objects.create(
            name="Ser Corp A", slug="ser-corp-a",
            matching_algorithm=MATCH_AUTO,
        )
        corr2 = Correspondent.objects.create(
            name="Ser Corp B", slug="ser-corp-b",
            matching_algorithm=MATCH_AUTO,
        )
        dt1 = DocumentType.objects.create(
            name="SerType A", slug="sertype-a",
            matching_algorithm=MATCH_AUTO,
        )
        dt2 = DocumentType.objects.create(
            name="SerType B", slug="sertype-b",
            matching_algorithm=MATCH_AUTO,
        )
        sp1 = StoragePath.objects.create(
            name="SerPath A", slug="serpath-a",
            path="/ser-a/", matching_algorithm=MATCH_AUTO,
        )
        sp2 = StoragePath.objects.create(
            name="SerPath B", slug="serpath-b",
            path="/ser-b/", matching_algorithm=MATCH_AUTO,
        )

        _create_training_data(
            self.user,
            self.tag, tag2,
            corr1, corr2,
            dt1, dt2,
            sp1, sp2,
        )

    @override_settings(MEDIA_ROOT="")
    def test_save_and_load(self):
        """Train, save, load -> loaded classifier can predict."""
        with self.settings(MEDIA_ROOT=self.temp_dir):
            classifier = DocumentClassifier()
            classifier.train()
            classifier.save()

            loaded = DocumentClassifier.load()
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.format_version, MODEL_FORMAT_VERSION)

            # Loaded classifier should be able to predict
            predictions = loaded.predict_correspondent(
                "invoice payment billing total amount"
            )
            self.assertIsInstance(predictions, list)

    @override_settings(MEDIA_ROOT="")
    def test_load_nonexistent(self):
        """load() returns None when no serialized file exists."""
        with self.settings(MEDIA_ROOT=self.temp_dir):
            result = DocumentClassifier.load()
            self.assertIsNone(result)

    @override_settings(MEDIA_ROOT="")
    def test_format_version_mismatch(self):
        """Corrupted version returns None on load."""
        with self.settings(MEDIA_ROOT=self.temp_dir):
            classifier = DocumentClassifier()
            classifier.train()
            # Tamper with the format version before saving
            classifier.format_version = 999
            classifier.save()

            loaded = DocumentClassifier.load()
            self.assertIsNone(loaded)

    @override_settings(MEDIA_ROOT="")
    def test_corrupted_file_returns_none(self):
        """A corrupted pickle file returns None on load."""
        with self.settings(MEDIA_ROOT=self.temp_dir):
            model_dir = os.path.join(self.temp_dir, "ml_models")
            os.makedirs(model_dir, exist_ok=True)
            path = os.path.join(model_dir, "classifier.pkl")
            with open(path, "wb") as f:
                f.write(b"this is not valid pickle data")

            loaded = DocumentClassifier.load()
            self.assertIsNone(loaded)
