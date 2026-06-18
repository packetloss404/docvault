"""Tests for watch-folder ingestion behavior."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from sources.constants import CONSUMED_ACTION_DELETE, SOURCE_WATCH_FOLDER
from sources.models import Source, WatchFolderSource
from sources.watch import poll_watch_folder

User = get_user_model()


class WatchFolderStagingTest(TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_delete_action_queues_staged_file_before_deleting_original(self):
        user = User.objects.create_user("owner", password="pass123")
        source = Source.objects.create(
            label="Watch",
            source_type=SOURCE_WATCH_FOLDER,
            owner=user,
        )
        folder = Path(self.tempdir.name)
        original = folder / "incoming.txt"
        original.write_text("hello", encoding="utf-8")
        watch = WatchFolderSource.objects.create(
            source=source,
            path=str(folder),
            consumed_action=CONSUMED_ACTION_DELETE,
        )

        queued_paths = []

        def capture_delay(source_path, *args, **kwargs):
            queued_paths.append(Path(source_path))

        with patch("processing.tasks.consume_document.delay", side_effect=capture_delay):
            submitted = poll_watch_folder(watch)

        self.assertEqual(submitted, 1)
        self.assertFalse(original.exists())
        self.assertEqual(len(queued_paths), 1)
        self.assertNotEqual(queued_paths[0], original)
        self.assertTrue(queued_paths[0].exists())
