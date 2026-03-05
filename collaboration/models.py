"""Models for the collaboration module."""

import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import AuditableModel, SoftDeleteModel


class Comment(SoftDeleteModel, AuditableModel):
    """Comment/note attached to a document.

    Supports markdown content and soft deletion.
    """

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    text = models.TextField(help_text="Comment text (markdown supported).")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "comment"
        verbose_name_plural = "comments"

    def __str__(self):
        return f"Comment by {self.user} on {self.document}"


class Checkout(models.Model):
    """Check-in/check-out lock for a document.

    Only one checkout per document (enforced by OneToOneField).
    """

    document = models.OneToOneField(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="checkout",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="checkouts",
    )
    checked_out_at = models.DateTimeField(auto_now_add=True)
    expiration = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Auto-release after this time.",
    )
    block_new_uploads = models.BooleanField(
        default=True,
        help_text="Prevent new file uploads while checked out.",
    )

    class Meta:
        verbose_name = "checkout"
        verbose_name_plural = "checkouts"

    def __str__(self):
        return f"{self.document} checked out by {self.user}"

    @property
    def is_expired(self):
        if self.expiration is None:
            return False
        return timezone.now() >= self.expiration


def _generate_slug():
    return secrets.token_urlsafe(16)


class ShareLink(AuditableModel):
    """Public share link for a document.

    Allows guest access with optional password and expiration.
    """

    FILE_VERSION_CHOICES = [
        ("original", "Original"),
        ("archive", "Archive (PDF/A)"),
    ]

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="share_links",
    )
    slug = models.SlugField(
        max_length=64,
        unique=True,
        default=_generate_slug,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_share_links",
    )
    expiration = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Link expires after this time.",
    )
    password_hash = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="SHA-256 hash of the share link password.",
    )
    file_version = models.CharField(
        max_length=16,
        choices=FILE_VERSION_CHOICES,
        default="original",
    )
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "share link"
        verbose_name_plural = "share links"

    def __str__(self):
        return f"Share: {self.slug} → {self.document}"

    @property
    def is_expired(self):
        if self.expiration is None:
            return False
        return timezone.now() >= self.expiration

    @property
    def has_password(self):
        return bool(self.password_hash)

    def set_password(self, password: str):
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password: str) -> bool:
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()
