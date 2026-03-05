"""Signal handlers for the collaboration module."""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.constants import EVENT_COMMENT_ADDED
from notifications.dispatch import send_notification

from .models import Comment

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Comment)
def notify_comment_added(sender, instance, created, **kwargs):
    """Send notification when a new comment is added to a document."""
    if not created:
        return

    document = instance.document
    if not document.owner:
        return

    # Don't notify the commenter about their own comment
    if document.owner == instance.user:
        return

    send_notification(
        user=document.owner,
        event_type=EVENT_COMMENT_ADDED,
        title="New comment",
        body=f'{instance.user.username} commented on "{document.title}".',
        document=document,
    )
