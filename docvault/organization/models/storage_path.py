"""StoragePath model - Jinja2-based path templates for file organization."""

from django.core.exceptions import ValidationError
from django.db import models

from .base import MatchingModel


def validate_path_template(value):
    """Validate that the path template is valid Jinja2."""
    import jinja2

    try:
        jinja2.Template(value)
    except jinja2.TemplateSyntaxError as e:
        raise ValidationError(f"Invalid Jinja2 template: {e}")


class StoragePath(MatchingModel):
    """
    Storage path template for organizing files on disk.

    Uses Jinja2 templates with document variables:
    {{ created_year }}, {{ correspondent }}, {{ title }},
    {{ document_type }}, {{ added_year }}, {{ added_month }}, etc.
    """

    path = models.CharField(
        max_length=1024,
        validators=[validate_path_template],
        help_text=(
            "Jinja2 template for file path. "
            "Available variables: created_year, created_month, "
            "correspondent, title, document_type, added_year, added_month, "
            "original_filename, asn."
        ),
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "storage path"
        verbose_name_plural = "storage paths"
        constraints = [
            models.UniqueConstraint(fields=["name"], name="unique_storage_path_name"),
        ]

    def render(self, document) -> str:
        """Render the path template for a given document."""
        import jinja2

        template = jinja2.Template(self.path)
        context = {
            "created_year": str(document.created.year) if document.created else "",
            "created_month": f"{document.created.month:02d}" if document.created else "",
            "added_year": str(document.added.year) if document.added else "",
            "added_month": f"{document.added.month:02d}" if document.added else "",
            "title": document.title or "",
            "original_filename": document.original_filename or "",
            "asn": str(document.archive_serial_number or ""),
            "correspondent": (
                document.correspondent.name if hasattr(document, "correspondent") and document.correspondent else ""
            ),
            "document_type": (
                document.document_type.name if document.document_type else ""
            ),
        }
        return template.render(**context).strip("/")
