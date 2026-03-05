"""MetadataType and DocumentMetadata models - structured metadata with validators/parsers."""

import importlib
import re
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

import jinja2

from core.models import AuditableModel, OwnedModel


class MetadataType(AuditableModel, OwnedModel):
    """
    Structured metadata type definition (Mayan EDMS pattern).

    Supports validators, parsers, lookup templates, and default templates.
    Can be assigned to specific DocumentTypes via DocumentTypeMetadata.
    """

    name = models.CharField(max_length=128, db_index=True)
    slug = models.SlugField(max_length=128, db_index=True)
    label = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="Human-readable label for display.",
    )
    default = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Jinja2 template for default value.",
    )
    lookup = models.TextField(
        blank=True,
        default="",
        help_text="Jinja2 template for populating dropdown options (one per line).",
    )
    validation = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="Dotted path to a validator function, or built-in name.",
    )
    parser = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="Dotted path to a parser function.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "metadata type"
        verbose_name_plural = "metadata types"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "owner"],
                name="unique_metadata_type_name_per_owner",
            ),
        ]

    def __str__(self):
        return self.label or self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_display_label(self):
        """Return label if set, otherwise name."""
        return self.label or self.name

    def render_default(self, context=None):
        """Render the default value template."""
        if not self.default:
            return ""
        try:
            template = jinja2.Template(self.default)
            return template.render(**(context or {}))
        except jinja2.TemplateError:
            return self.default

    def render_lookup(self, context=None):
        """Render the lookup template and return options as a list."""
        if not self.lookup:
            return []
        try:
            template = jinja2.Template(self.lookup)
            rendered = template.render(**(context or {}))
            return [line.strip() for line in rendered.splitlines() if line.strip()]
        except jinja2.TemplateError:
            return []

    def get_validator(self):
        """Load and return the validator function."""
        if not self.validation:
            return None
        # Check built-in validators first
        builtins = BUILTIN_VALIDATORS.get(self.validation)
        if builtins:
            return builtins
        # Try to load from dotted path
        return _load_callable(self.validation)

    def get_parser(self):
        """Load and return the parser function."""
        if not self.parser:
            return None
        builtins = BUILTIN_PARSERS.get(self.parser)
        if builtins:
            return builtins
        return _load_callable(self.parser)

    def validate_value(self, value):
        """Validate a value using this type's validator."""
        validator = self.get_validator()
        if validator:
            validator(value, self)

    def parse_value(self, value):
        """Parse a value using this type's parser."""
        parser = self.get_parser()
        if parser:
            return parser(value, self)
        return value


class DocumentTypeMetadata(models.Model):
    """Through model linking DocumentType to MetadataType."""

    document_type = models.ForeignKey(
        "documents.DocumentType",
        on_delete=models.CASCADE,
        related_name="metadata_assignments",
    )
    metadata_type = models.ForeignKey(
        MetadataType,
        on_delete=models.CASCADE,
        related_name="document_type_assignments",
    )
    required = models.BooleanField(
        default=False,
        help_text="Whether this metadata is required for the document type.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document_type", "metadata_type"],
                name="unique_doctype_metadata_type",
            ),
        ]

    def __str__(self):
        return f"{self.document_type} -> {self.metadata_type}"


class DocumentMetadata(AuditableModel):
    """
    Per-document metadata value instance.

    Stores a single metadata value for a document, validated against
    the MetadataType's validator on save.
    """

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="metadata_instances",
    )
    metadata_type = models.ForeignKey(
        MetadataType,
        on_delete=models.CASCADE,
        related_name="instances",
    )
    value = models.TextField(
        blank=True,
        default="",
        help_text="The metadata value (always stored as text, parsed on read).",
    )

    class Meta:
        ordering = ["metadata_type__name"]
        verbose_name = "document metadata"
        verbose_name_plural = "document metadata"
        constraints = [
            models.UniqueConstraint(
                fields=["document", "metadata_type"],
                name="unique_metadata_per_document",
            ),
        ]

    def __str__(self):
        return f"{self.metadata_type.name}: {self.value}"

    @property
    def parsed_value(self):
        """Return the value run through the metadata type's parser."""
        return self.metadata_type.parse_value(self.value)

    def clean(self):
        super().clean()
        self.metadata_type.validate_value(self.value)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Built-in validators
# ---------------------------------------------------------------------------

def _validate_regex(value, metadata_type):
    """Validate value against a regex pattern from extra config."""
    pattern = metadata_type.lookup or r".*"
    if not re.match(pattern, value):
        raise ValidationError(
            f"Value '{value}' does not match pattern '{pattern}'.",
        )


def _validate_numeric_range(value, metadata_type):
    """Validate value is a number within an optional range."""
    try:
        num = float(value)
    except (ValueError, TypeError):
        raise ValidationError(f"'{value}' is not a valid number.")
    # Range limits can be set in the default field as "min,max"
    if metadata_type.default:
        parts = metadata_type.default.split(",")
        if len(parts) == 2:
            try:
                min_val, max_val = float(parts[0]), float(parts[1])
                if num < min_val or num > max_val:
                    raise ValidationError(
                        f"Value {num} is outside range [{min_val}, {max_val}].",
                    )
            except ValueError:
                pass


def _validate_date_format(value, metadata_type):
    """Validate value matches a date format (default: YYYY-MM-DD)."""
    fmt = metadata_type.default or "%Y-%m-%d"
    try:
        datetime.strptime(value, fmt)
    except ValueError:
        raise ValidationError(
            f"'{value}' does not match date format '{fmt}'.",
        )


def _validate_required(value, metadata_type):
    """Validate that value is not empty."""
    if not value or not value.strip():
        raise ValidationError("This field is required.")


BUILTIN_VALIDATORS = {
    "regex": _validate_regex,
    "numeric_range": _validate_numeric_range,
    "date_format": _validate_date_format,
    "required": _validate_required,
}


# ---------------------------------------------------------------------------
# Built-in parsers
# ---------------------------------------------------------------------------

def _parse_integer(value, metadata_type):
    """Parse value as integer."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return value


def _parse_float(value, metadata_type):
    """Parse value as float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return value


def _parse_date(value, metadata_type):
    """Parse value as date."""
    fmt = metadata_type.default or "%Y-%m-%d"
    try:
        return datetime.strptime(value, fmt).date()
    except (ValueError, TypeError):
        return value


BUILTIN_PARSERS = {
    "integer": _parse_integer,
    "float": _parse_float,
    "date": _parse_date,
}


def _load_callable(dotted_path):
    """Load a callable from a dotted Python path."""
    try:
        module_path, func_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name)
    except (ValueError, ImportError, AttributeError):
        return None
