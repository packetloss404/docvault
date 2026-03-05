"""Celery configuration for DocVault."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "docvault.settings.development")

app = Celery("docvault")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
