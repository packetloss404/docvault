"""Mail Rule model for filtering and processing emails."""

from django.db import models

from sources.constants import (
    MAIL_ACTION_CHOICES,
    MAIL_ACTION_DOWNLOAD_ATTACHMENT,
    MAIL_PROCESSED_CHOICES,
    MAIL_PROCESSED_READ,
)


class MailRule(models.Model):
    """Rule for filtering and processing emails from a mail account."""

    name = models.CharField(max_length=192)
    enabled = models.BooleanField(default=True)

    account = models.ForeignKey(
        "sources.MailAccount",
        on_delete=models.CASCADE,
        related_name="rules",
    )

    # Folder to monitor
    folder = models.CharField(
        max_length=256,
        default="INBOX",
    )

    # Filters
    filter_from = models.CharField(max_length=256, blank=True, default="")
    filter_subject = models.CharField(max_length=256, blank=True, default="")
    filter_body = models.CharField(max_length=256, blank=True, default="")
    filter_attachment_filename = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="Glob pattern for attachment filenames.",
    )
    maximum_age = models.PositiveIntegerField(
        default=30,
        help_text="Maximum age of emails to process in days.",
    )

    # Action
    action = models.CharField(
        max_length=32,
        choices=MAIL_ACTION_CHOICES,
        default=MAIL_ACTION_DOWNLOAD_ATTACHMENT,
    )

    # Classification for ingested documents
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
        related_name="+",
    )

    # Post-processing
    processed_action = models.CharField(
        max_length=16,
        choices=MAIL_PROCESSED_CHOICES,
        default=MAIL_PROCESSED_READ,
    )
    processed_folder = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="Folder to move processed emails to (if action is 'move_to_folder').",
    )

    # Order
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "mail rule"
        verbose_name_plural = "mail rules"

    def __str__(self):
        return f"{self.name} ({self.account.name})"
