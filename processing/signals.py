"""Utilities for sending real-time task status updates via Channels."""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


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
