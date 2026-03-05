"""Document signature model for GPG/PGP signing."""

from django.conf import settings
from django.db import models

from core.models import AuditableModel


class Signature(AuditableModel):
    """Records a GPG/PGP signature for a document."""

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="signatures",
    )
    signer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="document_signatures",
    )
    signature_data = models.TextField(help_text="ASCII-armored GPG signature.")
    key_id = models.CharField(max_length=64, help_text="GPG key ID used for signing.")
    algorithm = models.CharField(max_length=32, default="RSA")
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "signature"
        verbose_name_plural = "signatures"

    def __str__(self):
        return f"Signature on doc {self.document_id} by key {self.key_id}"
