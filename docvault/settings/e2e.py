"""Isolated acceptance stack: production code, PostgreSQL and real worker processes."""

import os

from django.core.exceptions import ImproperlyConfigured

from .production import *  # noqa: F401, F403

if os.environ.get("DOCVAULT_E2E") != "1":
    raise ImproperlyConfigured("The E2E settings require the isolated DOCVAULT_E2E=1 stack.")

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = "/data/export/mail"
RETENTION_HARD_DELETE_ENABLED = True
PORTAL_UPLOAD_RATE_LIMIT = 1000
ESIGNATURE_SIGNING_RATE = "2000/minute"
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {"anon": "2000/minute", "user": "5000/minute"},
}

# These jobs must run during a bounded acceptance test rather than overnight.
CELERY_BEAT_SCHEDULE = {
    **CELERY_BEAT_SCHEDULE,  # noqa: F405
    "scheduled-rules": {"task": "workflows.tasks.execute_scheduled_rules", "schedule": 2.0},
    "workflow-escalations": {"task": "workflows.tasks.check_workflow_escalations", "schedule": 2.0},
    "physical-overdue": {"task": "physical_records.check_overdue_charge_outs", "schedule": 2.0},
    "signature-expiry": {"task": "esignatures.tasks.expire_signature_requests", "schedule": 2.0},
    "portal-expiry": {"task": "portal.tasks.expire_overdue_requests", "schedule": 2.0},
    "portal-reminders": {"task": "portal.tasks.check_deadline_reminders", "schedule": 2.0},
    "retention-enforcement": {"task": "notifications.tasks.enforce_retention", "schedule": 2.0},
    "mail-poll": {"task": "sources.tasks.fetch_all_mail", "schedule": 2.0},
    "watch-folders": {"task": "sources.tasks.poll_watch_folders", "schedule": 2.0},
    "staging-sources": {"task": "sources.tasks.poll_staging_sources", "schedule": 2.0},
    "s3-sources": {"task": "sources.tasks.poll_s3_sources", "schedule": 2.0},
}
