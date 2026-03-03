"""Celery tasks for search indexing."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="search.index_document")
def index_document_task(document_id):
    """Index a single document asynchronously."""
    from documents.models import Document
    from .indexing import index_document

    try:
        document = (
            Document.objects
            .select_related(
                "correspondent", "document_type", "cabinet", "storage_path",
            )
            .prefetch_related("tags", "custom_field_instances__field")
            .get(pk=document_id)
        )
        index_document(document)
    except Document.DoesNotExist:
        logger.warning("Document %s not found for indexing.", document_id)


@shared_task(name="search.remove_document")
def remove_document_task(document_id):
    """Remove a document from the index asynchronously."""
    from .indexing import remove_document
    remove_document(document_id)


@shared_task(name="search.rebuild_index")
def rebuild_index_task():
    """Rebuild the entire search index."""
    from .indexing import rebuild_index
    count = rebuild_index()
    logger.info("Index rebuild complete. %d documents indexed.", count)
    return count


@shared_task(name="search.optimize_index")
def optimize_index_task():
    """Optimize the search index (force merge)."""
    from .client import get_client, get_index_name

    client = get_client()
    if not client:
        return

    client.indices.forcemerge(
        index=get_index_name(),
        max_num_segments=1,
    )
    logger.info("Index optimization complete.")
