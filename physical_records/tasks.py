"""Celery tasks for the physical_records module."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="physical_records.check_overdue_charge_outs")
def check_overdue_charge_outs():
    """
    Find charge-outs past their expected_return date and update status to OVERDUE.

    This task should be scheduled to run periodically (e.g., every hour)
    via Celery Beat.
    """
    from .constants import CHECKED_OUT, OVERDUE
    from .models import ChargeOut

    now = timezone.now()
    overdue_qs = ChargeOut.objects.filter(
        status=CHECKED_OUT,
        expected_return__lt=now,
    )

    count = overdue_qs.update(status=OVERDUE)

    if count > 0:
        logger.info("Marked %d charge-out(s) as overdue.", count)

    return {"overdue_count": count}
