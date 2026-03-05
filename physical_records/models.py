"""Models for the physical_records module."""

from django.conf import settings
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

from core.models import AuditableModel

from .constants import (
    CHARGEOUT_STATUS_CHOICES,
    CHECKED_OUT,
    CONDITION_CHOICES,
    DESTRUCTION_METHOD_CHOICES,
    GOOD,
    LOCATION_TYPE_CHOICES,
)


class PhysicalLocation(MPTTModel):
    """
    Hierarchical physical storage location.

    Supports nested locations: Building > Room > Cabinet > Shelf > Box.
    """

    name = models.CharField(max_length=256)
    location_type = models.CharField(
        max_length=32,
        choices=LOCATION_TYPE_CHOICES,
    )
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    barcode = models.CharField(max_length=128, unique=True, null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    current_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        ordering = ["tree_id", "lft"]
        verbose_name = "physical location"
        verbose_name_plural = "physical locations"

    def __str__(self):
        return f"{self.get_location_type_display()}: {self.name}"


class PhysicalRecord(AuditableModel):
    """
    Links a digital document to a physical record with location and condition tracking.
    """

    document = models.OneToOneField(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="physical_record",
    )
    location = models.ForeignKey(
        PhysicalLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="records",
    )
    position = models.CharField(max_length=128, blank=True, default="")
    barcode = models.CharField(max_length=128, unique=True, null=True, blank=True)
    condition = models.CharField(
        max_length=32,
        choices=CONDITION_CHOICES,
        default=GOOD,
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "physical record"
        verbose_name_plural = "physical records"

    def __str__(self):
        return f"Physical Record #{self.pk} - {self.document.title}"


class ChargeOut(models.Model):
    """
    Tracks the check-out and return of physical records.
    """

    physical_record = models.ForeignKey(
        PhysicalRecord,
        on_delete=models.CASCADE,
        related_name="charge_outs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="charge_outs",
    )
    checked_out_at = models.DateTimeField(auto_now_add=True)
    expected_return = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=32,
        choices=CHARGEOUT_STATUS_CHOICES,
        default=CHECKED_OUT,
    )

    class Meta:
        ordering = ["-checked_out_at"]
        verbose_name = "charge out"
        verbose_name_plural = "charge outs"

    def __str__(self):
        return f"ChargeOut #{self.pk} - {self.physical_record}"


class DestructionCertificate(models.Model):
    """
    Certificate documenting the destruction of a physical record.
    """

    physical_record = models.ForeignKey(
        PhysicalRecord,
        on_delete=models.CASCADE,
        related_name="destruction_certificates",
    )
    destroyed_at = models.DateTimeField()
    destroyed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="destruction_certificates",
    )
    method = models.CharField(
        max_length=32,
        choices=DESTRUCTION_METHOD_CHOICES,
    )
    witness = models.CharField(max_length=256, blank=True, default="")
    certificate_pdf = models.FileField(
        upload_to="physical_records/certificates/",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-destroyed_at"]
        verbose_name = "destruction certificate"
        verbose_name_plural = "destruction certificates"

    def __str__(self):
        return f"Destruction Certificate #{self.pk} - {self.physical_record}"
