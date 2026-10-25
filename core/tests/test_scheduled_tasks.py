import gc
import importlib
import json
import os
import subprocess
import sys
from unittest.mock import Mock
from uuid import uuid4

import pytest
from celery import Celery
from celery.beat import ScheduleEntry, Scheduler
from celery.result import allow_join_result

from docvault.celery import app


def test_scheduled_tasks_are_registered():
    app.autodiscover_tasks(force=True)
    for name, entry in app.conf.beat_schedule.items():
        assert entry["task"] in app.tasks, f"Scheduled job {name} references an unregistered task"


def test_advertised_deadline_jobs_are_scheduled():
    scheduled = {entry["task"] for entry in app.conf.beat_schedule.values()}
    assert {
        "workflows.tasks.check_workflow_escalations",
        "physical_records.check_overdue_charge_outs",
        "esignatures.tasks.expire_signature_requests",
        "portal.tasks.expire_overdue_requests",
        "portal.tasks.check_deadline_reminders",
        "notifications.tasks.enforce_retention",
    } <= scheduled


def test_ordinary_tasks_use_the_queue_consumed_by_the_worker():
    assert app.conf.task_default_queue == "default"


@pytest.mark.parametrize("module_name", ["docvault.settings.base", "docvault.settings.e2e"])
def test_every_periodic_entry_ignores_unused_results(module_name):
    script = (
        "import importlib,json,sys; module=importlib.import_module(sys.argv[1]); "
        "print(json.dumps({name:entry.get('options',{}).get('ignore_result',False) "
        "for name,entry in module.CELERY_BEAT_SCHEDULE.items()}))"
    )
    environment = {
        **os.environ, "DOCVAULT_E2E": "1",
        "DJANGO_SECRET_KEY": "d994c8f66bf44e0683e8e38409d3bdef-scheduler-test",
    }
    result = subprocess.run(
        [sys.executable, "-c", script, module_name], env=environment,
        check=True, capture_output=True, text=True, timeout=15,
    )
    schedule = json.loads(result.stdout)
    assert schedule
    assert all(schedule.values()), f"Periodic results remain enabled: {schedule}"


@pytest.fixture
def result_tracking_app(monkeypatch):
    task_app = Celery(
        "periodic-results-test", broker="memory://", backend="redis://localhost:6379/0",
        set_as_current=False, fixups=[],
    )
    queue = f"periodic-test-{uuid4().hex}"
    task_app.conf.update(task_always_eager=False, task_ignore_result=False, task_default_queue=queue)
    backend = task_app.backend
    transport = Mock(name="redis_transport")
    monkeypatch.setattr(backend, "client", transport)
    subscribe = Mock(wraps=backend.result_consumer.consume_from)
    monkeypatch.setattr(backend.result_consumer, "consume_from", subscribe)
    with allow_join_result():
        yield task_app, queue, transport, subscribe
    with task_app.connection() as connection, connection.SimpleQueue(queue) as messages:
        messages.clear()
    task_app.close()


def test_periodic_dispatch_and_result_gc_never_open_redis_pubsub(result_tracking_app):
    task_app, queue, transport, subscribe = result_tracking_app
    scheduler = Scheduler(app=task_app, lazy=True)
    schedule = importlib.import_module("docvault.settings.base").CELERY_BEAT_SCHEDULE
    ignored_results = []
    for name, configured in schedule.items():
        entry = ScheduleEntry(
            name=name, app=task_app, task=configured["task"], schedule=configured["schedule"],
            options={**configured.get("options", {}), "queue": queue},
        )
        result = scheduler.apply_async(entry, advance=False)
        ignored_results.append(result.ignored)
        del result
    gc.collect()
    subscribe.assert_not_called()
    transport.pubsub.assert_not_called()
    assert task_app.backend.result_consumer._pubsub is None
    assert all(ignored_results)
    with task_app.connection() as connection, connection.SimpleQueue(queue) as messages:
        for _ in schedule:
            message = messages.get(block=False)
            assert message.headers["ignore_result"] is True
            assert message.delivery_info["routing_key"] == queue
            message.ack()


def test_user_ingestion_still_tracks_results(result_tracking_app):
    from processing.tasks import consume_document

    task_app, queue, transport, subscribe = result_tracking_app
    task = task_app.tasks[consume_document.name]
    assert task_app.conf.task_ignore_result is False
    assert task.ignore_result is False
    result = task.apply_async(args=["source.txt", "source.txt", str(uuid4()), 1], queue=queue)
    assert result.ignored is False
    subscribe.assert_called_once_with(result.id)
    transport.pubsub.return_value.subscribe.assert_called_once_with(task_app.backend.get_key_for_task(result.id))
    with task_app.connection() as connection, connection.SimpleQueue(queue) as messages:
        message = messages.get(block=False)
        assert message.headers["ignore_result"] is False
        message.ack()
