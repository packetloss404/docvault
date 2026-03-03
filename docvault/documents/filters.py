"""FilterSets for the documents module."""

import json

from django.db.models import Q
from django_filters import rest_framework as filters

from .models import Document


# Operator map for custom field filtering
CUSTOM_FIELD_OPS = {
    "exact": "exact",
    "contains": "icontains",
    "startswith": "istartswith",
    "gt": "gt",
    "gte": "gte",
    "lt": "lt",
    "lte": "lte",
    "isnull": "isnull",
}

# Map custom field data types to the value column
FIELD_TYPE_COLUMN = {
    "string": "value_text",
    "longtext": "value_text",
    "url": "value_url",
    "date": "value_date",
    "datetime": "value_datetime",
    "boolean": "value_bool",
    "integer": "value_int",
    "float": "value_float",
    "monetary": "value_monetary",
    "documentlink": "value_document_ids",
    "select": "value_select",
    "multiselect": "value_select",
}


class DocumentFilterSet(filters.FilterSet):
    """Comprehensive filter for Document list endpoints."""

    # Date range filters
    created_after = filters.DateFilter(field_name="created", lookup_expr="gte")
    created_before = filters.DateFilter(field_name="created", lookup_expr="lte")
    added_after = filters.DateTimeFilter(field_name="added", lookup_expr="gte")
    added_before = filters.DateTimeFilter(field_name="added", lookup_expr="lte")

    # Boolean convenience filters
    has_asn = filters.BooleanFilter(method="filter_has_asn")

    # Title search (case-insensitive contains)
    title__contains = filters.CharFilter(field_name="title", lookup_expr="icontains")

    # Organization filters
    tags__id__in = filters.BaseInFilter(field_name="tags__id", distinct=True)
    tags__id__none = filters.BooleanFilter(method="filter_no_tags")
    correspondent = filters.NumberFilter(field_name="correspondent")
    cabinet = filters.NumberFilter(field_name="cabinet")

    # Custom field filter
    custom_fields = filters.CharFilter(method="filter_custom_fields")

    # Has custom field filter
    has_custom_field = filters.NumberFilter(method="filter_has_custom_field")

    class Meta:
        model = Document
        fields = [
            "document_type",
            "mime_type",
            "language",
            "archive_serial_number",
            "owner",
            "correspondent",
            "cabinet",
        ]

    def filter_no_tags(self, queryset, name, value):
        if value:
            return queryset.filter(tags__isnull=True)
        return queryset.filter(tags__isnull=False).distinct()

    def filter_has_asn(self, queryset, name, value):
        if value:
            return queryset.filter(archive_serial_number__isnull=False)
        return queryset.filter(archive_serial_number__isnull=True)

    def filter_has_custom_field(self, queryset, name, value):
        """Filter documents that have a specific custom field set."""
        return queryset.filter(
            custom_field_instances__field_id=value,
        ).distinct()

    def filter_custom_fields(self, queryset, name, value):
        """
        Custom field query parser for complex filtering.

        Accepts JSON: {"field_name": "invoice_number", "op": "contains", "value": "2026"}
        Or field_id variant: {"field_id": 5, "op": "exact", "value": "INV-001"}
        """
        try:
            query = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return queryset

        field_name = query.get("field_name")
        field_id = query.get("field_id")
        op = query.get("op", "exact")
        filter_value = query.get("value")

        if not (field_name or field_id):
            return queryset

        # Build the base Q filter for the custom field
        base_q = Q()
        if field_id:
            base_q = Q(custom_field_instances__field_id=field_id)
        elif field_name:
            base_q = Q(custom_field_instances__field__name=field_name)

        # Determine the value column from the field
        from organization.models import CustomField
        try:
            if field_id:
                cf = CustomField.objects.get(pk=field_id)
            else:
                cf = CustomField.objects.get(name=field_name)
        except CustomField.DoesNotExist:
            return queryset.none()

        column = FIELD_TYPE_COLUMN.get(cf.data_type, "value_text")
        lookup = CUSTOM_FIELD_OPS.get(op, "exact")
        field_lookup = f"custom_field_instances__{column}__{lookup}"

        return queryset.filter(
            base_q, **{field_lookup: filter_value},
        ).distinct()
