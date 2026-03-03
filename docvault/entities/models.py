"""Models for named entity recognition."""

from django.db import models

from .constants import DEFAULT_ENTITY_TYPES


class EntityType(models.Model):
    """
    A category of named entity (e.g. PERSON, ORGANIZATION, LOCATION).

    Seed rows are created via a data migration; administrators can add
    additional custom types through the API.
    """

    name = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=128)
    color = models.CharField(max_length=7, default="#6c757d")
    icon = models.CharField(max_length=64, default="bi-tag")
    extraction_pattern = models.TextField(
        blank=True,
        default="",
        help_text="Optional regex pattern for custom extraction.",
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "entity type"
        verbose_name_plural = "entity types"

    def __str__(self):
        return self.label

    @classmethod
    def seed_defaults(cls):
        """Create the default entity types if they do not already exist."""
        for name, label, color, icon in DEFAULT_ENTITY_TYPES:
            cls.objects.get_or_create(
                name=name,
                defaults={
                    "label": label,
                    "color": color,
                    "icon": icon,
                },
            )


class Entity(models.Model):
    """
    A single named-entity mention extracted from a document.

    Entities are created by the NERPlugin during the processing pipeline
    and are indexed into Elasticsearch as nested objects for faceted search.
    """

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="entities",
    )
    entity_type = models.ForeignKey(
        EntityType,
        on_delete=models.CASCADE,
        related_name="entities",
    )
    value = models.CharField(
        max_length=512,
        help_text="Normalized entity value.",
    )
    raw_value = models.CharField(
        max_length=512,
        help_text="Original text as it appeared in the document.",
    )
    confidence = models.FloatField(default=1.0)
    start_offset = models.IntegerField(default=0)
    end_offset = models.IntegerField(default=0)
    page_number = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["entity_type", "value"]
        indexes = [
            models.Index(fields=["document", "entity_type"]),
        ]
        verbose_name = "entity"
        verbose_name_plural = "entities"

    def __str__(self):
        return f"{self.entity_type.name}: {self.value}"
