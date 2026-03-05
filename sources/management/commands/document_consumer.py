"""Management command for running the document consumer daemon."""

import logging
import time

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the document consumer daemon that polls watch folders for new files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=10,
            help="Default polling interval in seconds (default: 10)",
        )
        parser.add_argument(
            "--one-shot",
            action="store_true",
            help="Poll once and exit (for testing).",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        one_shot = options["one_shot"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting document consumer daemon (interval={interval}s)"
            )
        )

        while True:
            try:
                self._poll_all()
            except Exception:
                logger.exception("Error in document consumer daemon")

            if one_shot:
                break

            time.sleep(interval)

    def _poll_all(self):
        from sources.models import WatchFolderSource
        from sources.watch import poll_watch_folder

        sources = WatchFolderSource.objects.filter(
            source__enabled=True,
        ).select_related("source")

        for wf in sources:
            try:
                submitted = poll_watch_folder(wf)
                if submitted:
                    self.stdout.write(f"Submitted {submitted} file(s) from {wf.path}")
            except Exception:
                logger.exception("Error polling: %s", wf.path)
