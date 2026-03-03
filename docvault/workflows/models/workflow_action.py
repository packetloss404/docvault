"""WorkflowAction model - defines what a workflow rule does."""

from django.db import models

from workflows.constants import ACTION_TYPE_CHOICES


class WorkflowAction(models.Model):
    """
    An action to execute when a workflow rule fires.

    The 'configuration' JSON field holds action-specific parameters,
    e.g. tag_ids for ADD_TAG, email subject/body for SEND_EMAIL, etc.
    """

    type = models.CharField(max_length=32, choices=ACTION_TYPE_CHOICES)
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Action-specific configuration as JSON.",
    )
    order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "workflow action"
        verbose_name_plural = "workflow actions"

    def __str__(self):
        return f"{self.get_type_display()} action"
