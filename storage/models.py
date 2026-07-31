"""Models for the storage module."""

from django.conf import settings
from django.db import models


class StorageConfig(models.Model):
    """Runtime storage configuration, editable from the admin area.

    A single row (pk=1). When `enabled` is false — the default — the backend is
    resolved from environment settings instead, so a container deployment works
    with nothing in the database.

    Credentials live here in plaintext, exactly as they would in environment
    variables; database read access is equivalent to credential access either
    way. The API never returns the secret key, only whether one is set.
    """

    class Backend(models.TextChoices):
        LOCAL = "local", "Local filesystem"
        S3 = "s3", "Amazon S3"
        B2 = "b2", "Backblaze B2"
        MINIO = "minio", "MinIO"
        R2 = "r2", "Cloudflare R2"

    class AddressingStyle(models.TextChoices):
        AUTO = "auto", "Auto"
        PATH = "path", "Path-style"
        VIRTUAL = "virtual", "Virtual-hosted"

    enabled = models.BooleanField(
        default=False,
        help_text="Use this configuration instead of the environment settings.",
    )
    backend = models.CharField(
        max_length=16, choices=Backend.choices, default=Backend.LOCAL
    )

    bucket_name = models.CharField(max_length=255, blank=True, default="")
    endpoint_url = models.URLField(
        blank=True,
        default="",
        help_text="Required for B2, MinIO and R2. Leave blank for Amazon S3.",
    )
    region = models.CharField(max_length=64, blank=True, default="us-east-1")
    access_key = models.CharField(max_length=255, blank=True, default="")
    secret_key = models.CharField(max_length=512, blank=True, default="")
    prefix = models.CharField(
        max_length=255,
        blank=True,
        default="documents",
        help_text="Key prefix all objects are stored under.",
    )

    # Compatibility switches. Null means "use the provider preset".
    addressing_style = models.CharField(
        max_length=8,
        choices=AddressingStyle.choices,
        blank=True,
        default="",
        help_text="Leave blank to use the provider default.",
    )
    disable_checksums = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "Blank uses the provider default. B2, MinIO and R2 reject the "
            "checksum headers boto3 sends by default and need this on."
        ),
    )
    auto_create_bucket = models.BooleanField(
        default=False,
        help_text="Create the bucket if missing. Needs broader credentials.",
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="storage_config_updates",
    )

    class Meta:
        verbose_name = "storage configuration"
        verbose_name_plural = "storage configuration"

    def __str__(self):
        state = "enabled" if self.enabled else "disabled"
        return f"Storage configuration ({self.get_backend_display()}, {state})"

    def save(self, *args, **kwargs):
        # Singleton: there is only ever one configuration row. `objects.create()`
        # passes force_insert=True, which would raise IntegrityError on the
        # second call rather than updating the existing row — so drop it and let
        # Django decide between INSERT and UPDATE.
        self.pk = 1
        kwargs.pop("force_insert", None)
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "StorageConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def as_backend_config(self) -> dict:
        """Map onto the S3 backend's setting names."""
        return {
            "S3_PROVIDER": self.backend,
            "S3_BUCKET_NAME": self.bucket_name,
            "S3_ENDPOINT_URL": self.endpoint_url,
            "S3_REGION": self.region,
            "S3_ACCESS_KEY": self.access_key,
            "S3_SECRET_KEY": self.secret_key,
            "S3_PREFIX": self.prefix,
            "S3_ADDRESSING_STYLE": self.addressing_style or None,
            "S3_DISABLE_CHECKSUMS": self.disable_checksums,
            "S3_AUTO_CREATE_BUCKET": self.auto_create_bucket,
        }


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
