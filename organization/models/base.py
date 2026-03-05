"""Base models for the organization module."""

from django.db import models

from core.models import AuditableModel, OwnedModel
from documents.constants import MATCH_NONE, MATCHING_ALGORITHMS


class MatchingModel(AuditableModel, OwnedModel):
    """Abstract base class for models with automatic matching capabilities."""

    name = models.CharField(max_length=128, db_index=True)
    slug = models.SlugField(max_length=128, db_index=True)
    match = models.CharField(
        max_length=512,
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
        abstract = True

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
