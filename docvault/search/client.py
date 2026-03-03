"""Elasticsearch client singleton and index management."""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_client = None

# Index mapping schema
INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "integer"},
            "title": {"type": "text", "analyzer": "standard"},
            "content": {"type": "text", "analyzer": "standard"},
            "correspondent": {"type": "text"},
            "correspondent_id": {"type": "integer"},
            "document_type": {"type": "text"},
            "document_type_id": {"type": "integer"},
            "tags": {"type": "keyword"},
            "tag_ids": {"type": "integer"},
            "cabinet": {"type": "text"},
            "cabinet_id": {"type": "integer"},
            "asn": {"type": "integer"},
            "created": {"type": "date"},
            "added": {"type": "date"},
            "modified": {"type": "date"},
            "owner_id": {"type": "integer"},
            "checksum": {"type": "keyword"},
            "original_filename": {"type": "text"},
            "page_count": {"type": "integer"},
            "custom_fields": {"type": "object", "dynamic": True},
            "storage_path": {"type": "text"},
            "language": {"type": "keyword"},
            "mime_type": {"type": "keyword"},
            "comments": {"type": "text", "analyzer": "standard"},
            "entities": {
                "type": "nested",
                "properties": {
                    "type": {"type": "keyword"},
                    "value": {"type": "keyword"},
                    "value_text": {"type": "text"},
                },
            },
        },
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "standard": {
                    "type": "standard",
                },
            },
        },
    },
}


def get_client():
    """Return the Elasticsearch client singleton."""
    global _client
    if _client is not None:
        return _client

    if not getattr(settings, "ELASTICSEARCH_ENABLED", False):
        return None

    from elasticsearch import Elasticsearch

    _client = Elasticsearch(
        settings.ELASTICSEARCH_URL,
        request_timeout=30,
    )
    return _client


def reset_client():
    """Reset the client singleton (for testing)."""
    global _client
    _client = None


def get_index_name():
    """Return the configured index name."""
    return getattr(settings, "ELASTICSEARCH_INDEX", "docvault")


def create_index():
    """Create the Elasticsearch index with the defined mapping."""
    client = get_client()
    if not client:
        logger.warning("Elasticsearch not enabled, skipping index creation.")
        return False

    index_name = get_index_name()
    if client.indices.exists(index=index_name):
        logger.info("Index '%s' already exists.", index_name)
        return True

    client.indices.create(index=index_name, body=INDEX_MAPPING)
    logger.info("Created index '%s'.", index_name)
    return True


def delete_index():
    """Delete the Elasticsearch index."""
    client = get_client()
    if not client:
        return False

    index_name = get_index_name()
    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)
        logger.info("Deleted index '%s'.", index_name)
        return True
    return False


def update_mapping():
    """Update the index mapping (add new fields)."""
    client = get_client()
    if not client:
        return False

    index_name = get_index_name()
    client.indices.put_mapping(
        index=index_name,
        body=INDEX_MAPPING["mappings"],
    )
    logger.info("Updated mapping for index '%s'.", index_name)
    return True
