"""Validated filter-builder rules applied before the Elasticsearch permission scope."""

import json
from datetime import date

from rest_framework.exceptions import ValidationError

TEXT_FIELDS = {
    "title": "title",
    "content": "content",
    "document_type": "document_type__name",
    "correspondent": "correspondent__name",
    "tags": "tags__name",
    "language": "language",
}
TEXT_OPERATORS = {"contains": "icontains", "equals": "iexact", "starts_with": "istartswith"}
DATE_OPERATORS = {"date_before": "lt", "date_after": "gt"}


def apply_filter_rules(queryset, raw_rules):
    try:
        rules = json.loads(raw_rules)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"filter_rules": "Expected a JSON array of filter rules."}) from exc
    if not isinstance(rules, list) or len(rules) > 20:
        raise ValidationError({"filter_rules": "Expected at most 20 filter rules."})

    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {"field", "operator", "value"}:
            raise ValidationError({"filter_rules": "Each rule needs field, operator and value."})
        field, operator, value = rule["field"], rule["operator"], rule["value"]
        if not all(isinstance(item, str) for item in (field, operator, value)):
            raise ValidationError({"filter_rules": "Rule fields, operators and values must be strings."})
        if not value.strip() or len(value) > 1000:
            raise ValidationError({"filter_rules": "Rule values must contain 1 to 1000 characters."})
        if field == "created" and operator in DATE_OPERATORS:
            try:
                value = date.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError({"filter_rules": "Date values must be valid ISO dates."}) from exc
            lookup = f"created__{DATE_OPERATORS[operator]}"
        elif field in TEXT_FIELDS and operator in TEXT_OPERATORS:
            lookup = f"{TEXT_FIELDS[field]}__{TEXT_OPERATORS[operator]}"
        else:
            raise ValidationError({"filter_rules": "Unsupported field or operator."})
        queryset = queryset.filter(**{lookup: value})
    return queryset.distinct()
