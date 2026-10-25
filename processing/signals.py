"""Utilities for sending real-time task status updates via Channels."""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ProcessingTask

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ProcessingTask)
def publish_task_status(sender, instance, update_fields=None, **kwargs):
    if update_fields is not None and not set(update_fields) & {"status", "progress", "status_message"}:
        return
    user_id = instance.owner_id
    if not user_id and instance.document_id:
        user_id = instance.document.owner_id
    if not user_id:
        return
    task_id, progress, message, task_status = (
        instance.task_id, instance.progress, instance.status_message, instance.status,
    )
    if task_status in (ProcessingTask.Status.SUCCESS, ProcessingTask.Status.FAILURE):
        message = instance.result or message
    transaction.on_commit(lambda: send_task_update(task_id, user_id, progress, message, task_status))


def send_task_update(task_id, user_id, progress, message, task_status):
    """Send a task progress update to the user's WebSocket group."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}_tasks",
            {
                "type": "task.update",
                "data": {
                    "task_id": str(task_id),
                    "progress": progress,
                    "message": message,
                    "status": task_status,
                },
            },
        )
    except Exception:
        logger.debug("Could not send WebSocket update for task %s", task_id)
