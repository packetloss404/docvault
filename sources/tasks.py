"""Celery tasks for source polling."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def poll_watch_folders():
    """Poll all enabled watch folder sources for new files."""
    from sources.models import WatchFolderSource
    from sources.watch import poll_watch_folder

    sources = WatchFolderSource.objects.filter(
        source__enabled=True,
    ).select_related("source")

    total = 0
    for wf in sources:
        try:
            submitted = poll_watch_folder(wf)
            total += submitted
        except Exception:
            logger.exception("Error polling watch folder: %s", wf.path)

    return {"submitted": total}


@shared_task
def fetch_all_mail():
    """Fetch mail from all enabled mail accounts."""
    from sources.mail import fetch_mail
    from sources.models import MailAccount

    accounts = MailAccount.objects.filter(enabled=True)

    total = 0
    for account in accounts:
        try:
            processed = fetch_mail(account)
            total += processed
        except Exception:
            logger.exception("Error fetching mail for account: %s", account.name)

    return {"processed": total}
