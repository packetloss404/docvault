"""Models for the notifications module."""

from django.conf import settings
from django.db import models

from .constants import (
    CHANNEL_CHOICES,
    CHANNEL_IN_APP,
    EVENT_TYPE_CHOICES,
)


class Notification(models.Model):
    """
    A notification sent to a user about a system event.

    Tracks read/unread state and optionally links to a document.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    event_type = models.CharField(max_length=32, choices=EVENT_TYPE_CHOICES)
    title = models.CharField(max_length=256)
    body = models.TextField(blank=True, default="")
    document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "read", "-created_at"]),
        ]
        verbose_name = "notification"
        verbose_name_plural = "notifications"

    def __str__(self):
        status = "read" if self.read else "unread"
        return f"[{status}] {self.title} -> {self.user.username}"


class NotificationPreference(models.Model):
    """
    Per-user notification delivery preferences.

    Each row controls whether a specific event_type is delivered
    via a specific channel (in_app, email, webhook).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    event_type = models.CharField(max_length=32, choices=EVENT_TYPE_CHOICES)
    channel = models.CharField(
        max_length=16,
        choices=CHANNEL_CHOICES,
        default=CHANNEL_IN_APP,
    )
    enabled = models.BooleanField(default=True)

    # Webhook-specific config
    webhook_url = models.URLField(blank=True, default="")

    class Meta:
        unique_together = [["user", "event_type", "channel"]]
        ordering = ["user", "event_type", "channel"]
        verbose_name = "notification preference"
        verbose_name_plural = "notification preferences"

    def __str__(self):
        state = "on" if self.enabled else "off"
        return f"{self.user.username}: {self.event_type}/{self.channel} = {state}"


class Quota(models.Model):
    """
    Usage quota for a user or group.

    Null user + null group = global default quota.
    User-specific quotas take priority over group, which takes
    priority over global.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="quotas",
    )
    group = models.ForeignKey(
        "auth.Group",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="quotas",
    )
    max_documents = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of documents allowed. Null = unlimited.",
    )
    max_storage_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Maximum storage in bytes. Null = unlimited.",
    )

    class Meta:
        ordering = ["user", "group"]
        verbose_name = "quota"
        verbose_name_plural = "quotas"

    def __str__(self):
        if self.user:
            target = f"User: {self.user.username}"
        elif self.group:
            target = f"Group: {self.group.name}"
        else:
            target = "Global"
        return f"Quota({target})"
