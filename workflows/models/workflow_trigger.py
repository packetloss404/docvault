"""WorkflowTrigger model - defines when a workflow rule should fire."""

from django.db import models

from workflows.constants import (
    MATCH_NONE,
    MATCHING_ALGORITHM_CHOICES,
    TRIGGER_TYPE_CHOICES,
)


class WorkflowTrigger(models.Model):
    """
    A trigger condition for a workflow rule.

    Defines the event type and optional filters that determine
    when the associated rule's actions should execute.
    """

    type = models.CharField(max_length=32, choices=TRIGGER_TYPE_CHOICES)
    enabled = models.BooleanField(default=True)

    # Filename / path filters (glob patterns)
    filter_filename = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="Glob pattern to match against the document filename.",
    )
    filter_path = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Glob pattern to match against the source file path.",
    )

    # Classification filters
    filter_has_tags = models.ManyToManyField(
        "organization.Tag",
        blank=True,
        related_name="+",
    )
    filter_has_correspondent = models.ForeignKey(
        "organization.Correspondent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    filter_has_document_type = models.ForeignKey(
        "documents.DocumentType",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    # Custom field query (JSON-based complex filter)
    filter_custom_field_query = models.JSONField(default=dict, blank=True)

    # Text matching
    match_pattern = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="Text pattern to match against document title/content.",
    )
    matching_algorithm = models.IntegerField(
        choices=MATCHING_ALGORITHM_CHOICES,
        default=MATCH_NONE,
    )

    # Schedule settings (for SCHEDULED type)
    schedule_interval_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Interval in minutes for scheduled triggers.",
    )

    class Meta:
        ordering = ["type", "id"]
        verbose_name = "workflow trigger"
        verbose_name_plural = "workflow triggers"

    def __str__(self):
        return f"{self.get_type_display()} trigger"
