"""WorkflowTransitionField model - fields collected during transitions."""

from django.db import models

from workflows.constants import FIELD_TYPE_CHAR, FIELD_TYPE_CHOICES


class WorkflowTransitionField(models.Model):
    """
    A form field presented to the user during a transition.

    Values collected are stored in the workflow instance log entry.
    """

    transition = models.ForeignKey(
        "workflows.WorkflowTransition",
        on_delete=models.CASCADE,
        related_name="fields",
    )
    name = models.CharField(max_length=128, help_text="Internal field name.")
    label = models.CharField(max_length=192, help_text="Display label.")
    field_type = models.CharField(
        max_length=16,
        choices=FIELD_TYPE_CHOICES,
        default=FIELD_TYPE_CHAR,
    )
    required = models.BooleanField(default=False)
    default = models.CharField(max_length=512, blank=True, default="")
    help_text = models.CharField(max_length=512, blank=True, default="")

    class Meta:
        ordering = ["transition", "name"]
        verbose_name = "transition field"
        verbose_name_plural = "transition fields"

    def __str__(self):
        return f"{self.transition.label} - {self.label}"
