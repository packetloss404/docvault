"""Storage backends for DocVault."""

from .base import StorageBackend
from .content_addressed import ContentAddressedStorageBackend
from .local import LocalStorageBackend

__all__ = [
    "StorageBackend",
    "ContentAddressedStorageBackend",
    "LocalStorageBackend",
]
