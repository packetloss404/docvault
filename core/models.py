"""
Core abstract base models for DocVault.

All domain models should inherit from these base classes for consistent
behavior across the application:

- SoftDeleteModel: Soft deletion with trash support
- AuditableModel: Automatic timestamp and actor tracking
- OwnedModel: Ownership semantics
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from .managers import AllObjectsManager, SoftDeleteManager


class SoftDeleteModel(models.Model):
    """
    Abstract model providing soft delete functionality.

    Instead of permanently deleting records, sets a deleted_at timestamp.
    The default manager filters out deleted records. Use `all_objects`
    to include deleted records in queries.
    """

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def soft_delete(self):
        """Mark this object as deleted."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def restore(self):
        """Restore a soft-deleted object."""
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    def hard_delete(self):
        """Permanently delete this object from the database."""
        super().delete()

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class AuditableModel(models.Model):
    """
    Abstract model that tracks creation and modification timestamps
    along with the user who performed the action.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        abstract = True


class OwnedModel(models.Model):
    """
    Abstract model providing ownership semantics.

    The owner field indicates which user "owns" this object,
    used for permission checks and default filtering.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        abstract = True
