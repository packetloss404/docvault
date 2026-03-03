"""Semantic search and hybrid search combining Elasticsearch + FAISS."""

import logging

from .constants import HYBRID_KEYWORD_WEIGHT, HYBRID_SEMANTIC_WEIGHT, VECTOR_SEARCH_K
from .embeddings import generate_query_embedding
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


def semantic_search(query: str, k: int = VECTOR_SEARCH_K, user_id: int | None = None) -> list[dict]:
    """Perform semantic search using FAISS vector similarity.

    Args:
        query: Natural language search query.
        k: Maximum number of results.
        user_id: Optional user ID for permission filtering.

    Returns:
        List of result dicts with document_id, score, title, etc.
    """
    embedding = generate_query_embedding(query)
    if embedding is None:
        return []

    store = get_vector_store()
    raw_results = store.search(embedding, k=k * 2)  # Fetch extra for permission filtering

    if not raw_results:
        return []

    from documents.models import Document

    doc_ids = [doc_id for doc_id, _ in raw_results]
    score_map = {doc_id: score for doc_id, score in raw_results}

    qs = Document.objects.select_related(
        "correspondent", "document_type",
    ).prefetch_related("tags").filter(pk__in=doc_ids)

    if user_id:
        qs = qs.filter(owner_id=user_id)

    results = []
    for doc in qs:
        results.append({
            "id": doc.pk,
            "title": doc.title,
            "correspondent": doc.correspondent.name if doc.correspondent else None,
            "document_type": doc.document_type.name if doc.document_type else None,
            "tags": [t.name for t in doc.tags.all()],
            "created": doc.created.isoformat() if doc.created else None,
            "score": score_map.get(doc.pk, 0.0),
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:k]


def find_similar_documents(
    document_id: int, k: int = VECTOR_SEARCH_K, user_id: int | None = None
) -> list[dict]:
    """Find documents similar to a given document using vector similarity.

    Args:
        document_id: The ID of the source document.
        k: Maximum number of similar documents.
        user_id: Optional user ID for permission filtering.

    Returns:
        List of similar document dicts.
    """
    from documents.models import Document

    try:
        document = Document.objects.select_related(
            "correspondent", "document_type",
        ).prefetch_related("tags").get(pk=document_id)
    except Document.DoesNotExist:
        return []

    from .embeddings import generate_document_embedding

    embedding = generate_document_embedding(document)
    if embedding is None:
        return []

    store = get_vector_store()
    raw_results = store.search(embedding, k=k + 5)

    if not raw_results:
        return []

    # Exclude the source document
    doc_ids = [doc_id for doc_id, _ in raw_results if doc_id != document_id]
    score_map = {doc_id: score for doc_id, score in raw_results}

    qs = Document.objects.select_related(
        "correspondent", "document_type",
    ).prefetch_related("tags").filter(pk__in=doc_ids)

    if user_id:
        qs = qs.filter(owner_id=user_id)

    results = []
    for doc in qs:
        results.append({
            "id": doc.pk,
            "title": doc.title,
            "correspondent": doc.correspondent.name if doc.correspondent else None,
            "document_type": doc.document_type.name if doc.document_type else None,
            "tags": [t.name for t in doc.tags.all()],
            "created": doc.created.isoformat() if doc.created else None,
            "score": score_map.get(doc.pk, 0.0),
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:k]


def hybrid_search(
    query: str,
    k: int = VECTOR_SEARCH_K,
    user_id: int | None = None,
    keyword_weight: float = HYBRID_KEYWORD_WEIGHT,
    semantic_weight: float = HYBRID_SEMANTIC_WEIGHT,
) -> list[dict]:
    """Combine keyword (Elasticsearch) and semantic (FAISS) search results.

    Uses reciprocal rank fusion to merge the two result sets.
    """
    from search.query import execute_search

    # Keyword search
    keyword_results = execute_search(
        query_text=query,
        user_id=user_id,
        page=1,
        page_size=k * 2,
    )

    # Semantic search
    sem_results = semantic_search(query, k=k * 2, user_id=user_id)

    # Reciprocal Rank Fusion
    rrf_constant = 60
    scores: dict[int, float] = {}
    doc_data: dict[int, dict] = {}

    for rank, result in enumerate(keyword_results.get("results", [])):
        doc_id = result.get("id")
        if doc_id is None:
            continue
        rrf_score = keyword_weight / (rrf_constant + rank + 1)
        scores[doc_id] = scores.get(doc_id, 0) + rrf_score
        doc_data[doc_id] = result

    for rank, result in enumerate(sem_results):
        doc_id = result["id"]
        rrf_score = semantic_weight / (rrf_constant + rank + 1)
        scores[doc_id] = scores.get(doc_id, 0) + rrf_score
        if doc_id not in doc_data:
            doc_data[doc_id] = result

    # Sort by combined score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]

    results = []
    for doc_id, score in ranked:
        entry = doc_data[doc_id].copy()
        entry["hybrid_score"] = score
        results.append(entry)

    return results
