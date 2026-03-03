"""Abstract base class for storage backends."""

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageBackend(ABC):
    """Abstract storage backend interface for DocVault."""

    @abstractmethod
    def save(self, name: str, content: BinaryIO) -> str:
        """Save file and return the storage path."""

    @abstractmethod
    def open(self, name: str) -> BinaryIO:
        """Open file for reading."""

    @abstractmethod
    def delete(self, name: str) -> None:
        """Delete a file."""

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Check if a file exists."""

    @abstractmethod
    def url(self, name: str) -> str:
        """Get URL for file access."""

    @abstractmethod
    def size(self, name: str) -> int:
        """Get file size in bytes."""

    @abstractmethod
    def list_files(self, prefix: str = "") -> list[str]:
        """List files under a given prefix."""
