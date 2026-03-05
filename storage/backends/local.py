"""Local filesystem storage backend."""

import os
import shutil
from pathlib import Path
from typing import BinaryIO

from django.conf import settings

from .base import StorageBackend


class LocalStorageBackend(StorageBackend):
    """Store files on the local filesystem."""

    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir or settings.STORAGE_DIR)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create the storage directory structure."""
        for subdir in ("originals", "archive", "thumbnails"):
            (self.base_dir / subdir).mkdir(parents=True, exist_ok=True)

    def _full_path(self, name: str) -> Path:
        return self.base_dir / name

    def save(self, name: str, content: BinaryIO) -> str:
        path = self._full_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            shutil.copyfileobj(content, f)
        return name

    def open(self, name: str) -> BinaryIO:
        path = self._full_path(name)
        return open(path, "rb")

    def delete(self, name: str) -> None:
        path = self._full_path(name)
        if path.is_file():
            path.unlink()

    def exists(self, name: str) -> bool:
        return self._full_path(name).is_file()

    def url(self, name: str) -> str:
        return f"{settings.MEDIA_URL}documents/{name}"

    def size(self, name: str) -> int:
        return self._full_path(name).stat().st_size

    def list_files(self, prefix: str = "") -> list[str]:
        search_dir = self._full_path(prefix) if prefix else self.base_dir
        if not search_dir.is_dir():
            return []
        return [
            str(p.relative_to(self.base_dir))
            for p in search_dir.rglob("*")
            if p.is_file()
        ]
