"""DocumentType model - schema definition with retention policies."""

from django.db import models
from django.utils.text import slugify

from core.models import AuditableModel, OwnedModel
from documents.constants import MATCH_NONE, MATCHING_ALGORITHMS, TIME_UNITS


class DocumentType(AuditableModel, OwnedModel):
    """
    Document type defines a classification schema with optional
    retention policies and matching rules for auto-assignment.
    """

    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=128, unique=True)

    # Retention policies (from Mayan EDMS)
    trash_time_period = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Auto-trash documents of this type after this period.",
    )
    trash_time_unit = models.CharField(
        max_length=16,
        choices=TIME_UNITS,
        null=True,
        blank=True,
    )
    delete_time_period = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Auto-delete trashed documents after this period.",
    )
    delete_time_unit = models.CharField(
        max_length=16,
        choices=TIME_UNITS,
        null=True,
        blank=True,
    )

    # Matching (from Paperless-ngx)
    match = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="Pattern to match against document content.",
    )
    matching_algorithm = models.PositiveSmallIntegerField(
        choices=MATCHING_ALGORITHMS,
        default=MATCH_NONE,
    )
    is_insensitive = models.BooleanField(
        default=True,
        help_text="Case-insensitive matching.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "document type"
        verbose_name_plural = "document types"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
