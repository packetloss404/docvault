"""WorkflowState model - states within a workflow template."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class WorkflowState(models.Model):
    """
    A state in a workflow template.

    Exactly one state per workflow should be marked as initial.
    States marked as final indicate workflow completion.
    """

    workflow = models.ForeignKey(
        "workflows.WorkflowTemplate",
        on_delete=models.CASCADE,
        related_name="states",
    )
    label = models.CharField(max_length=192)
    initial = models.BooleanField(
        default=False,
        help_text="Whether this is the starting state for new instances.",
    )
    final = models.BooleanField(
        default=False,
        help_text="Whether reaching this state completes the workflow.",
    )
    completion = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Completion percentage (0-100) for progress tracking.",
    )

    class Meta:
        ordering = ["workflow", "label"]
        verbose_name = "workflow state"
        verbose_name_plural = "workflow states"
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "label"],
                name="unique_state_label_per_workflow",
            ),
        ]

    def __str__(self):
        return f"{self.workflow.label} - {self.label}"
