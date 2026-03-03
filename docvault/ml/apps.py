"""App configuration for the ML classification module."""

from django.apps import AppConfig


class MlConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ml"
    verbose_name = "ML Classification"
