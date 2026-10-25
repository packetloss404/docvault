import numpy as np
import pytest
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import MultiLabelBinarizer

from ml.classifier import DocumentClassifier, get_classifier, reload_classifier
from ml.preprocessing import preprocess


@pytest.mark.parametrize("labels", [[[11], [22], [11], [22]], [[11], [], [11], []]])
def test_tag_confidence_matches_actual_classifier_probabilities(labels):
    contents = ["invoice payment", "contract clause", "invoice billing", "contract agreement"]
    classifier = DocumentClassifier()
    classifier.tags_vectorizer = CountVectorizer()
    features = classifier.tags_vectorizer.fit_transform([preprocess(text) for text in contents])
    classifier.tags_binarizer = MultiLabelBinarizer()
    targets = classifier.tags_binarizer.fit_transform(labels)
    classifier.tags_classifier = MLPClassifier(hidden_layer_sizes=(5,), max_iter=1000, random_state=42)
    classifier.tags_classifier.fit(features, targets)
    expected = classifier.tags_classifier.predict_proba(
        classifier.tags_vectorizer.transform([preprocess("invoice payment")]),
    )[0]
    actual = dict(classifier.predict_tags("invoice payment", threshold=0))
    if len(classifier.tags_binarizer.classes_) == 1:
        assert actual[11] == pytest.approx(expected[1])
    else:
        np.testing.assert_allclose([actual[int(tag)] for tag in classifier.tags_binarizer.classes_], expected)


def test_web_process_reloads_classifier_published_by_worker(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    try:
        first = DocumentClassifier()
        first.tags_data_hash = "old"
        first.save()
        assert reload_classifier().tags_data_hash == "old"
        second = DocumentClassifier()
        second.tags_data_hash = "new-worker-model"
        second.save()
        assert get_classifier().tags_data_hash == "new-worker-model"
    finally:
        settings.MEDIA_ROOT = tmp_path / "reset"
        reload_classifier()
