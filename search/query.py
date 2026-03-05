"""Search query building and execution."""

import logging
import re

from .client import get_client, get_index_name

logger = logging.getLogger(__name__)


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
    """Execute a search query and return formatted results."""
    client = get_client()
    if not client:
        return _empty_results()

    body = build_search_query(query_text, user_id, filters, page, page_size)

    try:
        response = client.search(index=get_index_name(), body=body)
    except Exception as e:
        logger.error("Search failed: %s", e)
        return _empty_results()

    return _format_results(response, page, page_size)


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


def _empty_results():
    """Return an empty results structure."""
    return {
        "count": 0,
        "page": 1,
        "page_size": 25,
        "results": [],
        "facets": {},
    }
