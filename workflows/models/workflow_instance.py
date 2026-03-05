"""WorkflowInstance model - runtime workflow instances bound to documents."""

from django.db import models
from django.utils import timezone


class WorkflowInstance(models.Model):
    """
    A running instance of a workflow template attached to a document.

    Each document can have at most one instance per workflow template.
    """

    workflow = models.ForeignKey(
        "workflows.WorkflowTemplate",
        on_delete=models.CASCADE,
        related_name="instances",
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="workflow_instances",
    )
    current_state = models.ForeignKey(
        "workflows.WorkflowState",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Workflow context data (accumulated transition field values).",
    )
    launched_at = models.DateTimeField(default=timezone.now)
    state_changed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-launched_at"]
        verbose_name = "workflow instance"
        verbose_name_plural = "workflow instances"
        constraints = [
            models.UniqueConstraint(
                fields=["document", "workflow"],
                name="unique_workflow_per_document",
            ),
        ]

    def __str__(self):
        state_label = self.current_state.label if self.current_state else "No state"
        return f"{self.workflow.label} on {self.document} ({state_label})"

    @property
    def is_complete(self):
        return self.current_state is not None and self.current_state.final
