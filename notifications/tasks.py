"""Celery tasks for the notifications module."""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from documents.constants import (
    TIME_UNIT_DAYS,
    TIME_UNIT_MONTHS,
    TIME_UNIT_WEEKS,
    TIME_UNIT_YEARS,
)

logger = logging.getLogger(__name__)


def _to_timedelta(period, unit):
    """Convert a period + unit pair to a timedelta."""
    if unit == TIME_UNIT_DAYS:
        return timedelta(days=period)
    elif unit == TIME_UNIT_WEEKS:
        return timedelta(weeks=period)
    elif unit == TIME_UNIT_MONTHS:
        return timedelta(days=period * 30)
    elif unit == TIME_UNIT_YEARS:
        return timedelta(days=period * 365)
    return timedelta(days=period)


@shared_task
def enforce_retention(dry_run=False):
    """
    Enforce document retention policies.

    1. Find documents whose document_type has a trash policy and whose
       created_at + trash_period has passed -> soft_delete().
    2. Find soft-deleted documents whose document_type has a delete policy
       and whose deleted_at + delete_period has passed -> hard_delete().

    Run daily (typically at 2 AM via Celery Beat).
    """
    from documents.models import Document
    from documents.models.document_type import DocumentType

    now = timezone.now()
    trash_count = 0
    delete_count = 0

    # Phase 1: Auto-trash documents past retention deadline
    doc_types_with_trash = DocumentType.objects.filter(
        trash_time_period__isnull=False,
        trash_time_unit__isnull=False,
    )
    for doc_type in doc_types_with_trash:
        delta = _to_timedelta(doc_type.trash_time_period, doc_type.trash_time_unit)
        deadline = now - delta
        # Only trash non-deleted documents past the deadline
        docs = Document.objects.filter(
            document_type=doc_type,
            added__lt=deadline,
        )
        for doc in docs:
            if dry_run:
                logger.info(
                    "[DRY RUN] Would trash document %s (%s), type=%s, added=%s",
                    doc.id, doc.title, doc_type.name, doc.added,
                )
            else:
                doc.soft_delete()
                logger.info(
                    "Auto-trashed document %s (%s), type=%s",
                    doc.id, doc.title, doc_type.name,
                )
            trash_count += 1

    # Phase 2: Auto-delete trashed documents past delete deadline
    doc_types_with_delete = DocumentType.objects.filter(
        delete_time_period__isnull=False,
        delete_time_unit__isnull=False,
    )
    for doc_type in doc_types_with_delete:
        delta = _to_timedelta(doc_type.delete_time_period, doc_type.delete_time_unit)
        # Trashed documents: use all_objects to include soft-deleted
        trashed_docs = Document.all_objects.filter(
            document_type=doc_type,
            deleted_at__isnull=False,
        )
        for doc in trashed_docs:
            delete_deadline = doc.deleted_at + delta
            if now >= delete_deadline:
                if dry_run:
                    logger.info(
                        "[DRY RUN] Would delete document %s (%s), trashed=%s",
                        doc.id, doc.title, doc.deleted_at,
                    )
                else:
                    doc.hard_delete()
                    logger.info(
                        "Auto-deleted document %s (%s)",
                        doc.id, doc.title,
                    )
                delete_count += 1

    result = {
        "trashed": trash_count,
        "deleted": delete_count,
        "dry_run": dry_run,
    }
    logger.info("Retention enforcement complete: %s", result)
    return result


@shared_task
def prune_stale_uploads(max_age_hours=24):
    """
    Delete incomplete/stale processing tasks and their uploaded files.

    Cleans up uploads that were started but never completed within
    the configured time window.
    """
    from processing.models import ProcessingTask

    deadline = timezone.now() - timedelta(hours=max_age_hours)
    stale_tasks = ProcessingTask.objects.filter(
        status=ProcessingTask.Status.PENDING,
        created_at__lt=deadline,
    )

    count = 0
    for task in stale_tasks:
        logger.info(
            "Pruning stale upload: task_id=%s, created=%s",
            task.task_id, task.created_at,
        )
        task.status = ProcessingTask.Status.FAILURE
        task.result = "Pruned: stale upload exceeded maximum age."
        task.save(update_fields=["status", "result"])
        count += 1

    logger.info("Pruned %d stale uploads (older than %d hours)", count, max_age_hours)
    return {"pruned": count}
