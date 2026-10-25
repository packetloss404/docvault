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
