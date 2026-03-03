"""Celery tasks for the collaboration module."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="collaboration.release_expired_checkouts")
def release_expired_checkouts():
    """Release all expired document checkouts.

    Scheduled to run every 5 minutes via Celery beat.
    """
    from .models import Checkout

    expired = Checkout.objects.filter(
        expiration__isnull=False,
        expiration__lte=timezone.now(),
    )
    count = expired.count()
    expired.delete()

    if count > 0:
        logger.info("Released %d expired checkouts.", count)
    return {"released": count}


@shared_task(name="collaboration.cleanup_expired_share_links")
def cleanup_expired_share_links():
    """Delete share links that have been expired for more than 30 days."""
    from .models import ShareLink

    cutoff = timezone.now() - timezone.timedelta(days=30)
    expired = ShareLink.objects.filter(
        expiration__isnull=False,
        expiration__lte=cutoff,
    )
    count = expired.count()
    expired.delete()

    if count > 0:
        logger.info("Cleaned up %d expired share links.", count)
    return {"cleaned": count}
