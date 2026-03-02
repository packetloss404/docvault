"""WorkflowStateAction model - actions executed on state entry/exit."""

from django.db import models

from workflows.constants import ACTION_WHEN_CHOICES, ON_ENTRY


class WorkflowStateAction(models.Model):
    """
    An action to execute when entering or exiting a workflow state.

    Actions are loaded from a dotted Python path (backend_path) and
    configured via backend_data (JSON).
    """

    state = models.ForeignKey(
        "workflows.WorkflowState",
        on_delete=models.CASCADE,
        related_name="actions",
    )
    label = models.CharField(max_length=192)
    enabled = models.BooleanField(default=True)
    when = models.CharField(
        max_length=16,
        choices=ACTION_WHEN_CHOICES,
        default=ON_ENTRY,
    )
    backend_path = models.CharField(
        max_length=256,
        help_text="Dotted path to the action backend class.",
    )
    backend_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON configuration for the action backend.",
    )
    condition = models.TextField(
        blank=True,
        default="",
        help_text="Optional condition expression for this action.",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Execution order (lower runs first).",
    )

    class Meta:
        ordering = ["state", "order", "label"]
        verbose_name = "state action"
        verbose_name_plural = "state actions"

    def __str__(self):
        return f"{self.state.label} - {self.label} ({self.get_when_display()})"
