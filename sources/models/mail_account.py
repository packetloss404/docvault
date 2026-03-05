"""Mail Account model for IMAP email sources."""

from django.db import models

from sources.constants import (
    MAIL_ACCOUNT_IMAP,
    MAIL_ACCOUNT_TYPE_CHOICES,
    MAIL_SECURITY_CHOICES,
    MAIL_SECURITY_SSL,
)


class MailAccount(models.Model):
    """IMAP email account configuration."""

    name = models.CharField(max_length=192)
    enabled = models.BooleanField(default=True)

    # Connection
    imap_server = models.CharField(max_length=256)
    port = models.PositiveIntegerField(default=993)
    security = models.CharField(
        max_length=16,
        choices=MAIL_SECURITY_CHOICES,
        default=MAIL_SECURITY_SSL,
    )

    # Authentication
    account_type = models.CharField(
        max_length=32,
        choices=MAIL_ACCOUNT_TYPE_CHOICES,
        default=MAIL_ACCOUNT_IMAP,
    )
    username = models.CharField(max_length=256)
    password = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="IMAP password or app-specific password.",
    )

    # OAuth2 tokens (for Gmail/Outlook)
    oauth_client_id = models.CharField(max_length=512, blank=True, default="")
    oauth_client_secret = models.CharField(max_length=512, blank=True, default="")
    oauth_access_token = models.TextField(blank=True, default="")
    oauth_refresh_token = models.TextField(blank=True, default="")
    oauth_token_expiry = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "mail account"
        verbose_name_plural = "mail accounts"

    def __str__(self):
        return f"{self.name} ({self.username})"
