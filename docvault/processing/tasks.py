"""Celery tasks for document processing."""

import logging
from pathlib import Path

from celery import shared_task
from django.utils import timezone

from .consumer import DocumentConsumer
from .context import ProcessingContext
from .models import ProcessingTask

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, queue="processing")
def consume_document(self, source_path, original_filename, task_id,
                     user_id, **overrides):
    """Main document consumption Celery task."""
    context = ProcessingContext(
        source_path=Path(source_path),
        original_filename=original_filename,
        task_id=task_id,
        user_id=user_id,
        source_type="api",
        override_title=overrides.get("override_title"),
        override_correspondent=overrides.get("override_correspondent"),
        override_document_type=overrides.get("override_document_type"),
        override_tags=overrides.get("override_tags"),
        override_owner=overrides.get("override_owner"),
        override_asn=overrides.get("override_asn"),
    )

    task = ProcessingTask.objects.get(task_id=task_id)
    task.status = ProcessingTask.Status.STARTED
    task.started_at = timezone.now()
    task.save(update_fields=["status", "started_at"])

    try:
        consumer = DocumentConsumer()
        context = consumer.consume(context)

        if context.errors:
            task.status = ProcessingTask.Status.FAILURE
            task.result = "\n".join(context.errors)
        else:
            task.status = ProcessingTask.Status.SUCCESS
            task.document_id = context.document_id
            task.result = f"Document created: {context.title}"
            task.progress = 1.0

    except Exception as e:
        task.status = ProcessingTask.Status.FAILURE
        task.result = str(e)
        logger.exception("Document consumption failed: %s", original_filename)
        raise
    finally:
        task.completed_at = timezone.now()
        task.save()

    return {"task_id": task_id, "status": task.status, "document_id": context.document_id}


@shared_task
def update_task_progress(task_id, progress, message):
    """Update processing task progress (called by plugins)."""
    try:
        task = ProcessingTask.objects.get(task_id=task_id)
        task.progress = progress
        task.status_message = message
        task.save(update_fields=["progress", "status_message"])
    except ProcessingTask.DoesNotExist:
        logger.warning("Task %s not found for progress update", task_id)
