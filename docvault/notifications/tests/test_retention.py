"""Tests for retention policy enforcement."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from documents.constants import (
    TIME_UNIT_DAYS,
    TIME_UNIT_MONTHS,
    TIME_UNIT_WEEKS,
    TIME_UNIT_YEARS,
)
from documents.models import Document
from documents.models.document_type import DocumentType
from notifications.tasks import _to_timedelta, enforce_retention, prune_stale_uploads
from processing.models import ProcessingTask


class ToTimedeltaTest(TestCase):
    """Tests for the _to_timedelta helper function."""

    def test_days_conversion(self):
        """Days should convert directly to timedelta days."""
        result = _to_timedelta(7, TIME_UNIT_DAYS)
        self.assertEqual(result, timedelta(days=7))

    def test_weeks_conversion(self):
        """Weeks should convert to 7 * period days."""
        result = _to_timedelta(2, TIME_UNIT_WEEKS)
        self.assertEqual(result, timedelta(weeks=2))
        self.assertEqual(result, timedelta(days=14))

    def test_months_conversion(self):
        """Months should convert to 30 * period days."""
        result = _to_timedelta(3, TIME_UNIT_MONTHS)
        self.assertEqual(result, timedelta(days=90))

    def test_years_conversion(self):
        """Years should convert to 365 * period days."""
        result = _to_timedelta(2, TIME_UNIT_YEARS)
        self.assertEqual(result, timedelta(days=730))

    def test_single_year(self):
        """One year should be 365 days."""
        result = _to_timedelta(1, TIME_UNIT_YEARS)
        self.assertEqual(result, timedelta(days=365))

    def test_unknown_unit_defaults_to_days(self):
        """An unknown unit should fall back to days."""
        result = _to_timedelta(5, "unknown")
        self.assertEqual(result, timedelta(days=5))


class RetentionEnforcementTest(TestCase):
    """Tests for the enforce_retention task."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123!"
        )
        self.doc_type = DocumentType.objects.create(
            name="Temporary",
            trash_time_period=7,
            trash_time_unit=TIME_UNIT_DAYS,
        )

    def _create_document(self, title, doc_type=None, filename=None):
        """Helper to create a document with a unique filename."""
        if filename is None:
            filename = f"{title.lower().replace(' ', '_')}.pdf"
        return Document.objects.create(
            title=title,
            owner=self.user,
            document_type=doc_type or self.doc_type,
            filename=filename,
        )

    def test_trash_old_documents(self):
        """Documents past the trash retention deadline should be soft-deleted."""
        doc = self._create_document("Old Invoice")
        past_date = timezone.now() - timedelta(days=10)
        Document.objects.filter(pk=doc.pk).update(added=past_date)
        doc.refresh_from_db()

        result = enforce_retention()

        # Document should now be soft-deleted
        self.assertFalse(Document.objects.filter(pk=doc.pk).exists())
        self.assertTrue(Document.all_objects.filter(pk=doc.pk).exists())
        doc.refresh_from_db()
        self.assertIsNotNone(doc.deleted_at)
        self.assertEqual(result["trashed"], 1)

    def test_skip_recent_documents(self):
        """Documents within the retention period should not be trashed."""
        doc = self._create_document("Recent Invoice")
        past_date = timezone.now() - timedelta(days=3)
        Document.objects.filter(pk=doc.pk).update(added=past_date)
        doc.refresh_from_db()

        result = enforce_retention()

        # Document should still be visible in the default manager
        self.assertTrue(Document.objects.filter(pk=doc.pk).exists())
        doc.refresh_from_db()
        self.assertIsNone(doc.deleted_at)
        self.assertEqual(result["trashed"], 0)

    def test_skip_documents_without_retention(self):
        """Documents with a type that has no retention settings are untouched."""
        no_retention_type = DocumentType.objects.create(
            name="Permanent",
        )
        doc = self._create_document(
            "Permanent Doc",
            doc_type=no_retention_type,
            filename="permanent_doc.pdf",
        )
        past_date = timezone.now() - timedelta(days=365)
        Document.objects.filter(pk=doc.pk).update(added=past_date)
        doc.refresh_from_db()

        result = enforce_retention()

        self.assertTrue(Document.objects.filter(pk=doc.pk).exists())
        doc.refresh_from_db()
        self.assertIsNone(doc.deleted_at)
        self.assertEqual(result["trashed"], 0)

    def test_delete_trashed_documents(self):
        """Trashed documents past the delete deadline should be hard-deleted."""
        doc_type_with_delete = DocumentType.objects.create(
            name="Full Lifecycle",
            delete_time_period=30,
            delete_time_unit=TIME_UNIT_DAYS,
        )
        doc = self._create_document(
            "Trashed Doc",
            doc_type=doc_type_with_delete,
            filename="trashed_doc.pdf",
        )
        # Soft-delete the document
        doc.soft_delete()
        # Set deleted_at to 35 days ago
        past_deleted = timezone.now() - timedelta(days=35)
        Document.all_objects.filter(pk=doc.pk).update(deleted_at=past_deleted)
        doc.refresh_from_db()

        result = enforce_retention()

        # Document should be permanently gone
        self.assertFalse(Document.all_objects.filter(pk=doc.pk).exists())
        self.assertEqual(result["deleted"], 1)

    def test_skip_recently_trashed(self):
        """Recently trashed documents within delete period are not hard-deleted."""
        doc_type_with_delete = DocumentType.objects.create(
            name="Delete After 30",
            delete_time_period=30,
            delete_time_unit=TIME_UNIT_DAYS,
        )
        doc = self._create_document(
            "Recently Trashed",
            doc_type=doc_type_with_delete,
            filename="recently_trashed.pdf",
        )
        doc.soft_delete()
        # Set deleted_at to 5 days ago (within the 30 day window)
        recent_deleted = timezone.now() - timedelta(days=5)
        Document.all_objects.filter(pk=doc.pk).update(deleted_at=recent_deleted)
        doc.refresh_from_db()

        result = enforce_retention()

        # Document should still exist in all_objects
        self.assertTrue(Document.all_objects.filter(pk=doc.pk).exists())
        self.assertEqual(result["deleted"], 0)

    def test_dry_run_no_changes(self):
        """Dry run mode should not actually trash any documents."""
        doc = self._create_document("Dry Run Doc")
        past_date = timezone.now() - timedelta(days=10)
        Document.objects.filter(pk=doc.pk).update(added=past_date)
        doc.refresh_from_db()

        result = enforce_retention(dry_run=True)

        # Document should still be alive
        self.assertTrue(Document.objects.filter(pk=doc.pk).exists())
        doc.refresh_from_db()
        self.assertIsNone(doc.deleted_at)
        # But the count should still reflect what WOULD have been trashed
        self.assertEqual(result["trashed"], 1)
        self.assertTrue(result["dry_run"])

    def test_retention_with_weeks(self):
        """Retention using weeks unit should trash documents correctly."""
        doc_type_weeks = DocumentType.objects.create(
            name="Weekly Retention",
            trash_time_period=2,
            trash_time_unit=TIME_UNIT_WEEKS,
        )
        doc = self._create_document(
            "Week Old Doc",
            doc_type=doc_type_weeks,
            filename="week_old_doc.pdf",
        )
        # 15 days ago (> 14 days = 2 weeks)
        past_date = timezone.now() - timedelta(days=15)
        Document.objects.filter(pk=doc.pk).update(added=past_date)
        doc.refresh_from_db()

        result = enforce_retention()

        self.assertFalse(Document.objects.filter(pk=doc.pk).exists())
        self.assertTrue(Document.all_objects.filter(pk=doc.pk).exists())
        self.assertEqual(result["trashed"], 1)

    def test_return_counts(self):
        """The task should return a dict with trashed, deleted, and dry_run."""
        result = enforce_retention()
        self.assertIn("trashed", result)
        self.assertIn("deleted", result)
        self.assertIn("dry_run", result)
        self.assertIsInstance(result["trashed"], int)
        self.assertIsInstance(result["deleted"], int)
        self.assertIsInstance(result["dry_run"], bool)
        self.assertFalse(result["dry_run"])

    def test_return_counts_dry_run(self):
        """Dry run should return dry_run=True in the result."""
        result = enforce_retention(dry_run=True)
        self.assertTrue(result["dry_run"])

    def test_multiple_doc_types_enforcement(self):
        """Retention is enforced per document type independently."""
        doc_type_30 = DocumentType.objects.create(
            name="Monthly Retention",
            trash_time_period=30,
            trash_time_unit=TIME_UNIT_DAYS,
        )
        # Old doc with 7-day retention => should be trashed
        doc1 = self._create_document("Short Lived", filename="short_lived.pdf")
        past_date_10 = timezone.now() - timedelta(days=10)
        Document.objects.filter(pk=doc1.pk).update(added=past_date_10)

        # 10-day-old doc with 30-day retention => should NOT be trashed
        doc2 = self._create_document(
            "Long Lived",
            doc_type=doc_type_30,
            filename="long_lived.pdf",
        )
        Document.objects.filter(pk=doc2.pk).update(added=past_date_10)

        result = enforce_retention()

        self.assertFalse(Document.objects.filter(pk=doc1.pk).exists())
        self.assertTrue(Document.objects.filter(pk=doc2.pk).exists())
        self.assertEqual(result["trashed"], 1)


class PruneStaleUploadsTest(TestCase):
    """Tests for the prune_stale_uploads task."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123!"
        )

    def test_prune_old_pending_tasks(self):
        """Pending tasks older than max_age should be marked as failure."""
        task = ProcessingTask.objects.create(
            task_name="document_consumption",
            owner=self.user,
            status=ProcessingTask.Status.PENDING,
        )
        # Set created_at to 48 hours ago
        past_date = timezone.now() - timedelta(hours=48)
        ProcessingTask.objects.filter(pk=task.pk).update(created_at=past_date)
        task.refresh_from_db()

        result = prune_stale_uploads(max_age_hours=24)

        task.refresh_from_db()
        self.assertEqual(task.status, ProcessingTask.Status.FAILURE)
        self.assertIn("Pruned", task.result)
        self.assertEqual(result["pruned"], 1)

    def test_skip_recent_pending(self):
        """Recently created pending tasks should not be pruned."""
        task = ProcessingTask.objects.create(
            task_name="document_consumption",
            owner=self.user,
            status=ProcessingTask.Status.PENDING,
        )
        # Set created_at to 2 hours ago (well within 24-hour window)
        recent_date = timezone.now() - timedelta(hours=2)
        ProcessingTask.objects.filter(pk=task.pk).update(created_at=recent_date)
        task.refresh_from_db()

        result = prune_stale_uploads(max_age_hours=24)

        task.refresh_from_db()
        self.assertEqual(task.status, ProcessingTask.Status.PENDING)
        self.assertEqual(result["pruned"], 0)

    def test_skip_completed_tasks(self):
        """Completed tasks older than max_age should not be pruned."""
        task = ProcessingTask.objects.create(
            task_name="document_consumption",
            owner=self.user,
            status=ProcessingTask.Status.SUCCESS,
        )
        # Set created_at to 48 hours ago
        past_date = timezone.now() - timedelta(hours=48)
        ProcessingTask.objects.filter(pk=task.pk).update(created_at=past_date)
        task.refresh_from_db()

        result = prune_stale_uploads(max_age_hours=24)

        task.refresh_from_db()
        # Status should remain SUCCESS, not be changed to FAILURE
        self.assertEqual(task.status, ProcessingTask.Status.SUCCESS)
        self.assertEqual(result["pruned"], 0)

    def test_skip_failed_tasks(self):
        """Already-failed tasks should not be pruned again."""
        task = ProcessingTask.objects.create(
            task_name="document_consumption",
            owner=self.user,
            status=ProcessingTask.Status.FAILURE,
            result="Original failure reason",
        )
        past_date = timezone.now() - timedelta(hours=48)
        ProcessingTask.objects.filter(pk=task.pk).update(created_at=past_date)
        task.refresh_from_db()

        result = prune_stale_uploads(max_age_hours=24)

        task.refresh_from_db()
        self.assertEqual(task.status, ProcessingTask.Status.FAILURE)
        self.assertEqual(task.result, "Original failure reason")
        self.assertEqual(result["pruned"], 0)

    def test_custom_max_age(self):
        """Custom max_age_hours should be respected."""
        task = ProcessingTask.objects.create(
            task_name="document_consumption",
            owner=self.user,
            status=ProcessingTask.Status.PENDING,
        )
        # Set created_at to 5 hours ago
        past_date = timezone.now() - timedelta(hours=5)
        ProcessingTask.objects.filter(pk=task.pk).update(created_at=past_date)
        task.refresh_from_db()

        # With 4-hour max age, this should be pruned
        result = prune_stale_uploads(max_age_hours=4)

        task.refresh_from_db()
        self.assertEqual(task.status, ProcessingTask.Status.FAILURE)
        self.assertEqual(result["pruned"], 1)

    def test_prune_multiple_stale_tasks(self):
        """Multiple stale pending tasks should all be pruned."""
        past_date = timezone.now() - timedelta(hours=48)
        for i in range(3):
            task = ProcessingTask.objects.create(
                task_name="document_consumption",
                owner=self.user,
                status=ProcessingTask.Status.PENDING,
            )
            ProcessingTask.objects.filter(pk=task.pk).update(created_at=past_date)

        result = prune_stale_uploads(max_age_hours=24)

        self.assertEqual(result["pruned"], 3)
        # All should be marked as failure
        pending_count = ProcessingTask.objects.filter(
            status=ProcessingTask.Status.PENDING
        ).count()
        self.assertEqual(pending_count, 0)
