"""Correspondent model - sender/recipient with matching."""

from django.db import models

from .base import MatchingModel


class Correspondent(MatchingModel):
    """
    Correspondent (sender/recipient) associated with documents.

    Uses matching algorithms to auto-assign to incoming documents
    based on content analysis.
    """

    class Meta:
        ordering = ["name"]
        verbose_name = "correspondent"
        verbose_name_plural = "correspondents"
        constraints = [
            models.UniqueConstraint(fields=["name"], name="unique_correspondent_name"),
        ]
