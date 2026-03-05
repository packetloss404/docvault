"""Cabinet model - hierarchical folder structure with MPTT."""

from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

from core.models import AuditableModel, OwnedModel


class Cabinet(MPTTModel, AuditableModel, OwnedModel):
    """
    Hierarchical folder/cabinet for organizing documents.

    Unlike tags (which are many-to-many), a document belongs to at most
    one cabinet, providing a traditional folder-like organization.
    """

    name = models.CharField(max_length=128, db_index=True)
    slug = models.SlugField(max_length=128, db_index=True)
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        ordering = ["tree_id", "lft"]
        verbose_name = "cabinet"
        verbose_name_plural = "cabinets"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "parent"],
                name="unique_cabinet_name_per_parent",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
