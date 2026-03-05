"""AI plugin for the document processing pipeline."""

import logging

from processing.context import PluginResult, ProcessingContext
from processing.plugins.base import ProcessingPlugin

logger = logging.getLogger(__name__)


class AIPlugin(ProcessingPlugin):
    """Generate document embeddings during the processing pipeline.

    Runs after ClassificationPlugin (order=110, between ClassificationPlugin
    at 100 and ThumbnailPlugin at 130). Generates an embedding vector and
    adds it to the FAISS vector store.
    """

    name = "AIPlugin"
    order = 110

    def can_run(self, context: ProcessingContext) -> bool:
        """Only run if LLM is enabled and there's content."""
        from django.conf import settings

        return (
            getattr(settings, "LLM_ENABLED", False)
            and bool(context.content and context.content.strip())
        )

    def process(self, context: ProcessingContext) -> PluginResult:
        self.update_progress(context, 0.80, "Generating document embedding...")

        if not context.document_id:
            return PluginResult(
                success=True,
                message="No document_id yet, skipping embedding",
            )

        try:
            from documents.models import Document

            document = Document.objects.select_related(
                "correspondent", "document_type",
            ).prefetch_related("tags").get(pk=context.document_id)

            from .embeddings import generate_document_embedding
            from .vector_store import get_vector_store

            embedding = generate_document_embedding(document)
            if embedding:
                store = get_vector_store()
                store.add(document.pk, embedding)
                store.save()
                logger.info("Generated and stored embedding for document %s", document.pk)
            else:
                logger.debug("No embedding generated for document %s", document.pk)

        except Exception as e:
            logger.warning("AI embedding failed for document %s: %s", context.document_id, e)
            return PluginResult(success=True, message=f"Embedding failed (non-fatal): {e}")

        return PluginResult(success=True, message="Embedding generated")
