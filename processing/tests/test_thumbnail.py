"""Tests for the ThumbnailPlugin."""

import tempfile
from pathlib import Path

from django.test import TestCase
from PIL import Image

from processing.context import ProcessingContext
from processing.plugins.thumbnail import ThumbnailPlugin


class ThumbnailPluginTest(TestCase):
    """Tests for ThumbnailPlugin."""

    def setUp(self):
        self.plugin = ThumbnailPlugin()
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_can_run_with_source_and_mime(self):
        ctx = ProcessingContext(
            source_path=Path("/tmp/test.txt"),
            mime_type="text/plain",
        )
        self.assertTrue(self.plugin.can_run(ctx))

    def test_can_run_without_source(self):
        ctx = ProcessingContext(mime_type="text/plain")
        self.assertFalse(self.plugin.can_run(ctx))

    def test_can_run_without_mime(self):
        ctx = ProcessingContext(source_path=Path("/tmp/test"))
        self.assertFalse(self.plugin.can_run(ctx))

    def test_thumbnail_from_image_png(self):
        """Generate a thumbnail from a PNG image."""
        img_path = self.temp_dir / "test.png"
        img = Image.new("RGB", (800, 1000), color="blue")
        img.save(str(img_path))

        ctx = ProcessingContext(
            source_path=img_path,
            mime_type="image/png",
        )
        result = self.plugin.process(ctx)

        self.assertTrue(result.success)
        self.assertIsNotNone(ctx.thumbnail_path)
        self.assertTrue(ctx.thumbnail_path.exists())
        self.assertTrue(str(ctx.thumbnail_path).endswith(".webp"))

    def test_thumbnail_from_rgba_image(self):
        """RGBA images should be converted correctly."""
        img_path = self.temp_dir / "rgba.png"
        img = Image.new("RGBA", (600, 800), color=(255, 0, 0, 128))
        img.save(str(img_path))

        ctx = ProcessingContext(
            source_path=img_path,
            mime_type="image/png",
        )
        result = self.plugin.process(ctx)

        self.assertTrue(result.success)
        self.assertIsNotNone(ctx.thumbnail_path)

    def test_thumbnail_respects_dimensions(self):
        """Thumbnail should be resized within configured dimensions."""
        img_path = self.temp_dir / "large.png"
        img = Image.new("RGB", (2000, 3000), color="green")
        img.save(str(img_path))

        ctx = ProcessingContext(
            source_path=img_path,
            mime_type="image/png",
        )
        self.plugin.process(ctx)

        thumb = Image.open(str(ctx.thumbnail_path))
        self.assertLessEqual(thumb.width, 400)
        self.assertLessEqual(thumb.height, 560)

    def test_unsupported_mime_type_skips(self):
        """Unsupported MIME types should skip gracefully."""
        txt_path = self.temp_dir / "test.txt"
        txt_path.write_text("hello", encoding="utf-8")

        ctx = ProcessingContext(
            source_path=txt_path,
            mime_type="text/plain",
        )
        result = self.plugin.process(ctx)

        self.assertTrue(result.success)
        self.assertIn("skipped", result.message.lower())

    def test_thumbnail_from_jpeg(self):
        """Generate a thumbnail from a JPEG image."""
        img_path = self.temp_dir / "photo.jpg"
        img = Image.new("RGB", (500, 700), color="red")
        img.save(str(img_path), "JPEG")

        ctx = ProcessingContext(
            source_path=img_path,
            mime_type="image/jpeg",
        )
        result = self.plugin.process(ctx)

        self.assertTrue(result.success)
        self.assertIsNotNone(ctx.thumbnail_path)
