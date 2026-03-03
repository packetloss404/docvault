"""WorkflowRule model - binds triggers to actions."""

from django.db import models

from core.models import AuditableModel


class WorkflowRule(AuditableModel):
    """
    A trigger-action rule that automates document processing.

    When any associated trigger fires, all associated actions
    are executed in order against the matching document.
    """

    name = models.CharField(max_length=192)
    enabled = models.BooleanField(default=True)
    triggers = models.ManyToManyField(
        "workflows.WorkflowTrigger",
        related_name="rules",
        blank=True,
    )
    actions = models.ManyToManyField(
        "workflows.WorkflowAction",
        related_name="rules",
        blank=True,
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Execution order relative to other rules.",
    )

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "workflow rule"
        verbose_name_plural = "workflow rules"

    def __str__(self):
        return self.name
