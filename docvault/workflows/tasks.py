"""Celery tasks for the workflows module."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def launch_workflow_for_document(document_id, template_id, user_id=None):
    """Launch a workflow for a document (async)."""
    from django.contrib.auth.models import User

    from documents.models import Document
    from workflows.engine import launch
    from workflows.models import WorkflowTemplate

    try:
        document = Document.objects.get(pk=document_id)
        template = WorkflowTemplate.objects.get(pk=template_id)
        user = User.objects.get(pk=user_id) if user_id else None
        instance = launch(document, template, user=user)
        return {"instance_id": instance.pk, "status": "launched"}
    except Exception as e:
        logger.exception(
            "Failed to launch workflow %s for document %s",
            template_id, document_id,
        )
        return {"error": str(e)}


@shared_task
def check_workflow_escalations():
    """Check all active workflow instances for overdue escalations."""
    from workflows.engine import check_escalations

    count = check_escalations()
    logger.info("Escalation check completed: %d instances escalated.", count)
    return {"escalated_count": count}


@shared_task
def auto_launch_workflows(document_id):
    """Auto-launch matching workflows for a document."""
    from documents.models import Document
    from workflows.engine import launch
    from workflows.models import WorkflowTemplate

    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        logger.warning("Document %s not found for auto-launch.", document_id)
        return

    templates = WorkflowTemplate.objects.filter(auto_launch=True)
    if document.document_type_id:
        templates = templates.filter(document_types=document.document_type)
    else:
        templates = templates.filter(document_types__isnull=True)

    launched = []
    for template in templates:
        try:
            instance = launch(document, template)
            launched.append(instance.pk)
        except Exception:
            logger.exception(
                "Failed to auto-launch workflow '%s' for document %s",
                template.label, document_id,
            )

    return {"launched_instance_ids": launched}
