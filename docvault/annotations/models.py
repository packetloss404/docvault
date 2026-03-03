"""Models for the annotations module."""

from django.conf import settings
from django.db import models

from core.models import AuditableModel

from .constants import ANNOTATION_TYPE_CHOICES


class Annotation(AuditableModel):
    """
    A visual annotation placed on a specific page of a document.

    Coordinates are stored as normalised floats (0.0-1.0) relative to
    page dimensions so they remain valid regardless of rendering size.
    """

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="annotations",
    )
    page = models.PositiveIntegerField()
    annotation_type = models.CharField(
        max_length=32,
        choices=ANNOTATION_TYPE_CHOICES,
    )
    coordinates = models.JSONField(
        default=dict,
        help_text="Normalised coordinate data (all values 0.0-1.0).",
    )
    content = models.TextField(
        blank=True,
        default="",
        help_text="Text content for sticky notes, text boxes, or stamp labels.",
    )
    color = models.CharField(
        max_length=7,
        default="#FFFF00",
        help_text="Hex colour code, e.g. #FFFF00.",
    )
    opacity = models.FloatField(
        default=0.3,
        help_text="Opacity value between 0.0 and 1.0.",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="annotations",
    )
    is_private = models.BooleanField(
        default=False,
        help_text="Private annotations are visible only to the author and staff.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "annotation"
        verbose_name_plural = "annotations"

    def __str__(self):
        return f"{self.annotation_type} on page {self.page} of doc {self.document_id}"


class AnnotationReply(models.Model):
    """A threaded reply on an annotation."""

    annotation = models.ForeignKey(
        Annotation,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="annotation_replies",
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "annotation reply"
        verbose_name_plural = "annotation replies"

    def __str__(self):
        return f"Reply by {self.author_id} on annotation {self.annotation_id}"
