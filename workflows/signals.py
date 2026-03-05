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


@receiver(post_save, sender=Document)
def execute_document_rules(sender, instance, created, **kwargs):
    """Execute trigger-action rules when a document is added or updated."""
    from workflows.constants import TRIGGER_DOCUMENT_ADDED, TRIGGER_DOCUMENT_UPDATED
    from workflows.rules import execute_rule_actions, get_matching_rules

    trigger_type = TRIGGER_DOCUMENT_ADDED if created else TRIGGER_DOCUMENT_UPDATED

    try:
        rules = get_matching_rules(trigger_type, document=instance)
        for rule in rules:
            execute_rule_actions(rule, instance)
    except Exception:
        logger.exception(
            "Error executing rules for document %s (%s)",
            instance.pk,
            "added" if created else "updated",
        )
