"""Processing configuration (OCR settings, etc.)."""

from dataclasses import dataclass

from django.conf import settings


@dataclass
class OCRConfig:
    """Configuration for OCRmyPDF."""

    language: str = "eng"
    mode: str = "skip"  # 'skip', 'redo', 'force'
    output_type: str = "pdfa"  # 'pdfa' or 'pdf'
    image_dpi: int = 300
    deskew: bool = True
    rotate: bool = True
    clean: str = "clean"  # 'none', 'clean', 'finalize'
    max_image_pixels: int = 256_000_000
    pages: int = 0  # 0 = all pages


def get_ocr_config() -> OCRConfig:
    """Build OCR config from Django settings."""
    return OCRConfig(
        language=getattr(settings, "OCR_LANGUAGE", "eng"),
        mode=getattr(settings, "OCR_MODE", "skip"),
        output_type=getattr(settings, "OCR_OUTPUT_TYPE", "pdfa"),
        image_dpi=getattr(settings, "OCR_IMAGE_DPI", 300),
        deskew=getattr(settings, "OCR_DESKEW", True),
        rotate=getattr(settings, "OCR_ROTATE", True),
        clean=getattr(settings, "OCR_CLEAN", "clean"),
    )
