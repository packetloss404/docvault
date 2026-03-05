"""Models for the contributor portal."""

import secrets

from django.conf import settings
from django.db import models

from core.models import AuditableModel

from .constants import (
    REQUEST_PENDING,
    REQUEST_STATUS_CHOICES,
    SUBMISSION_PENDING,
    SUBMISSION_STATUS_CHOICES,
)


class PortalConfig(AuditableModel):
    """
    Configuration for a public-facing contributor portal.

    Each portal has its own slug-based URL, branding, and file-acceptance
    rules. External users can upload documents without authentication.
    """

    name = models.CharField(max_length=256)
    slug = models.SlugField(max_length=128, unique=True)
    welcome_text = models.TextField(blank=True, default="")
    logo = models.ImageField(upload_to="portal/logos/", blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#0d6efd")
    is_active = models.BooleanField(default=True)
    require_email = models.BooleanField(default=True)
    require_name = models.BooleanField(default=True)
    default_document_type = models.ForeignKey(
        "documents.DocumentType",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    default_tags = models.ManyToManyField(
        "organization.Tag",
        blank=True,
        related_name="+",
    )
    max_file_size_mb = models.PositiveIntegerField(default=50)
    allowed_mime_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Empty = all types allowed",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Portal Configuration"
        verbose_name_plural = "Portal Configurations"

    def __str__(self):
        return self.name


class DocumentRequest(AuditableModel):
    """
    A request sent to an external contributor asking them to submit
    specific documents through the portal.
    """

    portal = models.ForeignKey(
        PortalConfig,
        on_delete=models.CASCADE,
        related_name="requests",
    )
    title = models.CharField(max_length=256)
    description = models.TextField(blank=True, default="")
    assignee_email = models.EmailField()
    assignee_name = models.CharField(max_length=256, blank=True, default="")
    deadline = models.DateTimeField(null=True, blank=True)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(
        max_length=32,
        choices=REQUEST_STATUS_CHOICES,
        default=REQUEST_PENDING,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.assignee_email}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)


class PortalSubmission(models.Model):
    """
    A file uploaded by an external contributor through the portal
    or in response to a document request.
    """

    portal = models.ForeignKey(
        PortalConfig,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    request = models.ForeignKey(
        DocumentRequest,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions",
    )
    file = models.FileField(upload_to="portal/submissions/")
    original_filename = models.CharField(max_length=512)
    submitter_email = models.EmailField(blank=True, default="")
    submitter_name = models.CharField(max_length=256, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=32,
        choices=SUBMISSION_STATUS_CHOICES,
        default=SUBMISSION_PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default="")
    ingested_document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Submission: {self.original_filename}"
