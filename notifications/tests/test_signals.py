import pytest
from django.contrib.auth import get_user_model

from documents.models import Document
from notifications.constants import EVENT_DOCUMENT_PROCESSED, EVENT_PROCESSING_FAILED
from notifications.models import Notification
from processing.models import ProcessingTask

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return get_user_model().objects.create_user(username="processing-owner")


def test_failure_without_document_notifies_task_owner_once(owner):
    task = ProcessingTask.objects.create(owner=owner)
    task.status = ProcessingTask.Status.FAILURE
    task.result = "OCR failed"
    task.save()
    task.acknowledged = True
    task.save(update_fields=["acknowledged"])
    task.save()
    notifications = Notification.objects.filter(user=owner, event_type=EVENT_PROCESSING_FAILED)
    assert notifications.count() == 1
    assert "OCR failed" in notifications.get().body
    assert notifications.get().document_id is None


def test_success_does_not_repeat_for_progress_or_full_saves(owner):
    document = Document.objects.create(title="Completed", owner=owner)
    task = ProcessingTask.objects.create(owner=owner, document=document)
    task.status = ProcessingTask.Status.SUCCESS
    task.save(update_fields=["status"])
    task.progress = 1.0
    task.save(update_fields=["progress"])
    task.save()
    assert Notification.objects.filter(user=owner, event_type=EVENT_DOCUMENT_PROCESSED).count() == 1


def test_unsaved_terminal_status_does_not_notify_on_unrelated_update(owner):
    task = ProcessingTask.objects.create(owner=owner)
    task.status = ProcessingTask.Status.FAILURE
    task.acknowledged = True
    task.save(update_fields=["acknowledged"])
    assert not Notification.objects.filter(user=owner, event_type=EVENT_PROCESSING_FAILED).exists()
