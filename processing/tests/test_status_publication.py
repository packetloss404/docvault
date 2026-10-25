from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.db import transaction

from processing.models import ProcessingTask


@pytest.mark.django_db
def test_task_status_is_published_only_after_commit(django_capture_on_commit_callbacks):
    owner = User.objects.create_user("status-recipient")
    with patch("processing.signals.send_task_update") as publish:
        with django_capture_on_commit_callbacks(execute=True):
            task = ProcessingTask.objects.create(owner=owner, status_message="Queued")
            publish.assert_not_called()
        publish.assert_called_once_with(task.task_id, owner.pk, 0.0, "Queued", "pending")


@pytest.mark.django_db
def test_failed_tasks_publish_the_failure_reason(django_capture_on_commit_callbacks):
    owner = User.objects.create_user("failed-status-recipient")
    task = ProcessingTask.objects.create(owner=owner)
    with patch("processing.signals.send_task_update") as publish:
        with django_capture_on_commit_callbacks(execute=True):
            task.status = "failure"
            task.result = "Unreadable document"
            task.save()
        assert publish.call_args.args[-2:] == ("Unreadable document", "failure")


@pytest.mark.django_db
def test_rollback_does_not_publish_a_task(django_capture_on_commit_callbacks):
    owner = User.objects.create_user("rollback-status-recipient")
    with patch("processing.signals.send_task_update") as publish:
        with django_capture_on_commit_callbacks(execute=True):
            with pytest.raises(ValueError), transaction.atomic():
                ProcessingTask.objects.create(owner=owner)
                raise ValueError("Abort")
        publish.assert_not_called()
