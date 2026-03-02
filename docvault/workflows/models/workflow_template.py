"""WorkflowTemplate model - configurable workflow definitions."""

from django.db import models
from django.utils.text import slugify

from core.models import AuditableModel


class WorkflowTemplate(AuditableModel):
    """
    Workflow template defining a reusable workflow with states and transitions.

    Templates can be auto-launched when documents of specific types are created.
    """

    label = models.CharField(max_length=192)
    internal_name = models.SlugField(max_length=192, unique=True)
    auto_launch = models.BooleanField(
        default=False,
        help_text="Automatically launch this workflow for matching document types.",
    )
    document_types = models.ManyToManyField(
        "documents.DocumentType",
        blank=True,
        related_name="workflow_templates",
        help_text="Document types that this workflow applies to.",
    )

    class Meta:
        ordering = ["label"]
        verbose_name = "workflow template"
        verbose_name_plural = "workflow templates"

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):
        if not self.internal_name:
            self.internal_name = slugify(self.label)
        super().save(*args, **kwargs)
