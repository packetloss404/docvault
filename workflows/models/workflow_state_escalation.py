"""WorkflowStateEscalation model - time-based auto-transitions."""

from django.db import models

from workflows.constants import ESCALATION_UNIT_CHOICES, UNIT_DAYS


class WorkflowStateEscalation(models.Model):
    """
    Escalation rule for a workflow state.

    When an instance remains in a state longer than the configured duration,
    the linked transition is automatically executed.
    """

    state = models.ForeignKey(
        "workflows.WorkflowState",
        on_delete=models.CASCADE,
        related_name="escalations",
    )
    transition = models.ForeignKey(
        "workflows.WorkflowTransition",
        on_delete=models.CASCADE,
        related_name="escalation_rules",
        help_text="Transition to execute when escalation triggers.",
    )
    enabled = models.BooleanField(default=True)
    amount = models.PositiveIntegerField(
        help_text="Time duration before escalation triggers.",
    )
    unit = models.CharField(
        max_length=16,
        choices=ESCALATION_UNIT_CHOICES,
        default=UNIT_DAYS,
    )
    condition = models.TextField(
        blank=True,
        default="",
        help_text="Optional condition expression for this escalation.",
    )
    comment = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Comment added to the log when escalation triggers.",
    )
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Priority (lower is checked first).",
    )

    class Meta:
        ordering = ["state", "priority"]
        verbose_name = "state escalation"
        verbose_name_plural = "state escalations"

    def __str__(self):
        return f"{self.state.label} - escalate after {self.amount} {self.unit}"
