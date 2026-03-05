"""Models for search saved views, filter rules, and search analytics."""

from django.conf import settings
from django.db import models

from core.models import AuditableModel, OwnedModel


# Display modes
DISPLAY_TABLE = "table"
DISPLAY_SMALL_CARDS = "small_cards"
DISPLAY_LARGE_CARDS = "large_cards"

DISPLAY_MODE_CHOICES = [
    (DISPLAY_TABLE, "Table"),
    (DISPLAY_SMALL_CARDS, "Small Cards"),
    (DISPLAY_LARGE_CARDS, "Large Cards"),
]

# Filter rule types
RULE_TITLE_CONTAINS = "title_contains"
RULE_CONTENT_CONTAINS = "content_contains"
RULE_ASN_IS = "asn_is"
RULE_CORRESPONDENT_IS = "correspondent_is"
RULE_DOCUMENT_TYPE_IS = "document_type_is"
RULE_TAG_IS = "tag_is"
RULE_TAG_ALL = "tag_all"
RULE_TAG_NONE = "tag_none"
RULE_HAS_TAGS = "has_tags"
RULE_HAS_NO_TAGS = "has_no_tags"
RULE_CABINET_IS = "cabinet_is"
RULE_HAS_CORRESPONDENT = "has_correspondent"
RULE_HAS_NO_CORRESPONDENT = "has_no_correspondent"
RULE_HAS_DOCUMENT_TYPE = "has_document_type"
RULE_HAS_NO_DOCUMENT_TYPE = "has_no_document_type"
RULE_CREATED_AFTER = "created_after"
RULE_CREATED_BEFORE = "created_before"
RULE_ADDED_AFTER = "added_after"
RULE_ADDED_BEFORE = "added_before"
RULE_LANGUAGE_IS = "language_is"
RULE_MIME_TYPE_IS = "mime_type_is"
RULE_OWNER_IS = "owner_is"
RULE_HAS_CUSTOM_FIELD = "has_custom_field"
RULE_CUSTOM_FIELD_VALUE = "custom_field_value"
RULE_FILENAME_CONTAINS = "filename_contains"
RULE_ASN_GREATER_THAN = "asn_greater_than"
RULE_ASN_LESS_THAN = "asn_less_than"
RULE_HAS_ASN = "has_asn"
RULE_HAS_NO_ASN = "has_no_asn"

FILTER_RULE_TYPES = [
    (RULE_TITLE_CONTAINS, "Title contains"),
    (RULE_CONTENT_CONTAINS, "Content contains"),
    (RULE_ASN_IS, "ASN is"),
    (RULE_CORRESPONDENT_IS, "Correspondent is"),
    (RULE_DOCUMENT_TYPE_IS, "Document type is"),
    (RULE_TAG_IS, "Has tag"),
    (RULE_TAG_ALL, "Has all tags"),
    (RULE_TAG_NONE, "Has none of tags"),
    (RULE_HAS_TAGS, "Has any tags"),
    (RULE_HAS_NO_TAGS, "Has no tags"),
    (RULE_CABINET_IS, "Cabinet is"),
    (RULE_HAS_CORRESPONDENT, "Has a correspondent"),
    (RULE_HAS_NO_CORRESPONDENT, "Has no correspondent"),
    (RULE_HAS_DOCUMENT_TYPE, "Has a document type"),
    (RULE_HAS_NO_DOCUMENT_TYPE, "Has no document type"),
    (RULE_CREATED_AFTER, "Created after"),
    (RULE_CREATED_BEFORE, "Created before"),
    (RULE_ADDED_AFTER, "Added after"),
    (RULE_ADDED_BEFORE, "Added before"),
    (RULE_LANGUAGE_IS, "Language is"),
    (RULE_MIME_TYPE_IS, "MIME type is"),
    (RULE_OWNER_IS, "Owner is"),
    (RULE_HAS_CUSTOM_FIELD, "Has custom field"),
    (RULE_CUSTOM_FIELD_VALUE, "Custom field value"),
    (RULE_FILENAME_CONTAINS, "Filename contains"),
    (RULE_ASN_GREATER_THAN, "ASN greater than"),
    (RULE_ASN_LESS_THAN, "ASN less than"),
    (RULE_HAS_ASN, "Has ASN"),
    (RULE_HAS_NO_ASN, "Has no ASN"),
]


class SavedView(AuditableModel, OwnedModel):
    """
    A saved document view with display configuration and filter rules.
    """

    name = models.CharField(max_length=256)
    display_mode = models.CharField(
        max_length=16,
        choices=DISPLAY_MODE_CHOICES,
        default=DISPLAY_TABLE,
    )
    display_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="List of column names to display.",
    )
    sort_field = models.CharField(
        max_length=64,
        blank=True,
        default="created",
    )
    sort_reverse = models.BooleanField(default=True)
    page_size = models.PositiveIntegerField(default=25)
    show_on_dashboard = models.BooleanField(default=False)
    show_in_sidebar = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "saved view"
        verbose_name_plural = "saved views"

    def __str__(self):
        return self.name

    def get_filter_rules_dict(self):
        """Return filter rules as a dict for query building."""
        rules = {}
        for rule in self.filter_rules.all():
            if rule.rule_type not in rules:
                rules[rule.rule_type] = []
            rules[rule.rule_type].append(rule.value)
        return rules


class SavedViewFilterRule(models.Model):
    """
    A single filter rule within a saved view.

    Multiple rules are combined with AND logic by default.
    """

    saved_view = models.ForeignKey(
        SavedView,
        on_delete=models.CASCADE,
        related_name="filter_rules",
    )
    rule_type = models.CharField(
        max_length=32,
        choices=FILTER_RULE_TYPES,
    )
    value = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="The filter value (e.g., tag ID, date, text).",
    )

    class Meta:
        ordering = ["rule_type"]

    def __str__(self):
        return f"{self.get_rule_type_display()}: {self.value}"


# ---------------------------------------------------------------------------
# Search analytics models (Sprint 19)
# ---------------------------------------------------------------------------


class SearchQuery(models.Model):
    """
    Records every search query for analytics and relevance tuning.
    """

    query_text = models.CharField(max_length=512)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="search_queries",
    )
    results_count = models.IntegerField(default=0)
    clicked_document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    click_position = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    response_time_ms = models.IntegerField(default=0)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "search query"
        verbose_name_plural = "search queries"

    def __str__(self):
        return f"{self.query_text} ({self.timestamp:%Y-%m-%d %H:%M})"


class SearchSynonym(models.Model):
    """
    A group of synonymous terms used for query expansion.
    """

    terms = models.JSONField(
        default=list,
        help_text="List of synonymous terms.",
    )
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "search synonym"
        verbose_name_plural = "search synonyms"

    def __str__(self):
        return ", ".join(self.terms) if self.terms else "(empty)"


class SearchCuration(models.Model):
    """
    Admin-curated search results: pin, hide, or boost documents
    for a specific query string.
    """

    query_text = models.CharField(max_length=512, unique=True)
    pinned_documents = models.ManyToManyField(
        "documents.Document",
        blank=True,
        related_name="pinned_in_curations",
    )
    hidden_documents = models.ManyToManyField(
        "documents.Document",
        blank=True,
        related_name="hidden_in_curations",
    )
    boost_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Field boost overrides, e.g. {\"title\": 3.0}.",
    )
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["query_text"]
        verbose_name = "search curation"
        verbose_name_plural = "search curations"

    def __str__(self):
        return f"Curation: {self.query_text}"
