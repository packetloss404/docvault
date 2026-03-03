"""User preferences for dashboard layout, theme, and locale."""

from django.conf import settings
from django.db import models


class UserPreferences(models.Model):
    """Per-user settings for UI customization."""

    THEME_LIGHT = "light"
    THEME_DARK = "dark"
    THEME_SYSTEM = "system"

    THEME_CHOICES = [
        (THEME_LIGHT, "Light"),
        (THEME_DARK, "Dark"),
        (THEME_SYSTEM, "System"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    theme = models.CharField(max_length=8, choices=THEME_CHOICES, default=THEME_SYSTEM)
    language = models.CharField(max_length=8, default="en")
    dashboard_layout = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of widget configs for the dashboard.",
    )

    class Meta:
        verbose_name = "user preferences"
        verbose_name_plural = "user preferences"

    def __str__(self):
        return f"Preferences({self.user.username})"
