"""Celery tasks for ML classification."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def train_classifier():
    """Train the document classifier on current data.

    Scheduled to run hourly via Celery Beat. Uses hash-based
    change detection to skip retraining when data hasn't changed.
    """
    from .classifier import DocumentClassifier, reload_classifier

    # Load existing or create new
    classifier = DocumentClassifier.load() or DocumentClassifier()

    try:
        metrics = classifier.train()
        classifier.save()
        reload_classifier()

        trained = {k: v for k, v in metrics.items() if v is not None}
        if trained:
            logger.info("Classifier training complete: %s", trained)
        else:
            logger.info("No classifiers needed retraining (data unchanged)")

        return {
            "status": "success",
            "trained": list(trained.keys()),
            "metrics": metrics,
        }

    except Exception:
        logger.exception("Classifier training failed")
        raise


@shared_task
def reclassify_documents(document_ids=None):
    """Re-classify existing documents using the trained classifier.

    If document_ids is None, re-classifies all documents.
    Stores suggestions but does not auto-apply them.
    """
    from documents.models import Document

    from .classifier import get_classifier

    classifier = get_classifier()
    if classifier is None:
        logger.warning("No trained classifier available")
        return {"status": "skipped", "reason": "no_classifier"}

    if document_ids:
        docs = Document.objects.filter(id__in=document_ids)
    else:
        docs = Document.objects.filter(content__gt="")

    results = []
    for doc in docs.iterator():
        suggestions = get_suggestions_for_document(doc, classifier)
        if any(suggestions.values()):
            results.append({"document_id": doc.id, "suggestions": suggestions})

    logger.info("Re-classified %d documents with suggestions", len(results))
    return {"status": "success", "count": len(results)}


def get_suggestions_for_document(document, classifier=None):
    """Get ML suggestions for a document.

    Returns dict with tags, correspondent, document_type, storage_path.
    """
    from .classifier import get_classifier as _get_classifier

    if classifier is None:
        classifier = _get_classifier()

    if classifier is None:
        return {
            "tags": [],
            "correspondent": [],
            "document_type": [],
            "storage_path": [],
        }

    content = document.content or ""
    if not content.strip():
        return {
            "tags": [],
            "correspondent": [],
            "document_type": [],
            "storage_path": [],
        }

    return {
        "tags": [
            {"id": tid, "confidence": conf}
            for tid, conf in classifier.predict_tags(content)
        ],
        "correspondent": [
            {"id": cid, "confidence": conf}
            for cid, conf in classifier.predict_correspondent(content)
        ],
        "document_type": [
            {"id": dtid, "confidence": conf}
            for dtid, conf in classifier.predict_document_type(content)
        ],
        "storage_path": [
            {"id": spid, "confidence": conf}
            for spid, conf in classifier.predict_storage_path(content)
        ],
    }
