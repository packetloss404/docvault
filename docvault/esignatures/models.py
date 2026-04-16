"""Models for the e-signatures app."""

import uuid

from django.db import models

from core.models import AuditableModel

from .constants import (
    AUDIT_EVENT_TYPE_CHOICES,
    FIELD_TYPE_CHOICES,
    ORDER_SEQUENTIAL,
    REQUEST_DRAFT,
    REQUEST_STATUS_CHOICES,
    SIGNER_PENDING,
    SIGNER_STATUS_CHOICES,
    SIGNING_ORDER_CHOICES,
    VERIFICATION_METHOD_CHOICES,
    VERIFY_EMAIL,
)


class SignatureRequest(AuditableModel):
    """
    A request for one or more signers to sign a document.

    Tracks overall status, signing order, expiration, and the
    generated certificate of completion.
    """

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="signature_requests",
    )
    title = models.CharField(max_length=256)
    message = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=32,
        choices=REQUEST_STATUS_CHOICES,
        default=REQUEST_DRAFT,
    )
    signing_order = models.CharField(
        max_length=16,
        choices=SIGNING_ORDER_CHOICES,
        default=ORDER_SEQUENTIAL,
    )
    expiration = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    certificate_pdf = models.FileField(
        upload_to="esignatures/certificates/",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "signature request"
        verbose_name_plural = "signature requests"

    def __str__(self):
        return f"{self.title} ({self.status})"


class Signer(models.Model):
    """
    An individual signer on a signature request.

    Each signer receives a unique token for accessing the signing page.
    """

    request = models.ForeignKey(
        SignatureRequest,
        on_delete=models.CASCADE,
        related_name="signers",
    )
    name = models.CharField(max_length=256)
    email = models.EmailField()
    role = models.CharField(max_length=128, blank=True, default="")
    order = models.PositiveIntegerField(default=0)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(
        max_length=32,
        choices=SIGNER_STATUS_CHOICES,
        default=SIGNER_PENDING,
    )
    signed_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    verification_method = models.CharField(
        max_length=16,
        choices=VERIFICATION_METHOD_CHOICES,
        default=VERIFY_EMAIL,
    )
    verification_code = models.CharField(max_length=6, blank=True, default="")
    verified = models.BooleanField(
        default=False,
        help_text="True once the signer has verified their identity via the verification code.",
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Phone number for future SMS verification. Currently unused.",
    )
    viewed_pages = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["order", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["request", "email"],
                name="unique_signer_per_request",
            ),
        ]
        verbose_name = "signer"
        verbose_name_plural = "signers"

    def __str__(self):
        return f"{self.name} <{self.email}> ({self.status})"


class SignatureField(models.Model):
    """
    A field placed on a document page that a signer must complete.

    Coordinates are normalized to 0.0-1.0 relative to page dimensions.
    """

    request = models.ForeignKey(
        SignatureRequest,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    signer = models.ForeignKey(
        Signer,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    page = models.PositiveIntegerField()
    x = models.FloatField(help_text="X coordinate (0.0-1.0)")
    y = models.FloatField(help_text="Y coordinate (0.0-1.0)")
    width = models.FloatField(help_text="Width (0.0-1.0)")
    height = models.FloatField(help_text="Height (0.0-1.0)")
    field_type = models.CharField(
        max_length=16,
        choices=FIELD_TYPE_CHOICES,
    )
    required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    value = models.TextField(blank=True, default="")
    signed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "signature field"
        verbose_name_plural = "signature fields"

    def __str__(self):
        return f"Field {self.field_type} on page {self.page} for {self.signer.name}"


class SignatureAuditEvent(models.Model):
    """
    Audit trail entry for a signature request.

    Captures every significant action (sent, viewed, signed, etc.)
    with timestamp, IP address, and optional detail payload.
    """

    request = models.ForeignKey(
        SignatureRequest,
        on_delete=models.CASCADE,
        related_name="audit_events",
    )
    signer = models.ForeignKey(
        Signer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    event_type = models.CharField(
        max_length=32,
        choices=AUDIT_EVENT_TYPE_CHOICES,
    )
    detail = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "signature audit event"
        verbose_name_plural = "signature audit events"

    def __str__(self):
        return f"{self.event_type} at {self.timestamp}"
