"""Tag model - hierarchical tags with MPTT, colors, and matching."""

from django.core.validators import RegexValidator
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

from .base import MatchingModel


class Tag(MPTTModel, MatchingModel):
    """
    Hierarchical tag for document classification.

    Uses MPTT for efficient tree queries. Supports colors for UI display
    and inbox flag for auto-tagging workflows.
    """

    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    color = models.CharField(
        max_length=7,
        default="#3b82f6",
        validators=[RegexValidator(
            regex=r"^#[0-9a-fA-F]{6}$",
            message="Color must be a valid hex color (e.g. #3b82f6).",
        )],
        help_text="Hex color for tag display.",
    )
    is_inbox_tag = models.BooleanField(
        default=False,
        help_text="Automatically assigned to new documents for triage.",
    )

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        ordering = ["tree_id", "lft"]
        verbose_name = "tag"
        verbose_name_plural = "tags"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "parent"],
                name="unique_tag_name_per_parent",
            ),
        ]
