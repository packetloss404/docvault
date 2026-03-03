"""Celery tasks for the contributor portal."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def send_request_email(request_id):
    """Send document request email to assignee with token link."""
    from django.conf import settings
    from django.core.mail import send_mail
    from django.utils import timezone

    from .models import DocumentRequest

    doc_request = DocumentRequest.objects.select_related("portal").get(pk=request_id)
    portal = doc_request.portal

    subject = f"[{portal.name}] Document Request: {doc_request.title}"
    body = (
        f"Hello {doc_request.assignee_name or 'there'},\n\n"
        f"You have been asked to submit documents for: {doc_request.title}\n\n"
    )
    if doc_request.description:
        body += f"{doc_request.description}\n\n"
    if doc_request.deadline:
        body += f"Deadline: {doc_request.deadline.strftime('%Y-%m-%d %H:%M %Z')}\n\n"

    body += (
        f"Please use the following link to upload your documents:\n"
        f"/request/{doc_request.token}/\n\n"
        f"Thank you."
    )

    from_email = getattr(settings, "PORTAL_FROM_EMAIL", "noreply@docvault.local")

    send_mail(
        subject=subject,
        message=body,
        from_email=from_email,
        recipient_list=[doc_request.assignee_email],
        fail_silently=False,
    )

    doc_request.sent_at = timezone.now()
    doc_request.save(update_fields=["sent_at"])

    logger.info(
        "Sent document request email: request_id=%s, to=%s",
        request_id, doc_request.assignee_email,
    )
    return {"request_id": request_id, "sent_to": doc_request.assignee_email}


@shared_task
def send_deadline_reminder(request_id):
    """Send deadline reminder to assignee."""
    from django.conf import settings
    from django.core.mail import send_mail
    from django.utils import timezone

    from .models import DocumentRequest

    doc_request = DocumentRequest.objects.select_related("portal").get(pk=request_id)
    portal = doc_request.portal

    subject = f"[{portal.name}] Reminder: {doc_request.title}"
    body = (
        f"Hello {doc_request.assignee_name or 'there'},\n\n"
        f"This is a reminder that the following document request is approaching "
        f"its deadline:\n\n"
        f"  Title: {doc_request.title}\n"
    )
    if doc_request.deadline:
        body += f"  Deadline: {doc_request.deadline.strftime('%Y-%m-%d %H:%M %Z')}\n"

    body += (
        f"\nPlease use the following link to upload your documents:\n"
        f"/request/{doc_request.token}/\n\n"
        f"Thank you."
    )

    from_email = getattr(settings, "PORTAL_FROM_EMAIL", "noreply@docvault.local")

    send_mail(
        subject=subject,
        message=body,
        from_email=from_email,
        recipient_list=[doc_request.assignee_email],
        fail_silently=False,
    )

    doc_request.reminder_sent_at = timezone.now()
    doc_request.save(update_fields=["reminder_sent_at"])

    logger.info(
        "Sent deadline reminder: request_id=%s, to=%s",
        request_id, doc_request.assignee_email,
    )
    return {"request_id": request_id, "reminded": doc_request.assignee_email}


@shared_task
def expire_overdue_requests():
    """Mark overdue requests as expired."""
    from django.utils import timezone

    from .constants import REQUEST_EXPIRED, REQUEST_PARTIALLY_FULFILLED, REQUEST_PENDING
    from .models import DocumentRequest

    overdue = DocumentRequest.objects.filter(
        deadline__lt=timezone.now(),
        status__in=[REQUEST_PENDING, REQUEST_PARTIALLY_FULFILLED],
    )
    count = overdue.update(status=REQUEST_EXPIRED)

    logger.info("Expired %d overdue document requests.", count)
    return {"expired": count}


@shared_task
def check_deadline_reminders():
    """Check for requests approaching deadline and send reminders."""
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone

    from .constants import REQUEST_PENDING
    from .models import DocumentRequest

    reminder_days = getattr(settings, "PORTAL_REQUEST_REMINDER_DAYS", 3)
    threshold = timezone.now() + timedelta(days=reminder_days)

    upcoming = DocumentRequest.objects.filter(
        deadline__lte=threshold,
        deadline__gt=timezone.now(),
        status=REQUEST_PENDING,
        reminder_sent_at__isnull=True,
    )

    count = 0
    for req in upcoming:
        send_deadline_reminder.delay(req.pk)
        count += 1

    logger.info("Queued %d deadline reminders.", count)
    return {"reminders_queued": count}
