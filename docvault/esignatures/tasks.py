"""Celery tasks for the e-signatures app."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def send_signature_email(signer_id):
    """Send signing invitation email to a signer with their unique token link."""
    from django.conf import settings
    from django.core.mail import send_mail

    from .models import Signer

    signer = Signer.objects.select_related("request", "request__document").get(
        pk=signer_id,
    )
    sig_request = signer.request

    subject = f"Signature Requested: {sig_request.title}"
    body = (
        f"Hello {signer.name},\n\n"
        f"You have been asked to sign the document: "
        f"{sig_request.document.title}\n\n"
    )
    if sig_request.message:
        body += f"{sig_request.message}\n\n"
    if sig_request.expiration:
        body += (
            f"Please complete your signature before: "
            f"{sig_request.expiration.strftime('%Y-%m-%d %H:%M %Z')}\n\n"
        )

    signing_base_url = getattr(
        settings, "ESIGNATURE_SIGNING_BASE_URL", "/api/v1/sign",
    )
    body += (
        f"Please use the following link to review and sign:\n"
        f"{signing_base_url}/{signer.token}/\n\n"
        f"Thank you."
    )

    from_email = getattr(
        settings, "ESIGNATURE_FROM_EMAIL", "noreply@docvault.local",
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=from_email,
        recipient_list=[signer.email],
        fail_silently=False,
    )

    logger.info(
        "Sent signing invitation: signer_id=%s, to=%s, request=%s",
        signer_id,
        signer.email,
        sig_request.pk,
    )
    return {"signer_id": signer_id, "sent_to": signer.email}


@shared_task
def send_signature_reminder(request_id):
    """Send reminder emails to all pending signers on a request."""
    from django.conf import settings
    from django.core.mail import send_mail

    from .constants import EVENT_REMINDER_SENT, SIGNER_PENDING, SIGNER_VIEWED
    from .models import SignatureAuditEvent, SignatureRequest

    sig_request = SignatureRequest.objects.select_related("document").get(
        pk=request_id,
    )
    pending_signers = sig_request.signers.filter(
        status__in=[SIGNER_PENDING, SIGNER_VIEWED],
    )

    signing_base_url = getattr(
        settings, "ESIGNATURE_SIGNING_BASE_URL", "/api/v1/sign",
    )
    from_email = getattr(
        settings, "ESIGNATURE_FROM_EMAIL", "noreply@docvault.local",
    )

    reminded = []
    for signer in pending_signers:
        subject = f"Reminder: Signature Requested - {sig_request.title}"
        body = (
            f"Hello {signer.name},\n\n"
            f"This is a reminder that you have a pending signature request "
            f"for the document: {sig_request.document.title}\n\n"
        )
        if sig_request.expiration:
            body += (
                f"Deadline: "
                f"{sig_request.expiration.strftime('%Y-%m-%d %H:%M %Z')}\n\n"
            )

        body += (
            f"Please use the following link to review and sign:\n"
            f"{signing_base_url}/{signer.token}/\n\n"
            f"Thank you."
        )

        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[signer.email],
            fail_silently=False,
        )
        reminded.append(signer.email)

    # Create audit event for the reminder
    SignatureAuditEvent.objects.create(
        request=sig_request,
        event_type=EVENT_REMINDER_SENT,
        detail={"reminded_signers": reminded},
    )

    logger.info(
        "Sent reminders for request %s to %d signers: %s",
        request_id,
        len(reminded),
        ", ".join(reminded),
    )
    return {"request_id": request_id, "reminded": reminded}


@shared_task
def expire_signature_requests():
    """Auto-expire signature requests that have passed their expiration date."""
    from django.utils import timezone

    from .constants import (
        EVENT_EXPIRED,
        REQUEST_DRAFT,
        REQUEST_EXPIRED,
        REQUEST_IN_PROGRESS,
        REQUEST_SENT,
    )
    from .models import SignatureAuditEvent, SignatureRequest

    now = timezone.now()
    expired_qs = SignatureRequest.objects.filter(
        expiration__lt=now,
        status__in=[REQUEST_DRAFT, REQUEST_SENT, REQUEST_IN_PROGRESS],
    )

    count = 0
    for sig_request in expired_qs:
        sig_request.status = REQUEST_EXPIRED
        sig_request.save(update_fields=["status", "updated_at"])

        SignatureAuditEvent.objects.create(
            request=sig_request,
            event_type=EVENT_EXPIRED,
            detail={"expiration": sig_request.expiration.isoformat()},
        )
        count += 1

    logger.info("Expired %d signature requests.", count)
    return {"expired": count}


@shared_task
def generate_completion_certificate(request_id):
    """
    Generate a certificate of completion PDF for a signed request.

    Creates a simple PDF with:
    - Title: "Certificate of Completion"
    - Document name, request title
    - Signer details (name, email, signed_at, IP)
    - Audit trail summary
    - SHA-256 hash of the original document
    """
    import io
    import os

    from django.core.files.base import ContentFile
    from django.utils import timezone

    from .constants import SIGNER_SIGNED
    from .models import SignatureRequest

    sig_request = SignatureRequest.objects.select_related("document").get(
        pk=request_id,
    )

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        logger.warning(
            "reportlab is not installed. Cannot generate certificate for "
            "request %s. Install with: pip install reportlab",
            request_id,
        )
        return {"request_id": request_id, "error": "reportlab not installed"}

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CertTitle",
        parent=styles["Title"],
        fontSize=24,
        spaceAfter=30,
    )
    heading_style = ParagraphStyle(
        "CertHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20,
    )
    body_style = styles["Normal"]

    story = []

    # Title
    story.append(Paragraph("Certificate of Completion", title_style))
    story.append(Spacer(1, 12))

    # Document info
    story.append(Paragraph("Document Information", heading_style))
    story.append(Paragraph(
        f"<b>Request Title:</b> {sig_request.title}", body_style,
    ))
    story.append(Paragraph(
        f"<b>Document:</b> {sig_request.document.title}", body_style,
    ))
    story.append(Paragraph(
        f"<b>Document ID:</b> {sig_request.document.pk}", body_style,
    ))
    story.append(Paragraph(
        f"<b>Completed At:</b> "
        f"{sig_request.completed_at.strftime('%Y-%m-%d %H:%M:%S %Z') if sig_request.completed_at else 'N/A'}",
        body_style,
    ))

    # Document hash
    checksum = sig_request.document.checksum
    if checksum:
        story.append(Paragraph(
            f"<b>Document SHA-256:</b> {checksum}", body_style,
        ))
    story.append(Spacer(1, 12))

    # Signer details table
    story.append(Paragraph("Signer Details", heading_style))
    signers = sig_request.signers.all()

    table_data = [["Name", "Email", "Status", "Signed At", "IP Address"]]
    for signer in signers:
        signed_at_str = (
            signer.signed_at.strftime("%Y-%m-%d %H:%M:%S %Z")
            if signer.signed_at else "N/A"
        )
        table_data.append([
            signer.name,
            signer.email,
            signer.status.upper(),
            signed_at_str,
            signer.ip_address or "N/A",
        ])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    story.append(table)
    story.append(Spacer(1, 12))

    # Audit trail
    story.append(Paragraph("Audit Trail", heading_style))
    events = sig_request.audit_events.select_related("signer").all()

    audit_data = [["Timestamp", "Event", "Signer", "IP Address"]]
    for event in events:
        ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
        signer_info = (
            f"{event.signer.name} ({event.signer.email})"
            if event.signer else "System"
        )
        audit_data.append([
            ts,
            event.event_type.replace("_", " ").title(),
            signer_info,
            event.ip_address or "N/A",
        ])

    audit_table = Table(audit_data, repeatRows=1)
    audit_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    story.append(audit_table)
    story.append(Spacer(1, 20))

    # Footer
    story.append(Paragraph(
        f"<i>This certificate was automatically generated by DocVault on "
        f"{timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')}.</i>",
        body_style,
    ))

    doc.build(story)

    # Save to model
    pdf_content = buffer.getvalue()
    buffer.close()

    filename = f"certificate_{sig_request.pk}.pdf"
    sig_request.certificate_pdf.save(filename, ContentFile(pdf_content), save=True)

    logger.info(
        "Generated completion certificate for request %s (%d bytes)",
        request_id,
        len(pdf_content),
    )
    return {
        "request_id": request_id,
        "certificate_size": len(pdf_content),
        "filename": filename,
    }
