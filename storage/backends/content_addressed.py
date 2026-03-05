"""Content-addressable storage backend with deduplication."""

import hashlib
import logging
from typing import BinaryIO

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from .base import StorageBackend

logger = logging.getLogger(__name__)


class ContentAddressedStorageBackend(StorageBackend):
    """
    Content-addressable storage that wraps an underlying backend.

    Files are stored at hash-based paths (ab/cd/full_hash) for deduplication.
    When the same content is saved multiple times, only one copy is stored
    and a reference count is incremented.
    """

    def __init__(self, underlying_backend: StorageBackend):
        self.underlying = underlying_backend

    @staticmethod
    def _compute_hash(content: BinaryIO) -> tuple[str, int]:
        """
        Compute SHA-256 hash and size of file content.

        Resets the stream position to the beginning after reading.

        Returns:
            tuple of (hex_digest, size_in_bytes)
        """
        sha256 = hashlib.sha256()
        size = 0
        for chunk in iter(lambda: content.read(65536), b""):
            sha256.update(chunk)
            size += len(chunk)
        content.seek(0)
        return sha256.hexdigest(), size

    @staticmethod
    def _hash_to_path(sha256_hash: str) -> str:
        """
        Convert a SHA-256 hash to a sharded storage path.

        Example: "abcdef1234..." -> "ab/cd/abcdef1234..."
        """
        return f"{sha256_hash[:2]}/{sha256_hash[2:4]}/{sha256_hash}"

    def save(self, name: str, content: BinaryIO) -> str:
        """
        Save file content, deduplicating by SHA-256 hash.

        If a blob with the same hash already exists, increment the reference
        count and return the hash without storing a new copy.

        Args:
            name: Original filename (used for logging, not storage path).
            content: File-like object to store.

        Returns:
            The SHA-256 hash of the stored content.
        """
        from storage.models import ContentBlob

        sha256_hash, size = self._compute_hash(content)

        try:
            blob = ContentBlob.objects.get(pk=sha256_hash)
            blob.reference_count += 1
            blob.save(update_fields=["reference_count"])
            logger.info(
                "Deduplicated file %s (hash=%s, refs=%d)",
                name,
                sha256_hash[:12],
                blob.reference_count,
            )
            return sha256_hash
        except ContentBlob.DoesNotExist:
            pass

        # Store the file at a hash-based path
        storage_path = self._hash_to_path(sha256_hash)
        self.underlying.save(storage_path, content)

        ContentBlob.objects.create(
            sha256_hash=sha256_hash,
            size=size,
            reference_count=1,
            storage_backend=self._get_backend_name(),
            storage_path=storage_path,
        )

        logger.info(
            "Stored new blob for %s (hash=%s, size=%d)",
            name,
            sha256_hash[:12],
            size,
        )
        return sha256_hash

    def open(self, name: str) -> BinaryIO:
        """
        Open a file by its SHA-256 hash.

        Updates the last_accessed timestamp on the blob.

        Args:
            name: SHA-256 hash of the content.

        Returns:
            File-like object for reading.

        Raises:
            FileNotFoundError: If no blob with the given hash exists.
        """
        from storage.models import ContentBlob

        try:
            blob = ContentBlob.objects.get(pk=name)
        except ContentBlob.DoesNotExist:
            raise FileNotFoundError(f"No content blob found for hash {name}")

        blob.last_accessed = timezone.now()
        blob.save(update_fields=["last_accessed"])

        return self.underlying.open(blob.storage_path)

    def delete(self, name: str) -> None:
        """
        Decrement reference count for a blob. Delete file if count reaches zero.

        Args:
            name: SHA-256 hash of the content.
        """
        from storage.models import ContentBlob

        try:
            blob = ContentBlob.objects.get(pk=name)
        except ContentBlob.DoesNotExist:
            logger.warning("Attempted to delete non-existent blob: %s", name)
            return

        blob.reference_count -= 1

        if blob.reference_count <= 0:
            self.underlying.delete(blob.storage_path)
            blob.delete()
            logger.info("Deleted blob %s (no remaining references)", name[:12])
        else:
            blob.save(update_fields=["reference_count"])
            logger.info(
                "Decremented ref count for blob %s (refs=%d)",
                name[:12],
                blob.reference_count,
            )

    def exists(self, name: str) -> bool:
        """
        Check if a content blob exists by its SHA-256 hash.

        Args:
            name: SHA-256 hash of the content.

        Returns:
            True if a blob record exists.
        """
        from storage.models import ContentBlob

        return ContentBlob.objects.filter(pk=name).exists()

    def url(self, name: str) -> str:
        """
        Get URL for content blob access.

        Delegates to the underlying backend using the blob's storage path.

        Args:
            name: SHA-256 hash of the content.

        Returns:
            URL string for accessing the file.
        """
        from storage.models import ContentBlob

        try:
            blob = ContentBlob.objects.get(pk=name)
            return self.underlying.url(blob.storage_path)
        except ContentBlob.DoesNotExist:
            raise FileNotFoundError(f"No content blob found for hash {name}")

    def size(self, name: str) -> int:
        """
        Get the size of a content blob.

        Returns the stored size from the database rather than querying the
        underlying backend.

        Args:
            name: SHA-256 hash of the content.

        Returns:
            File size in bytes.
        """
        from storage.models import ContentBlob

        try:
            blob = ContentBlob.objects.get(pk=name)
            return blob.size
        except ContentBlob.DoesNotExist:
            raise FileNotFoundError(f"No content blob found for hash {name}")

    def list_files(self, prefix: str = "") -> list[str]:
        """
        List all content blob hashes, optionally filtered by hash prefix.

        Args:
            prefix: Optional hash prefix to filter by.

        Returns:
            List of SHA-256 hashes.
        """
        from storage.models import ContentBlob

        qs = ContentBlob.objects.all()
        if prefix:
            qs = qs.filter(sha256_hash__startswith=prefix)
        return list(qs.values_list("sha256_hash", flat=True))

    def get_dedup_stats(self) -> dict:
        """
        Return deduplication statistics.

        Returns:
            Dictionary with storage statistics including total blobs,
            total references, space saved, etc.
        """
        from storage.models import ContentBlob

        stats = ContentBlob.objects.aggregate(
            total_blobs=Count("sha256_hash"),
            total_references=Sum("reference_count"),
            total_stored_bytes=Sum("size"),
            avg_refs_per_blob=Avg("reference_count"),
        )

        total_blobs = stats["total_blobs"] or 0
        total_references = stats["total_references"] or 0
        total_stored_bytes = stats["total_stored_bytes"] or 0

        # Logical bytes = what would be stored without dedup
        logical_bytes = ContentBlob.objects.aggregate(
            logical=Sum("size", default=0)
        )["logical"]
        if total_references > 0 and total_blobs > 0:
            # Weighted sum: each blob's size * its reference_count
            from django.db.models import F

            logical_bytes = (
                ContentBlob.objects.aggregate(
                    total=Sum(F("size") * F("reference_count"))
                )["total"]
                or 0
            )

        bytes_saved = logical_bytes - total_stored_bytes

        return {
            "total_blobs": total_blobs,
            "total_references": total_references,
            "total_stored_bytes": total_stored_bytes,
            "logical_bytes": logical_bytes,
            "bytes_saved": bytes_saved,
            "dedup_ratio": (
                round(logical_bytes / total_stored_bytes, 2)
                if total_stored_bytes > 0
                else 1.0
            ),
            "avg_refs_per_blob": round(stats["avg_refs_per_blob"] or 1.0, 2),
        }

    def _get_backend_name(self) -> str:
        """Return a short identifier for the underlying backend type."""
        cls_name = type(self.underlying).__name__
        name_map = {
            "LocalStorageBackend": "local",
            "S3StorageBackend": "s3",
        }
        return name_map.get(cls_name, cls_name.lower())

    def verify_integrity(self) -> list[dict]:
        """
        Verify that stored file hashes match ContentBlob records.

        Returns:
            List of dictionaries describing mismatches. Empty list if all OK.
        """
        from storage.models import ContentBlob

        mismatches = []
        for blob in ContentBlob.objects.all().iterator():
            try:
                fh = self.underlying.open(blob.storage_path)
                sha256 = hashlib.sha256()
                for chunk in iter(lambda: fh.read(65536), b""):
                    sha256.update(chunk)
                fh.close()

                actual_hash = sha256.hexdigest()
                if actual_hash != blob.sha256_hash:
                    mismatches.append(
                        {
                            "expected": blob.sha256_hash,
                            "actual": actual_hash,
                            "storage_path": blob.storage_path,
                            "error": "hash_mismatch",
                        }
                    )
            except FileNotFoundError:
                mismatches.append(
                    {
                        "expected": blob.sha256_hash,
                        "actual": None,
                        "storage_path": blob.storage_path,
                        "error": "file_missing",
                    }
                )
            except Exception as e:
                mismatches.append(
                    {
                        "expected": blob.sha256_hash,
                        "actual": None,
                        "storage_path": blob.storage_path,
                        "error": str(e),
                    }
                )

        return mismatches
