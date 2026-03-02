"""Signals for the workflows module - auto-launch workflows on document creation."""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from documents.models import Document

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Document)
def auto_launch_workflows(sender, instance, created, **kwargs):
    """Auto-launch workflows for newly created documents matching workflow templates."""
    if not created:
        return

    from workflows.models import WorkflowTemplate

    templates = WorkflowTemplate.objects.filter(auto_launch=True)
    if instance.document_type_id:
        templates = templates.filter(document_types=instance.document_type)
    else:
        templates = templates.filter(document_types__isnull=True)

    for template in templates:
        from workflows.engine import launch

        try:
            launch(instance, template)
        except Exception:
            logger.exception(
                "Failed to auto-launch workflow '%s' for document %s",
                template.label,
                instance.pk,
            )
