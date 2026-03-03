"""Tests for processing models."""

from django.contrib.auth.models import User
from django.test import TestCase

from processing.models import ProcessingTask


class ProcessingTaskModelTest(TestCase):
    """Tests for the ProcessingTask model."""

    def setUp(self):
        self.user = User.objects.create_user("taskuser", password="test123!")

    def test_create_task(self):
        task = ProcessingTask.objects.create(
            task_name="document_consumption",
            owner=self.user,
        )
        self.assertEqual(task.status, ProcessingTask.Status.PENDING)
        self.assertEqual(task.progress, 0.0)
        self.assertIsNotNone(task.task_id)
        self.assertIsNotNone(task.created_at)

    def test_task_str(self):
        task = ProcessingTask.objects.create(
            task_name="document_consumption", owner=self.user,
        )
        self.assertIn("document_consumption", str(task))
        self.assertIn("pending", str(task))

    def test_task_status_transitions(self):
        task = ProcessingTask.objects.create(
            task_name="test", owner=self.user,
        )
        self.assertEqual(task.status, ProcessingTask.Status.PENDING)

        task.status = ProcessingTask.Status.STARTED
        task.save()
        task.refresh_from_db()
        self.assertEqual(task.status, ProcessingTask.Status.STARTED)

        task.status = ProcessingTask.Status.SUCCESS
        task.save()
        task.refresh_from_db()
        self.assertEqual(task.status, ProcessingTask.Status.SUCCESS)

    def test_task_unique_task_id(self):
        t1 = ProcessingTask.objects.create(task_name="t1", owner=self.user)
        t2 = ProcessingTask.objects.create(task_name="t2", owner=self.user)
        self.assertNotEqual(t1.task_id, t2.task_id)

    def test_task_acknowledge(self):
        task = ProcessingTask.objects.create(
            task_name="ack_test", owner=self.user,
        )
        self.assertFalse(task.acknowledged)
        task.acknowledged = True
        task.save()
        task.refresh_from_db()
        self.assertTrue(task.acknowledged)

    def test_task_ordering(self):
        """Tasks should be ordered by -created_at (newest first)."""
        t1 = ProcessingTask.objects.create(task_name="first", owner=self.user)
        t2 = ProcessingTask.objects.create(task_name="second", owner=self.user)
        tasks = list(ProcessingTask.objects.all())
        self.assertEqual(tasks[0], t2)
        self.assertEqual(tasks[1], t1)
