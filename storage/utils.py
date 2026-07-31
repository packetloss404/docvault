"""Storage utility functions."""

import logging

from django.conf import settings

from .backends.base import StorageBackend
from .backends.local import LocalStorageBackend

logger = logging.getLogger(__name__)

# Backend names served by the S3-compatible client.
S3_COMPATIBLE = {"s3", "b2", "minio", "r2"}


def _resolve_config() -> tuple[str, dict | None]:
    """Return the backend name and, if DB-configured, its settings override.

    The database configuration wins only when a row exists and is enabled, so a
    fresh container deployment runs purely on environment variables.
    """
    try:
        from .models import StorageConfig

        config = StorageConfig.objects.filter(pk=1, enabled=True).first()
    except Exception:  # noqa: BLE001 - the table may not exist yet during migrate
        config = None

    if config:
        return config.backend, config.as_backend_config()

    return getattr(settings, "STORAGE_BACKEND", "local"), None


def get_storage_backend() -> StorageBackend:
    """Return the configured storage backend instance."""
    backend_type, config = _resolve_config()

    if backend_type in S3_COMPATIBLE:
        from .backends.s3 import S3StorageBackend

        overrides = dict(config or {})
        # The provider drives the compatibility preset (checksums, addressing).
        overrides.setdefault("S3_PROVIDER", backend_type)
        backend = S3StorageBackend(config=overrides)
    else:
        backend = LocalStorageBackend()

    # Wrap with encryption if enabled
    if getattr(settings, "STORAGE_ENCRYPTION_ENABLED", False):
        from .backends.encrypted import EncryptedStorageBackend

        return EncryptedStorageBackend(delegate=backend)

    return backend
