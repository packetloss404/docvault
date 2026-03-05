"""Models for the relationships module."""

from django.db import models

from core.models import AuditableModel

from .constants import BUILTIN_TYPES


class RelationshipType(AuditableModel):
    """Defines a kind of relationship between two documents.

    Built-in types (e.g. "supersedes", "references") are seeded via
    ``seed_defaults()`` and cannot be deleted through the API.
    Custom types may be created by administrators.
    """

    slug = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=128)
    icon = models.CharField(max_length=64, default="bi-link-45deg")
    is_directional = models.BooleanField(
        default=True,
        help_text="If True, the relationship has a direction (source -> target).",
    )
    is_builtin = models.BooleanField(
        default=False,
        help_text="Built-in types cannot be deleted.",
    )
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["label"]
        verbose_name = "relationship type"
        verbose_name_plural = "relationship types"

    def __str__(self):
        return self.label

    @classmethod
    def seed_defaults(cls):
        """Create all built-in relationship types if they do not already exist."""
        for slug, label, icon, is_directional in BUILTIN_TYPES:
            cls.objects.get_or_create(
                slug=slug,
                defaults={
                    "label": label,
                    "icon": icon,
                    "is_directional": is_directional,
                    "is_builtin": True,
                },
            )


class DocumentRelationship(AuditableModel):
    """A typed relationship between two documents.

    For directional types the relationship reads as:
        source_document  --[relationship_type]-->  target_document

    For non-directional types the order is irrelevant but we still store
    source/target to keep the schema simple.

    NOTE: Supersession handling (e.g. marking the target document as
    obsolete) should be handled at the view/serializer layer rather than
    in ``save()``, because the Document model may not yet carry an
    ``is_obsolete`` field.
    """

    source_document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="outgoing_relationships",
    )
    target_document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="incoming_relationships",
    )
    relationship_type = models.ForeignKey(
        RelationshipType,
        on_delete=models.CASCADE,
        related_name="relationships",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "document relationship"
        verbose_name_plural = "document relationships"
        constraints = [
            models.UniqueConstraint(
                fields=["source_document", "target_document", "relationship_type"],
                name="unique_document_relationship",
            ),
        ]

    def __str__(self):
        return (
            f"{self.source_document} --[{self.relationship_type}]--> "
            f"{self.target_document}"
        )
