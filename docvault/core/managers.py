from django.db import models


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that supports soft delete operations."""

    def delete(self):
        """Soft delete all objects in the queryset."""
        from django.utils import timezone

        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        """Permanently delete all objects in the queryset."""
        return super().delete()

    def alive(self):
        """Return only non-deleted objects."""
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        """Return only soft-deleted objects."""
        return self.filter(deleted_at__isnull=False)

    def restore(self):
        """Restore all soft-deleted objects in the queryset."""
        return self.update(deleted_at=None)


class SoftDeleteManager(models.Manager):
    """Manager that filters out soft-deleted records by default."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class AllObjectsManager(models.Manager):
    """Manager that includes soft-deleted records, with soft delete queryset methods."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)

    def alive(self):
        return self.get_queryset().alive()

    def dead(self):
        return self.get_queryset().dead()
