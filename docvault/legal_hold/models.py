"""Models for the legal_hold module."""

from django.conf import settings
from django.db import models

from core.models import AuditableModel

from .constants import (
    CRITERIA_TYPE_CHOICES,
    DRAFT,
    HOLD_STATUS_CHOICES,
)


class LegalHold(AuditableModel):
    """
    A legal hold preserving documents from deletion or modification.

    Holds progress through a lifecycle: DRAFT -> ACTIVE -> RELEASED.
    Criteria define which documents are captured when the hold is activated.
    """

    name = models.CharField(max_length=256)
    matter_number = models.CharField(max_length=128, blank=True, default="")
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=32,
        choices=HOLD_STATUS_CHOICES,
        default=DRAFT,
        db_index=True,
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="released_holds",
    )
    release_reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "legal hold"
        verbose_name_plural = "legal holds"

    def __str__(self):
        return f"{self.name} ({self.status})"


class LegalHoldCriteria(models.Model):
    """
    A single criterion that defines which documents a hold captures.

    Multiple criteria on the same hold are combined with AND logic.
    The value field stores type-specific parameters as JSON.
    """

    hold = models.ForeignKey(
        LegalHold,
        on_delete=models.CASCADE,
        related_name="criteria",
    )
    criteria_type = models.CharField(
        max_length=32,
        choices=CRITERIA_TYPE_CHOICES,
    )
    value = models.JSONField(default=dict)

    class Meta:
        ordering = ["pk"]
        verbose_name = "legal hold criterion"
        verbose_name_plural = "legal hold criteria"

    def __str__(self):
        return f"{self.hold.name} - {self.get_criteria_type_display()}"


class LegalHoldCustodian(models.Model):
    """
    A user designated as a custodian for a legal hold.

    Custodians are notified when a hold is activated and must acknowledge
    receipt of the hold notification.
    """

    hold = models.ForeignKey(
        LegalHold,
        on_delete=models.CASCADE,
        related_name="custodians",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="legal_hold_custodianships",
    )
    notified_at = models.DateTimeField(null=True, blank=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["hold", "user"],
                name="unique_hold_custodian",
            ),
        ]
        verbose_name = "legal hold custodian"
        verbose_name_plural = "legal hold custodians"

    def __str__(self):
        return f"{self.hold.name} - {self.user}"


class LegalHoldDocument(models.Model):
    """
    Junction record linking a document to an active legal hold.

    Created when a hold is activated and criteria are evaluated.
    The released_at timestamp is set when the hold is released.
    """

    hold = models.ForeignKey(
        LegalHold,
        on_delete=models.CASCADE,
        related_name="held_documents",
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="legal_holds",
    )
    held_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-held_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["hold", "document"],
                name="unique_hold_document",
            ),
        ]
        verbose_name = "legal hold document"
        verbose_name_plural = "legal hold documents"

    def __str__(self):
        return f"{self.hold.name} - {self.document}"
