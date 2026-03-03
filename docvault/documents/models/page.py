"""DocumentPage model - page-level content."""

from django.db import models


class DocumentPage(models.Model):
    """
    Page-level content (from Mayan EDMS).

    Stores OCR text per page, enabling page-level search and display.
    """

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="pages",
    )
    page_number = models.PositiveIntegerField()
    content = models.TextField(blank=True, default="", help_text="OCR text for this page.")

    class Meta:
        ordering = ["page_number"]
        unique_together = [["document", "page_number"]]
        verbose_name = "document page"
        verbose_name_plural = "document pages"

    def __str__(self):
        return f"{self.document.title} - Page {self.page_number}"
