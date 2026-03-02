"""WorkflowInstanceLogEntry model - audit trail for workflow transitions."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class WorkflowInstanceLogEntry(models.Model):
    """
    Audit log entry for a workflow instance state transition.

    Records who performed the transition, when, and any field values submitted.
    """

    instance = models.ForeignKey(
        "workflows.WorkflowInstance",
        on_delete=models.CASCADE,
        related_name="log_entries",
    )
    datetime = models.DateTimeField(default=timezone.now, db_index=True)
    transition = models.ForeignKey(
        "workflows.WorkflowTransition",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    comment = models.TextField(blank=True, default="")
    transition_field_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="Values submitted for transition fields.",
    )

    class Meta:
        ordering = ["-datetime"]
        verbose_name = "workflow log entry"
        verbose_name_plural = "workflow log entries"

    def __str__(self):
        transition_label = self.transition.label if self.transition else "Launch"
        return f"{self.instance} - {transition_label} at {self.datetime}"
