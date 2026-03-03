"""Tests for core abstract base models."""

from django.contrib.auth.models import User
from django.db import models
from django.test import TestCase
from django.utils import timezone

from core.managers import AllObjectsManager, SoftDeleteManager
from core.models import AuditableModel, OwnedModel, SoftDeleteModel


# Concrete test models (these use the abstract bases)
# We test via the Document model which inherits all three base classes.
# But we also need standalone tests for the managers.


class SoftDeleteManagerTest(TestCase):
    """Tests for SoftDeleteManager and SoftDeleteQuerySet."""

    def setUp(self):
        # Use Document model as our concrete test subject
        from documents.models import Document

        self.doc1 = Document.objects.create(title="Active Doc", filename="active.pdf")
        self.doc2 = Document.objects.create(title="Also Active", filename="also_active.pdf")
        self.doc3 = Document.all_objects.create(
            title="Deleted Doc",
            filename="deleted.pdf",
            deleted_at=timezone.now(),
        )

    def test_default_manager_excludes_deleted(self):
        from documents.models import Document

        qs = Document.objects.all()
        self.assertEqual(qs.count(), 2)
        titles = set(qs.values_list("title", flat=True))
        self.assertIn("Active Doc", titles)
        self.assertIn("Also Active", titles)
        self.assertNotIn("Deleted Doc", titles)

    def test_all_objects_includes_deleted(self):
        from documents.models import Document

        qs = Document.all_objects.all()
        self.assertEqual(qs.count(), 3)

    def test_soft_delete(self):
        from documents.models import Document

        self.doc1.soft_delete()
        self.assertIsNotNone(self.doc1.deleted_at)
        self.assertTrue(self.doc1.is_deleted)
        # Should no longer appear in default manager
        self.assertEqual(Document.objects.count(), 1)

    def test_restore(self):
        from documents.models import Document

        self.doc3.restore()
        self.assertIsNone(self.doc3.deleted_at)
        self.assertFalse(self.doc3.is_deleted)
        # Should now appear in default manager
        self.assertEqual(Document.objects.count(), 3)

    def test_hard_delete(self):
        from documents.models import Document

        self.doc1.hard_delete()
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(Document.all_objects.count(), 2)

    def test_queryset_delete_soft_deletes(self):
        from documents.models import Document

        Document.objects.all().delete()
        # All should be soft deleted
        self.assertEqual(Document.objects.count(), 0)
        self.assertEqual(Document.all_objects.count(), 3)
        # All should have deleted_at set
        for doc in Document.all_objects.all():
            self.assertIsNotNone(doc.deleted_at)

    def test_queryset_alive(self):
        from documents.models import Document

        qs = Document.all_objects.alive()
        self.assertEqual(qs.count(), 2)

    def test_queryset_dead(self):
        from documents.models import Document

        qs = Document.all_objects.dead()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().title, "Deleted Doc")

    def test_queryset_restore(self):
        from documents.models import Document

        Document.all_objects.dead().restore()
        self.assertEqual(Document.objects.count(), 3)

    def test_is_deleted_property(self):
        self.assertFalse(self.doc1.is_deleted)
        self.assertTrue(self.doc3.is_deleted)


class AuditableModelTest(TestCase):
    """Tests for AuditableModel timestamps and actor tracking."""

    def test_created_at_auto_set(self):
        from documents.models import Document

        doc = Document.objects.create(title="Test", filename="test.pdf")
        self.assertIsNotNone(doc.created_at)

    def test_updated_at_auto_updated(self):
        from documents.models import Document

        doc = Document.objects.create(title="Test", filename="test.pdf")
        original_updated = doc.updated_at
        doc.title = "Updated Test"
        doc.save()
        doc.refresh_from_db()
        self.assertGreaterEqual(doc.updated_at, original_updated)

    def test_created_by_optional(self):
        from documents.models import Document

        doc = Document.objects.create(title="Test", filename="test.pdf")
        self.assertIsNone(doc.created_by)

    def test_created_by_with_user(self):
        from documents.models import Document

        user = User.objects.create_user("testuser", password="testpass")
        doc = Document.objects.create(title="Test", filename="test.pdf", created_by=user)
        self.assertEqual(doc.created_by, user)

    def test_user_deletion_nullifies(self):
        from documents.models import Document

        user = User.objects.create_user("testuser", password="testpass")
        doc = Document.objects.create(title="Test", filename="test.pdf", created_by=user)
        user.delete()
        doc.refresh_from_db()
        self.assertIsNone(doc.created_by)


class OwnedModelTest(TestCase):
    """Tests for OwnedModel ownership semantics."""

    def test_owner_optional(self):
        from documents.models import Document

        doc = Document.objects.create(title="Test", filename="test.pdf")
        self.assertIsNone(doc.owner)

    def test_owner_set(self):
        from documents.models import Document

        user = User.objects.create_user("testuser", password="testpass")
        doc = Document.objects.create(title="Test", filename="test.pdf", owner=user)
        self.assertEqual(doc.owner, user)

    def test_owner_deletion_nullifies(self):
        from documents.models import Document

        user = User.objects.create_user("testuser", password="testpass")
        doc = Document.objects.create(title="Test", filename="test.pdf", owner=user)
        user.delete()
        doc.refresh_from_db()
        self.assertIsNone(doc.owner)
