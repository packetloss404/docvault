"""Search query building and execution."""

import logging
import re

from .client import get_client, get_index_name

logger = logging.getLogger(__name__)


def _load_synonyms():
    """Load all enabled synonym groups from the database.

    Returns a list of term sets, e.g. [{'invoice', 'bill', 'receipt'}, ...].
    Imported lazily to avoid circular imports at module load time.
    """
    try:
        from .models import SearchSynonym
        groups = SearchSynonym.objects.filter(enabled=True).values_list("terms", flat=True)
        return [set(t) for t in groups if t]
    except Exception:
        logger.exception("Failed to load search synonyms")
        return []


def _expand_query_with_synonyms(query_text, synonym_groups):
    """Expand query_text with synonyms.

    For each word token in the query that appears in a synonym group, all
    synonyms from that group are appended to the query so Elasticsearch
    can match any of them.  The original token is preserved.

    Example:
        query = "invoice", groups = [{"invoice", "bill"}]
        -> "invoice bill"
    """
    if not synonym_groups or not query_text.strip():
        return query_text

    # Tokenise on whitespace; preserve field:value tokens intact
    tokens = query_text.split()
    extra_terms = []
    for token in tokens:
        # Skip field-specific tokens (contain ':')
        if ":" in token:
            continue
        token_lower = token.lower().strip("\"'")
        for group in synonym_groups:
            if token_lower in group:
                for synonym in group:
                    if synonym != token_lower:
                        extra_terms.append(synonym)
                break  # A term belongs to at most one group
    if extra_terms:
        return query_text + " " + " ".join(extra_terms)
    return query_text


def _load_curation(query_text):
    """Return the active SearchCuration for *query_text*, or None."""
    try:
        from .models import SearchCuration
        return (
            SearchCuration.objects
            .filter(query_text__iexact=query_text.strip(), enabled=True)
            .prefetch_related("pinned_documents", "hidden_documents")
            .first()
        )
    except Exception:
        logger.exception("Failed to load search curation")
        return None


def build_search_query(
    query_text,
    user_id=None,
    filters=None,
    page=1,
    page_size=25,
):
    """
    Build an Elasticsearch query body from search parameters.

    Supports:
    - Full-text search across title, content, original_filename
    - Field-specific queries: tag:invoice, correspondent:acme, type:invoice
    - Date range: created:[2025-01-01 TO 2025-12-31]
    - Permission filtering by owner_id
    """
    must_clauses = []
    filter_clauses = []

    # Parse field-specific queries out of the query text
    remaining_text, field_queries = _parse_field_queries(query_text)

    # Main text query
    if remaining_text.strip():
        must_clauses.append({
            "multi_match": {
                "query": remaining_text.strip(),
                "fields": ["title^3", "content", "original_filename"],
                "type": "best_fields",
                "fuzziness": "AUTO",
            },
        })

    # Field-specific queries
    for field, value in field_queries:
        if field == "tag":
            filter_clauses.append({"term": {"tags": value}})
        elif field == "correspondent":
            must_clauses.append({"match": {"correspondent": value}})
        elif field == "type":
            must_clauses.append({"match": {"document_type": value}})
        elif field == "cabinet":
            must_clauses.append({"match": {"cabinet": value}})
        elif field == "lang" or field == "language":
            filter_clauses.append({"term": {"language": value}})
        elif field == "mime":
            filter_clauses.append({"term": {"mime_type": value}})
        elif field == "created":
            date_range = _parse_date_range(value)
            if date_range:
                filter_clauses.append({"range": {"created": date_range}})

    # Permission filter
    if user_id:
        filter_clauses.append({"term": {"owner_id": user_id}})

    # Additional filters
    if filters:
        if filters.get("document_type_id"):
            filter_clauses.append(
                {"term": {"document_type_id": filters["document_type_id"]}},
            )
        if filters.get("correspondent_id"):
            filter_clauses.append(
                {"term": {"correspondent_id": filters["correspondent_id"]}},
            )
        if filters.get("tag_ids"):
            for tag_id in filters["tag_ids"]:
                filter_clauses.append({"term": {"tag_ids": tag_id}})
        if filters.get("cabinet_id"):
            filter_clauses.append(
                {"term": {"cabinet_id": filters["cabinet_id"]}},
            )
        if filters.get("created_after"):
            filter_clauses.append(
                {"range": {"created": {"gte": filters["created_after"]}}},
            )
        if filters.get("created_before"):
            filter_clauses.append(
                {"range": {"created": {"lte": filters["created_before"]}}},
            )
        if filters.get("language"):
            filter_clauses.append({"term": {"language": filters["language"]}})
        if filters.get("mime_type"):
            filter_clauses.append({"term": {"mime_type": filters["mime_type"]}})

    # Build the final query
    if not must_clauses and not filter_clauses:
        es_query = {"match_all": {}}
    else:
        bool_query = {}
        if must_clauses:
            bool_query["must"] = must_clauses
        if filter_clauses:
            bool_query["filter"] = filter_clauses
        es_query = {"bool": bool_query}

    body = {
        "query": es_query,
        "highlight": {
            "fields": {
                "title": {"number_of_fragments": 0},
                "content": {
                    "fragment_size": 200,
                    "number_of_fragments": 3,
                },
            },
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"],
        },
        "aggs": {
            "tag_facets": {"terms": {"field": "tags", "size": 20}},
            "type_facets": {"terms": {"field": "document_type_id", "size": 20}},
            "correspondent_facets": {
                "terms": {"field": "correspondent_id", "size": 20},
            },
            "date_histogram": {
                "date_histogram": {
                    "field": "created",
                    "calendar_interval": "month",
                },
            },
        },
        "from": (page - 1) * page_size,
        "size": page_size,
    }

    return body


def execute_search(query_text, user_id=None, filters=None, page=1, page_size=25):
    """Execute a search query and return formatted results.

    Before building the ES query:
    1. Synonym expansion — loads active SearchSynonym groups and appends
       equivalent terms to the query text so all synonyms are searched.
    2. Curation — if an admin has configured a SearchCuration for this exact
       query, pinned document IDs are prepended to the result list and hidden
       document IDs are excluded.
    """
    client = get_client()
    if not client:
        return _empty_results()

    # --- Synonym expansion ---
    synonym_groups = _load_synonyms()
    expanded_query = _expand_query_with_synonyms(query_text, synonym_groups)
    if expanded_query != query_text:
        logger.debug(
            "Synonym expansion: %r -> %r", query_text, expanded_query,
        )

    # --- Curation lookup ---
    curation = _load_curation(query_text)
    hidden_ids = set()
    pinned_ids = []
    if curation:
        pinned_ids = list(curation.pinned_documents.values_list("id", flat=True))
        hidden_ids = set(curation.hidden_documents.values_list("id", flat=True))
        logger.debug(
            "Curation applied for %r: pinned=%s hidden=%s",
            query_text, pinned_ids, list(hidden_ids),
        )

    # Build and execute main ES query using the expanded text
    body = build_search_query(expanded_query, user_id, filters, page, page_size)

    # Exclude hidden documents at the ES level for efficiency
    if hidden_ids:
        es_query = body["query"]
        body["query"] = {
            "bool": {
                "must": [es_query],
                "must_not": [{"ids": {"values": [str(i) for i in hidden_ids]}}],
            },
        }

    try:
        response = client.search(index=get_index_name(), body=body)
    except Exception as e:
        logger.error("Search failed: %s", e)
        return _empty_results()

    results = _format_results(response, page, page_size)

    # Prepend pinned documents on the first page only
    if pinned_ids and page == 1:
        results = _prepend_pinned(results, pinned_ids, hidden_ids)

    return results


def execute_autocomplete(query_text, user_id=None, limit=10):
    """Execute an autocomplete search for typeahead suggestions."""
    client = get_client()
    if not client:
        return []

    filter_clauses = []
    if user_id:
        filter_clauses.append({"term": {"owner_id": user_id}})

    body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query_text,
                            "fields": ["title^3", "content", "original_filename"],
                            "type": "phrase_prefix",
                        },
                    },
                ],
                "filter": filter_clauses,
            },
        },
        "_source": ["id", "title", "correspondent", "document_type"],
        "size": limit,
    }

    try:
        response = client.search(index=get_index_name(), body=body)
    except Exception as e:
        logger.error("Autocomplete search failed: %s", e)
        return []

    return [
        {
            "id": hit["_source"]["id"],
            "title": hit["_source"]["title"],
            "correspondent": hit["_source"].get("correspondent"),
            "document_type": hit["_source"].get("document_type"),
            "score": hit["_score"],
        }
        for hit in response["hits"]["hits"]
    ]


def execute_more_like_this(document_id, user_id=None, limit=10):
    """Find documents similar to the given document."""
    client = get_client()
    if not client:
        return []

    filter_clauses = [{"bool": {"must_not": {"term": {"id": document_id}}}}]
    if user_id:
        filter_clauses.append({"term": {"owner_id": user_id}})

    body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "more_like_this": {
                            "fields": ["title", "content"],
                            "like": [
                                {
                                    "_index": get_index_name(),
                                    "_id": str(document_id),
                                },
                            ],
                            "min_term_freq": 1,
                            "min_doc_freq": 1,
                            "max_query_terms": 25,
                        },
                    },
                ],
                "filter": filter_clauses,
            },
        },
        "_source": [
            "id", "title", "correspondent", "document_type",
            "created", "tags",
        ],
        "size": limit,
    }

    try:
        response = client.search(index=get_index_name(), body=body)
    except Exception as e:
        logger.error("MLT search failed: %s", e)
        return []

    return [
        {
            "id": hit["_source"]["id"],
            "title": hit["_source"]["title"],
            "correspondent": hit["_source"].get("correspondent"),
            "document_type": hit["_source"].get("document_type"),
            "created": hit["_source"].get("created"),
            "tags": hit["_source"].get("tags", []),
            "score": hit["_score"],
        }
        for hit in response["hits"]["hits"]
    ]


def _parse_field_queries(query_text):
    """Parse field:value patterns from query text."""
    field_queries = []
    # Match patterns like tag:invoice, correspondent:"Acme Corp", created:[2025-01-01 TO 2025-12-31]
    pattern = r'(\w+):(?:"([^"]+)"|\[([^\]]+)\]|(\S+))'
    remaining = query_text

    for match in re.finditer(pattern, query_text):
        field = match.group(1).lower()
        value = match.group(2) or match.group(3) or match.group(4)
        field_queries.append((field, value))
        remaining = remaining.replace(match.group(0), "", 1)

    return remaining, field_queries


def _parse_date_range(value):
    """Parse a date range string like '2025-01-01 TO 2025-12-31'."""
    parts = value.split(" TO ")
    if len(parts) == 2:
        result = {}
        start, end = parts[0].strip(), parts[1].strip()
        if start != "*":
            result["gte"] = start
        if end != "*":
            result["lte"] = end
        return result
    return None


def _format_results(response, page, page_size):
    """Format ES response into a standardized results dict."""
    hits = response["hits"]
    total = hits["total"]["value"] if isinstance(hits["total"], dict) else hits["total"]

    results = []
    for hit in hits["hits"]:
        result = hit["_source"].copy()
        result["score"] = hit["_score"]
        if "highlight" in hit:
            result["highlights"] = hit["highlight"]
        results.append(result)

    # Facets
    aggs = response.get("aggregations", {})
    facets = {}
    if "tag_facets" in aggs:
        facets["tags"] = [
            {"key": b["key"], "count": b["doc_count"]}
            for b in aggs["tag_facets"]["buckets"]
        ]
    if "type_facets" in aggs:
        facets["document_types"] = [
            {"key": b["key"], "count": b["doc_count"]}
            for b in aggs["type_facets"]["buckets"]
        ]
    if "correspondent_facets" in aggs:
        facets["correspondents"] = [
            {"key": b["key"], "count": b["doc_count"]}
            for b in aggs["correspondent_facets"]["buckets"]
        ]
    if "date_histogram" in aggs:
        facets["date_histogram"] = [
            {"key": b["key_as_string"], "count": b["doc_count"]}
            for b in aggs["date_histogram"]["buckets"]
        ]

    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "results": results,
        "facets": facets,
    }


def _prepend_pinned(results, pinned_ids, hidden_ids):
    """Prepend pinned documents to search results.

    Fetches pinned Document records and inserts them at the top of the first
    page, preserving their order as configured in the curation.  Any pinned ID
    that already appears in the organic results is removed from there to avoid
    duplication.  Hidden IDs are skipped.
    """
    from documents.models import Document

    # Build a lookup of existing result doc IDs to avoid duplicates
    existing_ids = {r.get("id") for r in results["results"]}

    # Fetch pinned documents in declared order (skip hidden ones)
    pinned_docs = {
        d.id: d
        for d in Document.objects.filter(
            id__in=pinned_ids,
        ).select_related("document_type", "correspondent")
    }

    pinned_entries = []
    for doc_id in pinned_ids:
        if doc_id in hidden_ids:
            continue
        doc = pinned_docs.get(doc_id)
        if doc is None:
            continue
        pinned_entries.append({
            "id": doc.id,
            "title": doc.title,
            "correspondent": doc.correspondent.name if doc.correspondent else None,
            "document_type": doc.document_type.name if doc.document_type else None,
            "created": str(doc.created),
            "score": None,
            "_pinned": True,
        })

    # Remove pinned docs from organic results to prevent duplication
    organic = [r for r in results["results"] if r.get("id") not in {e["id"] for e in pinned_entries}]

    results["results"] = pinned_entries + organic
    results["count"] = results["count"] + len(pinned_entries)
    return results


def _empty_results():
    """Return an empty results structure."""
    return {
        "count": 0,
        "page": 1,
        "page_size": 25,
        "results": [],
        "facets": {},
    }
