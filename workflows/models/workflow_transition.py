"""WorkflowTransition model - transitions between workflow states."""

from django.core.exceptions import ValidationError
from django.db import models


class WorkflowTransition(models.Model):
    """
    A transition between two states in a workflow.

    Both origin and destination states must belong to the same workflow.
    An optional condition expression is evaluated to determine availability.
    """

    workflow = models.ForeignKey(
        "workflows.WorkflowTemplate",
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    label = models.CharField(max_length=192)
    origin_state = models.ForeignKey(
        "workflows.WorkflowState",
        on_delete=models.CASCADE,
        related_name="outgoing_transitions",
    )
    destination_state = models.ForeignKey(
        "workflows.WorkflowState",
        on_delete=models.CASCADE,
        related_name="incoming_transitions",
    )
    condition = models.TextField(
        blank=True,
        default="",
        help_text="Python expression evaluated to determine if transition is available.",
    )

    class Meta:
        ordering = ["workflow", "label"]
        verbose_name = "workflow transition"
        verbose_name_plural = "workflow transitions"

    def __str__(self):
        return f"{self.label} ({self.origin_state.label} -> {self.destination_state.label})"

    def clean(self):
        super().clean()
        if self.origin_state_id and self.destination_state_id:
            if self.origin_state.workflow_id != self.workflow_id:
                raise ValidationError(
                    {"origin_state": "Origin state must belong to the same workflow."}
                )
            if self.destination_state.workflow_id != self.workflow_id:
                raise ValidationError(
                    {"destination_state": "Destination state must belong to the same workflow."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
