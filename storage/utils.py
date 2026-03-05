"""Storage utility functions."""

from django.conf import settings

from .backends.base import StorageBackend
from .backends.local import LocalStorageBackend


def get_storage_backend() -> StorageBackend:
    """Return the configured storage backend instance."""
    backend_type = getattr(settings, "STORAGE_BACKEND", "local")

    if backend_type == "s3":
        from .backends.s3 import S3StorageBackend
        backend = S3StorageBackend()
    else:
        backend = LocalStorageBackend()

    # Wrap with encryption if enabled
    if getattr(settings, "STORAGE_ENCRYPTION_ENABLED", False):
        from .backends.encrypted import EncryptedStorageBackend
        return EncryptedStorageBackend(delegate=backend)

    return backend
