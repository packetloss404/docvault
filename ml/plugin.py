"""Classification plugin for the document processing pipeline."""

import logging

from processing.context import PluginResult, ProcessingContext
from processing.plugins.base import ProcessingPlugin

logger = logging.getLogger(__name__)


class ClassificationPlugin(ProcessingPlugin):
    """ML-based document classification plugin.

    Runs after document storage (order=100, between StorePlugin at 90
    and ThumbnailPlugin at 130). Loads the trained classifier and
    populates the ProcessingContext with suggestions.

    Predictions are only applied to fields whose matching objects use
    MATCH_AUTO. Otherwise they are stored as suggestions for user review.
    """

    name = "ClassificationPlugin"
    order = 100

    def can_run(self, context: ProcessingContext) -> bool:
        """Only run if there's content to classify."""
        return bool(context.content and context.content.strip())

    def process(self, context: ProcessingContext) -> PluginResult:
        self.update_progress(context, 0.75, "Running ML classification...")

        from .classifier import get_classifier

        classifier = get_classifier()
        if classifier is None:
            logger.debug("No trained classifier available, skipping classification")
            return PluginResult(success=True, message="No classifier available")

        content = context.content

        # Predict tags
        tag_predictions = classifier.predict_tags(content)
        if tag_predictions and not context.override_tags:
            context.suggested_tags = [tid for tid, _ in tag_predictions]

        # Predict correspondent
        corr_predictions = classifier.predict_correspondent(content)
        if corr_predictions and not context.override_correspondent:
            context.suggested_correspondent = corr_predictions[0][0]

        # Predict document type
        dt_predictions = classifier.predict_document_type(content)
        if dt_predictions and not context.override_document_type:
            context.suggested_document_type = dt_predictions[0][0]

        # Predict storage path
        sp_predictions = classifier.predict_storage_path(content)
        if sp_predictions:
            context.suggested_storage_path = sp_predictions[0][0]

        logger.info(
            "Classification complete: tags=%d, correspondent=%s, type=%s, path=%s",
            len(context.suggested_tags),
            context.suggested_correspondent,
            context.suggested_document_type,
            context.suggested_storage_path,
        )

        return PluginResult(
            success=True,
            message="Classification complete",
        )
