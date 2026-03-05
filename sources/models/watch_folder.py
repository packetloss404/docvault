"""Watch Folder source model."""

from django.db import models

from sources.constants import CONSUMED_ACTION_CHOICES, CONSUMED_ACTION_MOVE


class WatchFolderSource(models.Model):
    """Configuration for a filesystem watch folder source."""

    source = models.OneToOneField(
        "sources.Source",
        on_delete=models.CASCADE,
        related_name="watch_folder",
    )
    path = models.CharField(
        max_length=1024,
        help_text="Absolute path to watch directory.",
    )
    polling_interval = models.PositiveIntegerField(
        default=300,
        help_text="Polling interval in seconds.",
    )
    consumed_action = models.CharField(
        max_length=16,
        choices=CONSUMED_ACTION_CHOICES,
        default=CONSUMED_ACTION_MOVE,
    )
    consumed_directory = models.CharField(
        max_length=1024,
        blank=True,
        default="",
        help_text="Directory to move consumed files to (if action is 'move').",
    )

    class Meta:
        verbose_name = "watch folder source"
        verbose_name_plural = "watch folder sources"

    def __str__(self):
        return f"WatchFolder: {self.path}"
