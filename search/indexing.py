"""Document indexing for Elasticsearch."""

import logging

from .client import get_client, get_index_name

logger = logging.getLogger(__name__)


def document_to_index_body(document):
    """Convert a Document model instance to an ES index body dict."""
    body = {
        "id": document.pk,
        "title": document.title,
        "content": document.content or "",
        "original_filename": document.original_filename,
        "mime_type": document.mime_type,
        "checksum": document.checksum,
        "page_count": document.page_count,
        "language": document.language,
        "created": (
            document.created.isoformat() if document.created else None
        ),
        "added": (
            document.added.isoformat() if document.added else None
        ),
        "modified": (
            document.updated_at.isoformat() if document.updated_at else None
        ),
        "asn": document.archive_serial_number,
        "owner_id": document.owner_id,
    }

    # Relations
    if document.correspondent:
        body["correspondent"] = document.correspondent.name
        body["correspondent_id"] = document.correspondent_id
    else:
        body["correspondent"] = None
        body["correspondent_id"] = None

    if document.document_type:
        body["document_type"] = document.document_type.name
        body["document_type_id"] = document.document_type_id
    else:
        body["document_type"] = None
        body["document_type_id"] = None

    if document.cabinet:
        body["cabinet"] = document.cabinet.name
        body["cabinet_id"] = document.cabinet_id
    else:
        body["cabinet"] = None
        body["cabinet_id"] = None

    if document.storage_path:
        body["storage_path"] = document.storage_path.name
    else:
        body["storage_path"] = None

    # Tags
    tags = document.tags.all()
    body["tags"] = [t.name for t in tags]
    body["tag_ids"] = [t.id for t in tags]

    # Custom fields
    custom_fields = {}
    for inst in document.custom_field_instances.select_related("field").all():
        custom_fields[inst.field.slug] = inst.value
    body["custom_fields"] = custom_fields

    # Comments (for full-text search)
    if hasattr(document, "comments"):
        comments = document.comments.all()
        body["comments"] = " ".join(c.text for c in comments)
    else:
        body["comments"] = ""

    # Named entities (nested objects for faceted search)
    try:
        from entities.models import Entity
        entity_qs = Entity.objects.filter(document=document).select_related("entity_type")
        body["entities"] = [
            {
                "type": ent.entity_type.name,
                "value": ent.value,
                "value_text": ent.value,
            }
            for ent in entity_qs
        ]
    except Exception:
        body["entities"] = []

    return body


def index_document(document):
    """Index a single document in Elasticsearch."""
    client = get_client()
    if not client:
        return False

    body = document_to_index_body(document)
    client.index(
        index=get_index_name(),
        id=document.pk,
        body=body,
    )
    logger.debug("Indexed document %s.", document.pk)
    return True


def remove_document(document_id):
    """Remove a document from the Elasticsearch index."""
    client = get_client()
    if not client:
        return False

    try:
        client.delete(
            index=get_index_name(),
            id=document_id,
        )
        logger.debug("Removed document %s from index.", document_id)
        return True
    except Exception:
        logger.warning("Failed to remove document %s from index.", document_id)
        return False


def bulk_index_documents(documents):
    """Bulk index multiple documents."""
    client = get_client()
    if not client:
        return 0

    from elasticsearch.helpers import bulk

    actions = []
    for doc in documents:
        body = document_to_index_body(doc)
        actions.append({
            "_index": get_index_name(),
            "_id": doc.pk,
            "_source": body,
        })

    if not actions:
        return 0

    success, errors = bulk(client, actions, raise_on_error=False)
    if errors:
        logger.warning("Bulk indexing had %d errors.", len(errors))
    logger.info("Bulk indexed %d documents.", success)
    return success


def rebuild_index():
    """Rebuild the entire search index from the database."""
    from .client import create_index, delete_index

    delete_index()
    create_index()

    from documents.models import Document

    documents = (
        Document.objects
        .select_related(
            "correspondent", "document_type", "cabinet", "storage_path",
        )
        .prefetch_related("tags", "custom_field_instances__field")
        .all()
    )
    return bulk_index_documents(documents)
