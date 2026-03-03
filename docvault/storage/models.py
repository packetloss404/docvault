"""Models for the storage module."""

from django.db import models


class ContentBlob(models.Model):
    """
    Content-addressable blob representing a unique file by its SHA-256 hash.

    Multiple documents may reference the same blob, enabling deduplication.
    """

    sha256_hash = models.CharField(max_length=64, primary_key=True)
    size = models.BigIntegerField(help_text="File size in bytes.")
    reference_count = models.IntegerField(default=1)
    storage_backend = models.CharField(max_length=32, default="local")
    storage_path = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "content blob"
        verbose_name_plural = "content blobs"

    def __str__(self):
        return f"Blob {self.sha256_hash[:12]}... ({self.size} bytes, {self.reference_count} refs)"
