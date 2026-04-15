"""Celery configuration for DocVault."""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "docvault.settings.development")

app = Celery("docvault")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "workflow-escalations": {
        "task": "workflows.tasks.check_workflow_escalations",
        "schedule": 300.0,  # every 5 minutes
    },
    "scheduled-rules": {
        "task": "workflows.tasks.execute_scheduled_rules",
        "schedule": 900.0,  # every 15 minutes
    },
    "mail-poll": {
        "task": "sources.tasks.fetch_all_mail",
        "schedule": 300.0,  # every 5 minutes
    },
    "retention-check": {
        "task": "legal_hold.tasks.reevaluate_holds",
        "schedule": crontab(hour=2, minute=0),  # daily at 2 AM
    },
    "es-optimize": {
        "task": "search.optimize_index",
        "schedule": crontab(hour=3, minute=0),  # nightly at 3 AM
    },
}
