"""
Stateless service module for e-signature workflow orchestration.

All business logic for signature requests lives here, keeping views
and models thin. Functions accept model instances and perform
state transitions, audit logging, and task dispatching.
"""

import logging

from django.db import transaction
from django.utils import timezone

from .constants import (
    EVENT_CANCELLED,
    EVENT_COMPLETED,
    EVENT_DECLINED,
    EVENT_PAGE_VIEWED,
    EVENT_SENT,
    EVENT_SIGNED,
    EVENT_VIEWED,
    ORDER_SEQUENTIAL,
    REQUEST_CANCELLED,
    REQUEST_COMPLETED,
    REQUEST_DRAFT,
    REQUEST_IN_PROGRESS,
    REQUEST_SENT,
    SIGNER_DECLINED,
    SIGNER_PENDING,
    SIGNER_SIGNED,
    SIGNER_VIEWED,
)
from .models import SignatureAuditEvent

logger = logging.getLogger(__name__)


class SignatureEngineError(Exception):
    """Base exception for signature engine errors."""


class InvalidStateError(SignatureEngineError):
    """Raised when an operation is invalid for the current state."""


class ValidationError(SignatureEngineError):
    """Raised when validation fails for an engine operation."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@transaction.atomic
def send_request(signature_request):
    """
    Validate and send a signature request to its signers.

    For sequential signing, only the first pending signer is notified.
    For parallel signing, all signers are notified simultaneously.

    Raises:
        InvalidStateError: If the request is not in DRAFT status.
        ValidationError: If there are no signers or no fields.
    """
    if signature_request.status != REQUEST_DRAFT:
        raise InvalidStateError(
            f"Cannot send request in '{signature_request.status}' status. "
            f"Only draft requests can be sent."
        )

    if not signature_request.signers.exists():
        raise ValidationError("Cannot send a request with no signers.")

    if not signature_request.fields.exists():
        raise ValidationError("Cannot send a request with no signature fields.")

    signature_request.status = REQUEST_SENT
    signature_request.save(update_fields=["status", "updated_at"])

    SignatureAuditEvent.objects.create(
        request=signature_request,
        event_type=EVENT_SENT,
        detail={"signing_order": signature_request.signing_order},
    )

    # Dispatch email tasks
    from .tasks import send_signature_email

    if signature_request.signing_order == ORDER_SEQUENTIAL:
        next_signer = get_next_signer(signature_request)
        if next_signer:
            send_signature_email.delay(next_signer.pk)
    else:
        for signer in signature_request.signers.all():
            send_signature_email.delay(signer.pk)

    logger.info(
        "Sent signature request %s (%s order)",
        signature_request.pk,
        signature_request.signing_order,
    )
    return signature_request


@transaction.atomic
def record_view(signer, ip_address=None):
    """
    Record that a signer has viewed the signing page.

    Only transitions from PENDING to VIEWED. If the signer has already
    viewed or signed, this is a no-op for status but still logs the event.
    """
    request = signer.request

    if signer.status == SIGNER_PENDING:
        signer.status = SIGNER_VIEWED
        signer.save(update_fields=["status"])

        # Transition request from SENT to IN_PROGRESS on first view
        if request.status == REQUEST_SENT:
            request.status = REQUEST_IN_PROGRESS
            request.save(update_fields=["status", "updated_at"])

    SignatureAuditEvent.objects.create(
        request=request,
        signer=signer,
        event_type=EVENT_VIEWED,
        ip_address=ip_address,
        detail={"signer_name": signer.name, "signer_email": signer.email},
    )

    logger.info(
        "Signer %s viewed request %s",
        signer.email,
        request.pk,
    )
    return signer


def record_page_view(signer, page, ip_address=None):
    """
    Record that a signer has viewed a specific page of the document.

    Adds the page number to the signer's viewed_pages list (deduplicated).
    """
    viewed = list(signer.viewed_pages or [])
    if page not in viewed:
        viewed.append(page)
        signer.viewed_pages = viewed
        signer.save(update_fields=["viewed_pages"])

    SignatureAuditEvent.objects.create(
        request=signer.request,
        signer=signer,
        event_type=EVENT_PAGE_VIEWED,
        ip_address=ip_address,
        detail={"page": page},
    )

    return signer


@transaction.atomic
def complete_signing(signer, field_values, ip_address=None, user_agent=""):
    """
    Complete the signing process for a signer.

    Validates that all required fields have values, updates field data,
    and transitions the signer to SIGNED status.

    For sequential signing, triggers the next signer. For parallel signing,
    checks if all signers are done.

    Args:
        signer: The Signer instance.
        field_values: List of dicts with 'field_id' and 'value' keys.
        ip_address: Client IP address.
        user_agent: Client user agent string.

    Raises:
        InvalidStateError: If signer is not in PENDING or VIEWED status.
        ValidationError: If required fields are missing values.
    """
    if signer.status not in (SIGNER_PENDING, SIGNER_VIEWED):
        raise InvalidStateError(
            f"Signer '{signer.email}' is in '{signer.status}' status "
            f"and cannot complete signing."
        )

    request = signer.request

    # Build a map of field_id -> value from the submitted data
    value_map = {fv["field_id"]: fv["value"] for fv in field_values}

    # Validate required fields
    signer_fields = signer.fields.all()
    now = timezone.now()
    missing = []

    for field in signer_fields:
        submitted_value = value_map.get(field.pk, "")
        if field.required and not submitted_value:
            missing.append(field.pk)
        else:
            field.value = submitted_value
            field.signed_at = now
            field.save(update_fields=["value", "signed_at"])

    if missing:
        raise ValidationError(
            f"Required fields are missing values: {missing}"
        )

    # Update signer
    signer.status = SIGNER_SIGNED
    signer.signed_at = now
    signer.ip_address = ip_address
    signer.user_agent = user_agent
    signer.save(update_fields=[
        "status", "signed_at", "ip_address", "user_agent",
    ])

    SignatureAuditEvent.objects.create(
        request=request,
        signer=signer,
        event_type=EVENT_SIGNED,
        ip_address=ip_address,
        detail={
            "signer_name": signer.name,
            "signer_email": signer.email,
            "fields_completed": len(value_map),
        },
    )

    logger.info(
        "Signer %s completed signing on request %s",
        signer.email,
        request.pk,
    )

    # Check for completion or advance to next signer
    if check_completion(request):
        _mark_completed(request)
    elif request.signing_order == ORDER_SEQUENTIAL:
        next_signer = get_next_signer(request)
        if next_signer:
            from .tasks import send_signature_email

            send_signature_email.delay(next_signer.pk)

    return signer


@transaction.atomic
def decline_signing(signer, reason="", ip_address=None):
    """
    Record that a signer has declined to sign.

    Args:
        signer: The Signer instance.
        reason: Optional reason for declining.
        ip_address: Client IP address.

    Raises:
        InvalidStateError: If signer has already signed or declined.
    """
    if signer.status in (SIGNER_SIGNED, SIGNER_DECLINED):
        raise InvalidStateError(
            f"Signer '{signer.email}' is in '{signer.status}' status "
            f"and cannot decline."
        )

    signer.status = SIGNER_DECLINED
    signer.ip_address = ip_address
    signer.save(update_fields=["status", "ip_address"])

    SignatureAuditEvent.objects.create(
        request=signer.request,
        signer=signer,
        event_type=EVENT_DECLINED,
        ip_address=ip_address,
        detail={
            "signer_name": signer.name,
            "signer_email": signer.email,
            "reason": reason,
        },
    )

    logger.info(
        "Signer %s declined request %s: %s",
        signer.email,
        signer.request.pk,
        reason,
    )

    # Check if all signers are now done (signed or declined)
    if check_completion(signer.request):
        _mark_completed(signer.request)

    return signer


@transaction.atomic
def cancel_request(signature_request, user=None):
    """
    Cancel a signature request.

    Args:
        signature_request: The SignatureRequest instance.
        user: The user who cancelled the request.

    Raises:
        InvalidStateError: If the request is already completed or cancelled.
    """
    if signature_request.status in (REQUEST_COMPLETED, REQUEST_CANCELLED):
        raise InvalidStateError(
            f"Cannot cancel request in '{signature_request.status}' status."
        )

    signature_request.status = REQUEST_CANCELLED
    if user:
        signature_request.updated_by = user
    signature_request.save(update_fields=["status", "updated_by", "updated_at"])

    SignatureAuditEvent.objects.create(
        request=signature_request,
        event_type=EVENT_CANCELLED,
        detail={
            "cancelled_by": user.username if user else "system",
        },
    )

    logger.info(
        "Signature request %s cancelled by %s",
        signature_request.pk,
        user.username if user else "system",
    )
    return signature_request


def get_next_signer(signature_request):
    """
    For sequential signing, return the lowest-order signer
    that is still PENDING or VIEWED.

    Returns None if no pending signers remain.
    """
    return (
        signature_request.signers
        .filter(status__in=[SIGNER_PENDING, SIGNER_VIEWED])
        .order_by("order", "pk")
        .first()
    )


def check_completion(signature_request):
    """
    Check whether all signers have completed (SIGNED or DECLINED).

    Returns True if no signers remain in PENDING or VIEWED status.
    """
    pending_count = signature_request.signers.filter(
        status__in=[SIGNER_PENDING, SIGNER_VIEWED],
    ).count()
    return pending_count == 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _mark_completed(signature_request):
    """Mark a request as completed and trigger certificate generation."""
    now = timezone.now()
    signature_request.status = REQUEST_COMPLETED
    signature_request.completed_at = now
    signature_request.save(update_fields=["status", "completed_at", "updated_at"])

    SignatureAuditEvent.objects.create(
        request=signature_request,
        event_type=EVENT_COMPLETED,
        detail={
            "completed_at": now.isoformat(),
            "signer_count": signature_request.signers.count(),
            "signed_count": signature_request.signers.filter(
                status=SIGNER_SIGNED,
            ).count(),
        },
    )

    from .tasks import generate_completion_certificate

    generate_completion_certificate.delay(signature_request.pk)

    logger.info(
        "Signature request %s completed",
        signature_request.pk,
    )
