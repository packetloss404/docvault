"""Celery tasks for the legal_hold module."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def notify_custodians(hold_id):
    """
    Send notification emails to all custodians of a legal hold.

    Updates the notified_at timestamp on each custodian record.
    """
    from django.conf import settings
    from django.core.mail import send_mail
    from django.utils import timezone

    from .models import LegalHold

    try:
        hold = LegalHold.objects.get(pk=hold_id)
    except LegalHold.DoesNotExist:
        logger.error("Legal hold %s not found for notification", hold_id)
        return

    custodians = hold.custodians.select_related("user").filter(
        notified_at__isnull=True
    )
    now = timezone.now()
    notified_count = 0

    for custodian in custodians:
        user = custodian.user
        if not user.email:
            logger.warning(
                "Custodian %s (user %s) has no email address",
                custodian.pk,
                user.pk,
            )
            continue

        try:
            send_mail(
                subject=f"Legal Hold Notice: {hold.name}",
                message=(
                    f"Dear {user.get_full_name() or user.username},\n\n"
                    f"You have been designated as a custodian for the following legal hold:\n\n"
                    f"  Hold Name: {hold.name}\n"
                    f"  Matter Number: {hold.matter_number or 'N/A'}\n"
                    f"  Description: {hold.description or 'N/A'}\n\n"
                    f"Please acknowledge receipt of this notice by logging into DocVault.\n\n"
                    f"This is an automated notification. Do not reply to this email."
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@docvault.local"),
                recipient_list=[user.email],
                fail_silently=False,
            )
            custodian.notified_at = now
            custodian.save(update_fields=["notified_at"])
            notified_count += 1
        except Exception:
            logger.exception(
                "Failed to send notification to custodian %s (user %s)",
                custodian.pk,
                user.pk,
            )

    logger.info(
        "Notified %d custodians for hold %s (%s)",
        notified_count,
        hold.pk,
        hold.name,
    )


@shared_task
def reevaluate_holds():
    """
    Daily task to re-evaluate all active holds with SEARCH_QUERY criteria.

    Finds new documents matching the query criteria that may have been
    added since the hold was last evaluated.
    """
    from .constants import ACTIVE, SEARCH_QUERY
    from .engine import refresh_hold
    from .models import LegalHold

    holds = LegalHold.objects.filter(
        status=ACTIVE,
        criteria__criteria_type=SEARCH_QUERY,
    ).distinct()

    total_new = 0
    for hold in holds:
        try:
            new_count = refresh_hold(hold)
            total_new += new_count
        except Exception:
            logger.exception(
                "Failed to re-evaluate hold %s (%s)", hold.pk, hold.name
            )

    logger.info(
        "Re-evaluated %d holds with search query criteria; %d new documents added",
        holds.count(),
        total_new,
    )
