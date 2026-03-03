"""CustomField and CustomFieldInstance models for extensible metadata."""

import json

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from core.models import AuditableModel, OwnedModel


# Custom field data types
FIELD_STRING = "string"
FIELD_LONGTEXT = "longtext"
FIELD_URL = "url"
FIELD_DATE = "date"
FIELD_DATETIME = "datetime"
FIELD_BOOLEAN = "boolean"
FIELD_INTEGER = "integer"
FIELD_FLOAT = "float"
FIELD_MONETARY = "monetary"
FIELD_DOCUMENTLINK = "documentlink"
FIELD_SELECT = "select"
FIELD_MULTISELECT = "multiselect"

FIELD_TYPE_CHOICES = [
    (FIELD_STRING, "String"),
    (FIELD_LONGTEXT, "Long Text"),
    (FIELD_URL, "URL"),
    (FIELD_DATE, "Date"),
    (FIELD_DATETIME, "Date & Time"),
    (FIELD_BOOLEAN, "Boolean"),
    (FIELD_INTEGER, "Integer"),
    (FIELD_FLOAT, "Float"),
    (FIELD_MONETARY, "Monetary"),
    (FIELD_DOCUMENTLINK, "Document Link"),
    (FIELD_SELECT, "Select"),
    (FIELD_MULTISELECT, "Multi-Select"),
]

# Map field types to the value column used for storage
FIELD_TYPE_COLUMN_MAP = {
    FIELD_STRING: "value_text",
    FIELD_LONGTEXT: "value_text",
    FIELD_URL: "value_url",
    FIELD_DATE: "value_date",
    FIELD_DATETIME: "value_datetime",
    FIELD_BOOLEAN: "value_bool",
    FIELD_INTEGER: "value_int",
    FIELD_FLOAT: "value_float",
    FIELD_MONETARY: "value_monetary",
    FIELD_DOCUMENTLINK: "value_document_ids",
    FIELD_SELECT: "value_select",
    FIELD_MULTISELECT: "value_select",
}


class CustomField(AuditableModel, OwnedModel):
    """
    Definition of a custom metadata field.

    Supports 12 data types with type-specific configuration via extra_data.
    Can be assigned to specific DocumentTypes via DocumentTypeCustomField.
    """

    name = models.CharField(max_length=128, db_index=True)
    slug = models.SlugField(max_length=128, db_index=True)
    data_type = models.CharField(
        max_length=16,
        choices=FIELD_TYPE_CHOICES,
        help_text="The data type for this field.",
    )
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Type-specific configuration. For SELECT/MULTISELECT: "
            '{"options": ["opt1", "opt2"]}. For STRING: {"max_length": 256}.'
        ),
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "custom field"
        verbose_name_plural = "custom fields"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "owner"],
                name="unique_custom_field_name_per_owner",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def value_column(self):
        """Return the column name used to store values for this field type."""
        return FIELD_TYPE_COLUMN_MAP.get(self.data_type, "value_text")

    def get_select_options(self):
        """Return select options from extra_data, or empty list."""
        if self.data_type in (FIELD_SELECT, FIELD_MULTISELECT):
            return self.extra_data.get("options", [])
        return []


class DocumentTypeCustomField(models.Model):
    """Through model linking DocumentType to CustomField."""

    document_type = models.ForeignKey(
        "documents.DocumentType",
        on_delete=models.CASCADE,
        related_name="custom_field_assignments",
    )
    custom_field = models.ForeignKey(
        CustomField,
        on_delete=models.CASCADE,
        related_name="document_type_assignments",
    )
    required = models.BooleanField(
        default=False,
        help_text="Whether this field is required for the document type.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document_type", "custom_field"],
                name="unique_doctype_custom_field",
            ),
        ]

    def __str__(self):
        return f"{self.document_type} -> {self.custom_field}"


class CustomFieldInstance(AuditableModel):
    """
    Per-document custom field value.

    Uses multi-column storage: the correct column is selected based on
    the field's data_type. The `value` property provides unified access.
    """

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="custom_field_instances",
    )
    field = models.ForeignKey(
        CustomField,
        on_delete=models.CASCADE,
        related_name="instances",
    )

    # Multi-column value storage
    value_text = models.TextField(blank=True, null=True)
    value_bool = models.BooleanField(null=True, blank=True)
    value_url = models.URLField(max_length=2048, blank=True, null=True)
    value_date = models.DateField(null=True, blank=True)
    value_datetime = models.DateTimeField(null=True, blank=True)
    value_int = models.IntegerField(null=True, blank=True)
    value_float = models.FloatField(null=True, blank=True)
    value_monetary = models.DecimalField(
        max_digits=19, decimal_places=4, null=True, blank=True,
    )
    value_document_ids = models.JSONField(
        default=list, blank=True,
        help_text="List of document IDs for DOCUMENTLINK type.",
    )
    value_select = models.JSONField(
        default=list, blank=True,
        help_text="Selected value(s) for SELECT/MULTISELECT.",
    )

    class Meta:
        ordering = ["field__name"]
        verbose_name = "custom field instance"
        verbose_name_plural = "custom field instances"
        constraints = [
            models.UniqueConstraint(
                fields=["document", "field"],
                name="unique_custom_field_per_document",
            ),
        ]

    def __str__(self):
        return f"{self.field.name}: {self.value}"

    @property
    def value(self):
        """Return the value from the correct column based on field type."""
        column = self.field.value_column
        return getattr(self, column)

    @value.setter
    def value(self, val):
        """Set the value on the correct column based on field type."""
        column = self.field.value_column
        setattr(self, column, val)

    def clean(self):
        """Validate the value based on field type."""
        super().clean()
        data_type = self.field.data_type
        val = self.value

        if val is None:
            return

        if data_type == FIELD_STRING:
            max_len = self.field.extra_data.get("max_length", 256)
            if isinstance(val, str) and len(val) > max_len:
                raise ValidationError(
                    f"String value exceeds maximum length of {max_len}.",
                )

        elif data_type == FIELD_URL:
            if isinstance(val, str) and not (
                val.startswith("http://") or val.startswith("https://")
            ):
                raise ValidationError("URL must start with http:// or https://.")

        elif data_type == FIELD_SELECT:
            options = self.field.get_select_options()
            if options and val not in [None, []] and val not in options:
                # value_select stores as JSON; for SELECT it's a single string
                if isinstance(val, list):
                    val_check = val[0] if val else None
                else:
                    val_check = val
                if val_check and val_check not in options:
                    raise ValidationError(
                        f"'{val_check}' is not a valid option. "
                        f"Choose from: {options}",
                    )

        elif data_type == FIELD_MULTISELECT:
            options = self.field.get_select_options()
            if options and val:
                vals = val if isinstance(val, list) else [val]
                invalid = [v for v in vals if v not in options]
                if invalid:
                    raise ValidationError(
                        f"Invalid options: {invalid}. Choose from: {options}",
                    )

        elif data_type == FIELD_DOCUMENTLINK:
            if val and not isinstance(val, list):
                raise ValidationError("Document link value must be a list of IDs.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
