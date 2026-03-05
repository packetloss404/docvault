"""Zone OCR models for template-based field extraction."""

from django.conf import settings
from django.db import models

from core.models import AuditableModel

from .constants import FIELD_TYPE_CHOICES, PREPROCESSING_CHOICES, PREPROCESS_NONE


class ZoneOCRTemplate(AuditableModel):
    """
    A template that defines zones (regions) on a document page
    for targeted OCR extraction.

    Each template targets a specific page and contains multiple
    ZoneOCRField definitions that map bounding boxes to field types.
    """

    name = models.CharField(max_length=256, db_index=True)
    description = models.TextField(blank=True, default="")
    sample_page_image = models.ImageField(
        upload_to="zone_ocr/samples/",
        blank=True,
        null=True,
        help_text="Sample page image used to define zones visually.",
    )
    page_number = models.PositiveIntegerField(
        default=1,
        help_text="The page number this template applies to (1-indexed).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is used during document processing.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "zone OCR template"
        verbose_name_plural = "zone OCR templates"

    def __str__(self):
        return self.name


class ZoneOCRField(models.Model):
    """
    A single field zone within a ZoneOCRTemplate.

    Defines the bounding box (as percentages), the expected data type,
    optional preprocessing, and an optional mapping to a CustomField
    for automatic metadata population.
    """

    template = models.ForeignKey(
        ZoneOCRTemplate,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    name = models.CharField(max_length=128)
    field_type = models.CharField(
        max_length=16,
        choices=FIELD_TYPE_CHOICES,
        help_text="Expected data type for the extracted value.",
    )
    bounding_box = models.JSONField(
        default=dict,
        help_text="Bounding box as percentages: {x, y, width, height}.",
    )
    custom_field = models.ForeignKey(
        "organization.CustomField",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="zone_ocr_fields",
        help_text="If set, extracted value is written to this custom field.",
    )
    order = models.PositiveIntegerField(default=0)
    preprocessing = models.CharField(
        max_length=32,
        choices=PREPROCESSING_CHOICES,
        default=PREPROCESS_NONE,
        help_text="Preprocessing to apply to the raw OCR text.",
    )
    validation_regex = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Optional regex to validate extracted values.",
    )

    class Meta:
        ordering = ["order"]
        verbose_name = "zone OCR field"
        verbose_name_plural = "zone OCR fields"
        constraints = [
            models.UniqueConstraint(
                fields=["template", "name"],
                name="unique_zone_field_name_per_template",
            ),
        ]

    def __str__(self):
        return f"{self.template.name} - {self.name}"


class ZoneOCRResult(models.Model):
    """
    Stores the result of zone OCR extraction for a single field
    on a single document.

    Supports a review workflow: results can be flagged as reviewed
    and corrections can be provided by a user.
    """

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="zone_ocr_results",
    )
    template = models.ForeignKey(
        ZoneOCRTemplate,
        on_delete=models.CASCADE,
        related_name="results",
    )
    field = models.ForeignKey(
        ZoneOCRField,
        on_delete=models.CASCADE,
        related_name="results",
    )
    extracted_value = models.TextField(
        default="",
        help_text="The raw value extracted by OCR.",
    )
    confidence = models.FloatField(
        default=0.0,
        help_text="OCR confidence score (0.0 to 1.0).",
    )
    reviewed = models.BooleanField(
        default=False,
        help_text="Whether a human has reviewed this result.",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="zone_ocr_reviews",
    )
    corrected_value = models.TextField(
        blank=True,
        default="",
        help_text="User-corrected value, if different from extracted_value.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "zone OCR result"
        verbose_name_plural = "zone OCR results"
        constraints = [
            models.UniqueConstraint(
                fields=["document", "template", "field"],
                name="unique_zone_result_per_document_field",
            ),
        ]

    def __str__(self):
        return f"{self.document} - {self.field.name}: {self.extracted_value}"

    @property
    def effective_value(self):
        """Return the corrected value if available, otherwise the extracted value."""
        if self.corrected_value:
            return self.corrected_value
        return self.extracted_value
