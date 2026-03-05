"""Tests for storage backends."""

import io
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings

from storage.backends.local import LocalStorageBackend


class LocalStorageBackendTest(TestCase):
    """Tests for the local filesystem storage backend."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.backend = LocalStorageBackend(base_dir=self.temp_dir)

    def test_ensure_directories_created(self):
        """The backend creates originals/, archive/, thumbnails/ subdirs."""
        for subdir in ("originals", "archive", "thumbnails"):
            self.assertTrue((Path(self.temp_dir) / subdir).is_dir())

    def test_save_and_open(self):
        content = io.BytesIO(b"Hello, DocVault!")
        name = self.backend.save("originals/test.txt", content)
        self.assertEqual(name, "originals/test.txt")

        f = self.backend.open("originals/test.txt")
        self.assertEqual(f.read(), b"Hello, DocVault!")
        f.close()

    def test_exists(self):
        self.assertFalse(self.backend.exists("originals/nope.txt"))
        self.backend.save("originals/exists.txt", io.BytesIO(b"data"))
        self.assertTrue(self.backend.exists("originals/exists.txt"))

    def test_delete(self):
        self.backend.save("originals/deleteme.txt", io.BytesIO(b"data"))
        self.assertTrue(self.backend.exists("originals/deleteme.txt"))
        self.backend.delete("originals/deleteme.txt")
        self.assertFalse(self.backend.exists("originals/deleteme.txt"))

    def test_delete_nonexistent_no_error(self):
        """Deleting a non-existent file should not raise."""
        self.backend.delete("originals/nonexistent.txt")

    def test_size(self):
        data = b"x" * 1024
        self.backend.save("originals/sized.txt", io.BytesIO(data))
        self.assertEqual(self.backend.size("originals/sized.txt"), 1024)

    def test_url(self):
        url = self.backend.url("originals/test.txt")
        self.assertIn("documents/originals/test.txt", url)

    def test_list_files(self):
        self.backend.save("originals/a.txt", io.BytesIO(b"a"))
        self.backend.save("originals/b.txt", io.BytesIO(b"b"))
        self.backend.save("archive/c.txt", io.BytesIO(b"c"))

        all_files = self.backend.list_files()
        self.assertEqual(len(all_files), 3)

        originals = self.backend.list_files("originals")
        self.assertEqual(len(originals), 2)

    def test_list_files_empty_prefix(self):
        files = self.backend.list_files("nonexistent")
        self.assertEqual(files, [])

    def test_save_creates_subdirectories(self):
        """Saving to a nested path should create parent dirs."""
        self.backend.save("originals/2025/01/doc.txt", io.BytesIO(b"nested"))
        self.assertTrue(self.backend.exists("originals/2025/01/doc.txt"))


class StorageUtilsTest(TestCase):
    """Tests for the get_storage_backend utility."""

    @override_settings(STORAGE_BACKEND="local")
    def test_get_local_backend(self):
        from storage.utils import get_storage_backend
        backend = get_storage_backend()
        self.assertIsInstance(backend, LocalStorageBackend)

    @override_settings(STORAGE_BACKEND="unknown")
    def test_unknown_backend_defaults_to_local(self):
        from storage.utils import get_storage_backend
        backend = get_storage_backend()
        self.assertIsInstance(backend, LocalStorageBackend)
