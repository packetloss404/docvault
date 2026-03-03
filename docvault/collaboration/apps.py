"""Django app configuration for the collaboration module."""

from django.apps import AppConfig


class CollaborationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "collaboration"
    verbose_name = "Collaboration"

    def ready(self):
        import collaboration.signals  # noqa: F401
