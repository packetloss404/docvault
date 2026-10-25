"""Signal handlers for the notifications module."""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from documents.models import Document
from processing.models import ProcessingTask

from .constants import (
    EVENT_DOCUMENT_ADDED,
    EVENT_DOCUMENT_PROCESSED,
    EVENT_PROCESSING_FAILED,
)
from .dispatch import send_notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Document)
def notify_document_added(sender, instance, created, **kwargs):
    """Send notification when a new document is added."""
    if not created:
        return
    if not instance.owner:
        return

    send_notification(
        user=instance.owner,
        event_type=EVENT_DOCUMENT_ADDED,
        title="Document added",
        body=f'"{instance.title}" has been added to DocVault.',
        document=instance,
    )


@receiver(pre_save, sender=ProcessingTask)
def remember_processing_status(sender, instance, update_fields=None, raw=False, **kwargs):
    if raw or (update_fields is not None and "status" not in update_fields):
        return
    instance._notification_previous_status = (
        sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first() if instance.pk else None
    )


@receiver(post_save, sender=ProcessingTask)
def notify_processing_complete(sender, instance, update_fields=None, raw=False, **kwargs):
    """Send notification when document processing completes or fails."""
    if raw or (update_fields is not None and "status" not in update_fields):
        return
    if getattr(instance, "_notification_previous_status", None) == instance.status:
        return
    if instance.status == ProcessingTask.Status.SUCCESS:
        if not instance.document or not instance.document.owner:
            return
        send_notification(
            user=instance.document.owner,
            event_type=EVENT_DOCUMENT_PROCESSED,
            title="Document processed",
            body=f'"{instance.document.title}" has been processed successfully.',
            document=instance.document,
        )
    elif instance.status == ProcessingTask.Status.FAILURE:
        document = instance.document if instance.document_id else None
        user = document.owner if document and document.owner_id else instance.owner
        if not user:
            return
        send_notification(
            user=user,
            event_type=EVENT_PROCESSING_FAILED,
            title="Processing failed",
            body=f"Processing failed for task {instance.task_id}: {instance.result or 'Unknown error'}",
            document=document,
        )
