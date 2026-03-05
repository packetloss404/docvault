"""Execute saved views by applying filter rules to Django querysets."""

from django.db.models import Q

from documents.models import Document

from .models import (
    RULE_ADDED_AFTER,
    RULE_ADDED_BEFORE,
    RULE_ASN_GREATER_THAN,
    RULE_ASN_IS,
    RULE_ASN_LESS_THAN,
    RULE_CABINET_IS,
    RULE_CONTENT_CONTAINS,
    RULE_CORRESPONDENT_IS,
    RULE_CREATED_AFTER,
    RULE_CREATED_BEFORE,
    RULE_CUSTOM_FIELD_VALUE,
    RULE_DOCUMENT_TYPE_IS,
    RULE_FILENAME_CONTAINS,
    RULE_HAS_ASN,
    RULE_HAS_CORRESPONDENT,
    RULE_HAS_CUSTOM_FIELD,
    RULE_HAS_DOCUMENT_TYPE,
    RULE_HAS_NO_ASN,
    RULE_HAS_NO_CORRESPONDENT,
    RULE_HAS_NO_DOCUMENT_TYPE,
    RULE_HAS_NO_TAGS,
    RULE_HAS_TAGS,
    RULE_LANGUAGE_IS,
    RULE_MIME_TYPE_IS,
    RULE_OWNER_IS,
    RULE_TAG_ALL,
    RULE_TAG_IS,
    RULE_TAG_NONE,
    RULE_TITLE_CONTAINS,
)


def execute_saved_view(saved_view, user=None):
    """
    Execute a saved view and return a queryset of matching documents.

    Applies all filter rules with AND logic.
    """
    qs = Document.objects.all()

    # Permission: non-superusers only see their own documents
    if user and not user.is_superuser:
        qs = qs.filter(owner=user)

    rules = saved_view.get_filter_rules_dict()

    for rule_type, values in rules.items():
        for value in values:
            qs = _apply_rule(qs, rule_type, value)

    # Apply sorting
    sort_field = saved_view.sort_field or "created"
    if saved_view.sort_reverse:
        sort_field = f"-{sort_field}"
    qs = qs.order_by(sort_field)

    return qs.distinct()


def _apply_rule(qs, rule_type, value):
    """Apply a single filter rule to a queryset."""
    if rule_type == RULE_TITLE_CONTAINS:
        return qs.filter(title__icontains=value)

    elif rule_type == RULE_CONTENT_CONTAINS:
        return qs.filter(content__icontains=value)

    elif rule_type == RULE_ASN_IS:
        return qs.filter(archive_serial_number=int(value))

    elif rule_type == RULE_CORRESPONDENT_IS:
        return qs.filter(correspondent_id=int(value))

    elif rule_type == RULE_DOCUMENT_TYPE_IS:
        return qs.filter(document_type_id=int(value))

    elif rule_type == RULE_TAG_IS:
        return qs.filter(tags__id=int(value))

    elif rule_type == RULE_TAG_ALL:
        # value is comma-separated tag IDs
        tag_ids = [int(x) for x in value.split(",")]
        for tag_id in tag_ids:
            qs = qs.filter(tags__id=tag_id)
        return qs

    elif rule_type == RULE_TAG_NONE:
        tag_ids = [int(x) for x in value.split(",")]
        return qs.exclude(tags__id__in=tag_ids)

    elif rule_type == RULE_HAS_TAGS:
        return qs.filter(tags__isnull=False)

    elif rule_type == RULE_HAS_NO_TAGS:
        return qs.filter(tags__isnull=True)

    elif rule_type == RULE_CABINET_IS:
        return qs.filter(cabinet_id=int(value))

    elif rule_type == RULE_HAS_CORRESPONDENT:
        return qs.filter(correspondent__isnull=False)

    elif rule_type == RULE_HAS_NO_CORRESPONDENT:
        return qs.filter(correspondent__isnull=True)

    elif rule_type == RULE_HAS_DOCUMENT_TYPE:
        return qs.filter(document_type__isnull=False)

    elif rule_type == RULE_HAS_NO_DOCUMENT_TYPE:
        return qs.filter(document_type__isnull=True)

    elif rule_type == RULE_CREATED_AFTER:
        return qs.filter(created__gte=value)

    elif rule_type == RULE_CREATED_BEFORE:
        return qs.filter(created__lte=value)

    elif rule_type == RULE_ADDED_AFTER:
        return qs.filter(added__gte=value)

    elif rule_type == RULE_ADDED_BEFORE:
        return qs.filter(added__lte=value)

    elif rule_type == RULE_LANGUAGE_IS:
        return qs.filter(language=value)

    elif rule_type == RULE_MIME_TYPE_IS:
        return qs.filter(mime_type=value)

    elif rule_type == RULE_OWNER_IS:
        return qs.filter(owner_id=int(value))

    elif rule_type == RULE_HAS_CUSTOM_FIELD:
        return qs.filter(custom_field_instances__field_id=int(value))

    elif rule_type == RULE_CUSTOM_FIELD_VALUE:
        # value format: "field_id:value"
        parts = value.split(":", 1)
        if len(parts) == 2:
            field_id, field_val = parts
            return qs.filter(
                custom_field_instances__field_id=int(field_id),
                custom_field_instances__value_text__icontains=field_val,
            )
        return qs

    elif rule_type == RULE_FILENAME_CONTAINS:
        return qs.filter(original_filename__icontains=value)

    elif rule_type == RULE_ASN_GREATER_THAN:
        return qs.filter(archive_serial_number__gt=int(value))

    elif rule_type == RULE_ASN_LESS_THAN:
        return qs.filter(archive_serial_number__lt=int(value))

    elif rule_type == RULE_HAS_ASN:
        return qs.filter(archive_serial_number__isnull=False)

    elif rule_type == RULE_HAS_NO_ASN:
        return qs.filter(archive_serial_number__isnull=True)

    return qs
