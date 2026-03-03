"""Celery tasks for AI operations."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="ai.update_vector_index")
def update_vector_index():
    """Update the vector index for documents that need embedding.

    Finds documents without embeddings and generates them.
    Scheduled to run daily.
    """
    from django.conf import settings

    if not getattr(settings, "LLM_ENABLED", False):
        logger.debug("LLM not enabled, skipping vector index update")
        return {"status": "skipped", "reason": "LLM not enabled"}

    from documents.models import Document

    from .embeddings import generate_document_embedding
    from .vector_store import get_vector_store

    store = get_vector_store()
    existing_ids = set(doc_id for doc_id in store.doc_ids if doc_id != -1)

    documents = (
        Document.objects
        .select_related("correspondent", "document_type")
        .prefetch_related("tags")
        .exclude(content="")
        .exclude(pk__in=existing_ids)
    )

    added = 0
    failed = 0
    for doc in documents.iterator():
        try:
            embedding = generate_document_embedding(doc)
            if embedding:
                store.add(doc.pk, embedding)
                added += 1
        except Exception as e:
            logger.warning("Failed to generate embedding for document %s: %s", doc.pk, e)
            failed += 1

    if added > 0:
        store.save()

    logger.info("Vector index update complete: %d added, %d failed", added, failed)
    return {"status": "complete", "added": added, "failed": failed}


@shared_task(name="ai.rebuild_vector_index")
def rebuild_vector_index():
    """Rebuild the entire vector index from scratch."""
    from django.conf import settings

    if not getattr(settings, "LLM_ENABLED", False):
        return {"status": "skipped", "reason": "LLM not enabled"}

    from documents.models import Document

    from .client import get_llm_client
    from .embeddings import build_embedding_text
    from .vector_store import VectorStore

    client = get_llm_client()
    if not client:
        return {"status": "skipped", "reason": "No LLM client"}

    documents = (
        Document.objects
        .select_related("correspondent", "document_type")
        .prefetch_related("tags")
        .exclude(content="")
    )

    doc_ids = []
    embeddings = []
    failed = 0

    batch_texts = []
    batch_ids = []
    batch_size = 32

    for doc in documents.iterator():
        text = build_embedding_text(doc)
        if not text.strip():
            continue

        batch_texts.append(text)
        batch_ids.append(doc.pk)

        if len(batch_texts) >= batch_size:
            try:
                batch_embeddings = client.embed_batch(batch_texts)
                doc_ids.extend(batch_ids)
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.warning("Batch embedding failed: %s", e)
                failed += len(batch_texts)

            batch_texts = []
            batch_ids = []

    # Process remaining
    if batch_texts:
        try:
            batch_embeddings = client.embed_batch(batch_texts)
            doc_ids.extend(batch_ids)
            embeddings.extend(batch_embeddings)
        except Exception as e:
            logger.warning("Final batch embedding failed: %s", e)
            failed += len(batch_texts)

    store = VectorStore(dimension=client.embedding_dimension)
    store.rebuild(doc_ids, embeddings)
    store.save()

    logger.info(
        "Vector index rebuild complete: %d indexed, %d failed",
        len(doc_ids), failed,
    )
    return {"status": "complete", "indexed": len(doc_ids), "failed": failed}
