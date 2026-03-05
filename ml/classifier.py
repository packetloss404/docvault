"""Document classifier — four sub-classifiers for auto-assignment.

Implements the Paperless-ngx classification approach using scikit-learn:
- tags_classifier: multi-label (MLPClassifier + MultiLabelBinarizer)
- correspondent_classifier: single-label (MLPClassifier)
- document_type_classifier: single-label (MLPClassifier)
- storage_path_classifier: single-label (MLPClassifier)
"""

import hashlib
import logging
import pickle
from pathlib import Path

from django.conf import settings

from .preprocessing import preprocess

logger = logging.getLogger(__name__)

# Model format version — bump when changing serialization format
MODEL_FORMAT_VERSION = 1

# Minimum documents required to train a classifier
MIN_TRAINING_DOCS = 5


def _get_model_dir() -> Path:
    """Return the directory for storing serialized models."""
    model_dir = Path(settings.MEDIA_ROOT) / "ml_models"
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir


class DocumentClassifier:
    """Four-classifier system for document auto-assignment.

    Each sub-classifier is trained independently on documents that use
    MATCH_AUTO for the corresponding field.
    """

    def __init__(self):
        self.tags_classifier = None
        self.correspondent_classifier = None
        self.document_type_classifier = None
        self.storage_path_classifier = None

        # Vectorizers (one per classifier for independent vocabularies)
        self.tags_vectorizer = None
        self.correspondent_vectorizer = None
        self.document_type_vectorizer = None
        self.storage_path_vectorizer = None

        # For multi-label tags
        self.tags_binarizer = None

        # Training data hashes for change detection
        self.tags_data_hash = ""
        self.correspondent_data_hash = ""
        self.document_type_data_hash = ""
        self.storage_path_data_hash = ""

        self.format_version = MODEL_FORMAT_VERSION

    def train(self):
        """Train all four classifiers on current data.

        Only trains classifiers where the data has changed since
        the last training run (hash-based change detection).
        """
        from sklearn.feature_extraction.text import CountVectorizer
        from sklearn.neural_network import MLPClassifier
        from sklearn.preprocessing import MultiLabelBinarizer

        from documents.constants import MATCH_AUTO
        from documents.models import Document
        from organization.models import Correspondent, StoragePath, Tag

        metrics = {
            "tags": None,
            "correspondent": None,
            "document_type": None,
            "storage_path": None,
        }

        # --- Tags classifier (multi-label) ---
        tags_with_auto = Tag.objects.filter(matching_algorithm=MATCH_AUTO)
        if tags_with_auto.exists():
            auto_tag_ids = set(tags_with_auto.values_list("id", flat=True))
            docs = Document.objects.filter(
                tags__in=auto_tag_ids
            ).distinct().prefetch_related("tags")

            if docs.count() >= MIN_TRAINING_DOCS:
                contents = []
                labels = []
                for doc in docs:
                    preprocessed = preprocess(doc.content)
                    if not preprocessed.strip():
                        continue
                    contents.append(preprocessed)
                    doc_tag_ids = [
                        t.id for t in doc.tags.all() if t.id in auto_tag_ids
                    ]
                    labels.append(doc_tag_ids)

                data_hash = _compute_hash(contents, labels)
                if data_hash != self.tags_data_hash and len(contents) >= MIN_TRAINING_DOCS:
                    vectorizer = CountVectorizer(
                        ngram_range=(1, 2), min_df=0.01, max_df=0.95,
                    )
                    X = vectorizer.fit_transform(contents)

                    binarizer = MultiLabelBinarizer()
                    y = binarizer.fit_transform(labels)

                    clf = MLPClassifier(
                        hidden_layer_sizes=(100,),
                        max_iter=500,
                        random_state=42,
                        early_stopping=True,
                    )
                    clf.fit(X, y)

                    self.tags_classifier = clf
                    self.tags_vectorizer = vectorizer
                    self.tags_binarizer = binarizer
                    self.tags_data_hash = data_hash

                    metrics["tags"] = {
                        "documents": len(contents),
                        "features": X.shape[1],
                        "labels": len(binarizer.classes_),
                    }
                    logger.info(
                        "Tags classifier trained: %d docs, %d features, %d labels",
                        len(contents), X.shape[1], len(binarizer.classes_),
                    )

        # --- Correspondent classifier (single-label) ---
        metrics["correspondent"] = self._train_single_label(
            "correspondent",
            Document.objects.filter(
                correspondent__matching_algorithm=MATCH_AUTO,
                correspondent__isnull=False,
            ),
            lambda doc: doc.correspondent_id,
        )

        # --- Document type classifier (single-label) ---
        metrics["document_type"] = self._train_single_label(
            "document_type",
            Document.objects.filter(
                document_type__matching_algorithm=MATCH_AUTO,
                document_type__isnull=False,
            ),
            lambda doc: doc.document_type_id,
        )

        # --- Storage path classifier (single-label) ---
        metrics["storage_path"] = self._train_single_label(
            "storage_path",
            Document.objects.filter(
                storage_path__matching_algorithm=MATCH_AUTO,
                storage_path__isnull=False,
            ),
            lambda doc: doc.storage_path_id,
        )

        return metrics

    def _train_single_label(self, name, queryset, label_fn):
        """Train a single-label classifier for a given field."""
        from sklearn.feature_extraction.text import CountVectorizer
        from sklearn.neural_network import MLPClassifier

        docs = list(queryset)
        if len(docs) < MIN_TRAINING_DOCS:
            return None

        contents = []
        labels = []
        for doc in docs:
            preprocessed = preprocess(doc.content)
            if not preprocessed.strip():
                continue
            contents.append(preprocessed)
            labels.append(label_fn(doc))

        if len(contents) < MIN_TRAINING_DOCS:
            return None

        data_hash = _compute_hash(contents, labels)
        current_hash = getattr(self, f"{name}_data_hash")
        if data_hash == current_hash:
            return None  # No changes

        vectorizer = CountVectorizer(
            ngram_range=(1, 2), min_df=0.01, max_df=0.95,
        )
        X = vectorizer.fit_transform(contents)
        unique_labels = set(labels)
        if len(unique_labels) < 2:
            return None  # Need at least 2 classes

        clf = MLPClassifier(
            hidden_layer_sizes=(100,),
            max_iter=500,
            random_state=42,
            early_stopping=True,
        )
        clf.fit(X, labels)

        setattr(self, f"{name}_classifier", clf)
        setattr(self, f"{name}_vectorizer", vectorizer)
        setattr(self, f"{name}_data_hash", data_hash)

        metrics = {
            "documents": len(contents),
            "features": X.shape[1],
            "labels": len(unique_labels),
        }
        logger.info(
            "%s classifier trained: %d docs, %d features, %d labels",
            name, len(contents), X.shape[1], len(unique_labels),
        )
        return metrics

    def predict_tags(self, content: str, threshold=0.5):
        """Predict tags for document content.

        Returns list of (tag_id, confidence) tuples.
        """
        if self.tags_classifier is None or self.tags_vectorizer is None:
            return []

        preprocessed = preprocess(content)
        if not preprocessed.strip():
            return []

        X = self.tags_vectorizer.transform([preprocessed])
        probas = self.tags_classifier.predict_proba(X)

        results = []
        for i, tag_id in enumerate(self.tags_binarizer.classes_):
            # For multi-output, probas is a list of arrays
            if isinstance(probas, list):
                confidence = float(probas[i][0][1]) if probas[i].shape[1] > 1 else float(probas[i][0][0])
            else:
                confidence = float(probas[0][i]) if probas.shape[1] > len(self.tags_binarizer.classes_) else threshold + 0.01
            if confidence >= threshold:
                results.append((int(tag_id), confidence))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def predict_correspondent(self, content: str):
        """Predict correspondent. Returns list of (id, confidence) tuples."""
        return self._predict_single("correspondent", content)

    def predict_document_type(self, content: str):
        """Predict document type. Returns list of (id, confidence) tuples."""
        return self._predict_single("document_type", content)

    def predict_storage_path(self, content: str):
        """Predict storage path. Returns list of (id, confidence) tuples."""
        return self._predict_single("storage_path", content)

    def _predict_single(self, name, content):
        """Generic single-label prediction."""
        clf = getattr(self, f"{name}_classifier")
        vectorizer = getattr(self, f"{name}_vectorizer")
        if clf is None or vectorizer is None:
            return []

        preprocessed = preprocess(content)
        if not preprocessed.strip():
            return []

        X = vectorizer.transform([preprocessed])
        probas = clf.predict_proba(X)[0]
        classes = clf.classes_

        results = [
            (int(classes[i]), float(probas[i]))
            for i in range(len(classes))
            if probas[i] > 0.01
        ]
        return sorted(results, key=lambda x: x[1], reverse=True)

    def save(self):
        """Serialize the classifier to disk."""
        model_dir = _get_model_dir()
        path = model_dir / "classifier.pkl"
        with open(path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info("Classifier saved to %s", path)

    @classmethod
    def load(cls):
        """Load the classifier from disk. Returns None if not available."""
        model_dir = _get_model_dir()
        path = model_dir / "classifier.pkl"
        if not path.exists():
            return None

        try:
            with open(path, "rb") as f:
                classifier = pickle.load(f)
            if not isinstance(classifier, cls):
                logger.warning("Invalid classifier file format")
                return None
            if classifier.format_version != MODEL_FORMAT_VERSION:
                logger.warning(
                    "Model format version mismatch: %s != %s",
                    classifier.format_version, MODEL_FORMAT_VERSION,
                )
                return None
            return classifier
        except Exception:
            logger.exception("Failed to load classifier from %s", path)
            return None


def _compute_hash(contents, labels):
    """Compute a hash of training data for change detection."""
    h = hashlib.sha256()
    for c in contents:
        h.update(c.encode("utf-8", errors="ignore"))
    h.update(str(labels).encode("utf-8"))
    return h.hexdigest()


# Module-level cached classifier instance
_classifier_instance = None


def get_classifier() -> DocumentClassifier | None:
    """Get the cached classifier instance, loading from disk if needed."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = DocumentClassifier.load()
    return _classifier_instance


def reload_classifier():
    """Force reload the classifier from disk."""
    global _classifier_instance
    _classifier_instance = DocumentClassifier.load()
    return _classifier_instance
