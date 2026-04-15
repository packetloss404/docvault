"""Document, DocumentFile, and DocumentVersion models."""

import uuid
from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import AuditableModel, OwnedModel, SoftDeleteModel

from .document_type import DocumentType


class Document(SoftDeleteModel, AuditableModel, OwnedModel):
    """
    Core document entity.

    Represents a logical document with metadata, classification,
    and references to physical file artifacts.
    """

    # Identity
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=128, db_index=True)
    content = models.TextField(blank=True, default="", help_text="OCR/extracted text content.")

    # Classification
    document_type = models.ForeignKey(
        DocumentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    correspondent = models.ForeignKey(
        "organization.Correspondent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    storage_path = models.ForeignKey(
        "organization.StoragePath",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    tags = models.ManyToManyField(
        "organization.Tag",
        blank=True,
        related_name="documents",
    )
    cabinet = models.ForeignKey(
        "organization.Cabinet",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )

    # File info
    original_filename = models.CharField(max_length=1024, blank=True, default="")
    mime_type = models.CharField(max_length=256, blank=True, default="")
    checksum = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="SHA-256 checksum of the original file.",
    )
    archive_checksum = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="SHA-256 checksum of the archive (PDF/A) file.",
    )
    page_count = models.PositiveIntegerField(default=0)

    # Storage
    filename = models.CharField(max_length=1024, unique=True, null=True, blank=True)
    archive_filename = models.CharField(max_length=1024, unique=True, null=True, blank=True)
    thumbnail_path = models.CharField(
        max_length=1024,
        blank=True,
        default="",
        help_text="Storage path to the WebP thumbnail.",
    )

    # Dates
    created = models.DateField(
        default=date.today,
        db_index=True,
        help_text="Document date (extracted or user-set).",
    )
    added = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Date/time this document was ingested into the system.",
    )

    # Archive Serial Number (from Paperless-ngx)
    archive_serial_number = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="Unique physical archive reference number.",
    )

    # Language
    language = models.CharField(max_length=16, default="en")

    # Legal hold
    is_held = models.BooleanField(default=False, db_index=True)

    # Supersession
    is_obsolete = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Set automatically when another document supersedes this one.",
    )

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["checksum"]),
            models.Index(fields=["archive_serial_number"]),
            models.Index(fields=["mime_type"]),
        ]
        verbose_name = "document"
        verbose_name_plural = "documents"

    def __str__(self):
        return self.title


class DocumentFile(AuditableModel):
    """
    Physical file artifact (from Mayan EDMS multi-file support).

    A single document can have multiple files (original, archive, etc.).
    """

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="files",
    )
    file = models.FileField(upload_to="documents/files/")
    filename = models.CharField(max_length=1024)
    mime_type = models.CharField(max_length=256)
    encoding = models.CharField(max_length=64, blank=True, default="")
    checksum = models.CharField(max_length=64, help_text="SHA-256 checksum.")
    size = models.PositiveBigIntegerField(default=0, help_text="File size in bytes.")
    comment = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "document file"
        verbose_name_plural = "document files"

    def __str__(self):
        return f"{self.document.title} - {self.filename}"


class DocumentVersion(AuditableModel):
    """
    Version tracking (from Mayan EDMS).

    Each document can have multiple versions, with one marked as active.
    """

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="version_history",
    )
    version_number = models.PositiveIntegerField()
    comment = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=False)
    file = models.ForeignKey(
        DocumentFile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="versions",
    )

    class Meta:
        ordering = ["-version_number"]
        unique_together = [["document", "version_number"]]
        verbose_name = "document version"
        verbose_name_plural = "document versions"

    def __str__(self):
        return f"{self.document.title} v{self.version_number}"
