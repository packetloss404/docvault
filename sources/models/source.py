"""Base Source model for document ingestion."""

from django.db import models

from core.models import AuditableModel
from sources.constants import SOURCE_TYPE_CHOICES


class Source(AuditableModel):
    """Base model for all document sources."""

    label = models.CharField(max_length=192)
    enabled = models.BooleanField(default=True)
    source_type = models.CharField(max_length=32, choices=SOURCE_TYPE_CHOICES)

    # Default classification for ingested documents
    document_type = models.ForeignKey(
        "documents.DocumentType",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    tags = models.ManyToManyField(
        "organization.Tag",
        blank=True,
        related_name="+",
    )
    owner = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_sources",
        help_text="Default owner for documents ingested from this source.",
    )

    class Meta:
        ordering = ["label"]
        verbose_name = "source"
        verbose_name_plural = "sources"

    def __str__(self):
        return f"{self.label} ({self.get_source_type_display()})"
