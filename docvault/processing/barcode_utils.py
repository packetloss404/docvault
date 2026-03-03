"""Barcode scanning and processing utilities.

Uses zxing-cpp for barcode detection on PDF pages. Supports:
- Document splitting via separator barcodes
- ASN (Archive Serial Number) extraction
- Tag extraction from barcode content
"""

import logging
import re
import tempfile
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

# Default configuration (overridden by settings)
DEFAULT_SEPARATOR_BARCODE = "PATCH T"
DEFAULT_ASN_PREFIX = "ASN"
DEFAULT_BARCODE_DPI = 300
DEFAULT_MAX_PAGES = 5
DEFAULT_UPSCALE = 2.0

# Supported barcode formats for zxing-cpp
SUPPORTED_FORMATS = {
    "Code128", "QRCode", "UPCA", "UPCE",
    "EAN8", "EAN13", "DataMatrix",
}


def get_barcode_settings():
    """Get barcode configuration from Django settings."""
    return {
        "separator_barcode": getattr(
            settings, "BARCODE_SEPARATOR", DEFAULT_SEPARATOR_BARCODE
        ),
        "asn_prefix": getattr(settings, "BARCODE_ASN_PREFIX", DEFAULT_ASN_PREFIX),
        "dpi": getattr(settings, "BARCODE_DPI", DEFAULT_BARCODE_DPI),
        "max_pages": getattr(settings, "BARCODE_MAX_PAGES", DEFAULT_MAX_PAGES),
        "upscale": getattr(settings, "BARCODE_UPSCALE", DEFAULT_UPSCALE),
        "tag_mapping": getattr(settings, "BARCODE_TAG_MAPPING", {}),
        "retain_separator_pages": getattr(
            settings, "BARCODE_RETAIN_SEPARATOR_PAGES", False
        ),
        "enabled": getattr(settings, "BARCODE_ENABLED", True),
    }


def scan_page_for_barcodes(image):
    """Scan a single page image for barcodes using zxing-cpp.

    Args:
        image: PIL Image object.

    Returns:
        List of dicts with 'text' and 'format' keys.
    """
    try:
        import zxingcpp
    except ImportError:
        logger.warning("zxing-cpp not installed, barcode scanning disabled")
        return []

    try:
        results = zxingcpp.read_barcodes(image)
        return [
            {"text": r.text, "format": r.format.name}
            for r in results
        ]
    except Exception:
        logger.exception("Barcode scanning failed for page")
        return []


def scan_pdf_for_barcodes(pdf_path, max_pages=None, dpi=None):
    """Scan a PDF file for barcodes on each page.

    Args:
        pdf_path: Path to the PDF file.
        max_pages: Maximum number of pages to scan.
        dpi: DPI for PDF to image conversion.

    Returns:
        Dict mapping page number (0-indexed) to list of barcode results.
    """
    conf = get_barcode_settings()
    max_pages = max_pages or conf["max_pages"]
    dpi = dpi or conf["dpi"]

    try:
        from pdf2image import convert_from_path
    except ImportError:
        logger.warning("pdf2image not installed, barcode scanning disabled")
        return {}

    try:
        images = convert_from_path(
            str(pdf_path),
            dpi=dpi,
            first_page=1,
            last_page=max_pages,
        )
    except Exception:
        logger.exception("Failed to convert PDF to images for barcode scanning")
        return {}

    page_barcodes = {}
    for page_num, image in enumerate(images):
        barcodes = scan_page_for_barcodes(image)
        if barcodes:
            page_barcodes[page_num] = barcodes
            logger.debug(
                "Page %d: found %d barcode(s): %s",
                page_num, len(barcodes),
                [b["text"] for b in barcodes],
            )

    return page_barcodes


def find_separator_pages(page_barcodes, separator_string=None):
    """Find pages containing separator barcodes.

    Args:
        page_barcodes: Dict mapping page number to barcode results.
        separator_string: The separator barcode text to look for.

    Returns:
        Sorted list of page numbers containing separator barcodes.
    """
    conf = get_barcode_settings()
    separator = separator_string or conf["separator_barcode"]

    separator_pages = []
    for page_num, barcodes in page_barcodes.items():
        for barcode in barcodes:
            if barcode["text"].strip() == separator:
                separator_pages.append(page_num)
                break

    return sorted(separator_pages)


def split_pdf_at_separators(pdf_path, separator_pages, retain_separators=None):
    """Split a PDF at separator pages into multiple segments.

    Args:
        pdf_path: Path to the original PDF.
        separator_pages: List of page numbers where separators were found.
        retain_separators: Whether to keep separator pages in output.

    Returns:
        List of Paths to the split PDF segments.
    """
    conf = get_barcode_settings()
    retain = retain_separators if retain_separators is not None else conf["retain_separator_pages"]

    if not separator_pages:
        return [pdf_path]

    try:
        import pikepdf
    except ImportError:
        logger.warning("pikepdf not installed, document splitting disabled")
        return [pdf_path]

    try:
        src = pikepdf.open(str(pdf_path))
    except Exception:
        logger.exception("Failed to open PDF for splitting")
        return [pdf_path]

    total_pages = len(src.pages)
    separator_set = set(separator_pages)

    # Build segments: ranges of pages between separators
    segments = []
    current_start = 0

    for sep_page in sorted(separator_pages):
        if current_start < sep_page:
            segments.append((current_start, sep_page))
        if retain:
            segments.append((sep_page, sep_page + 1))
        current_start = sep_page + 1

    # Last segment after final separator
    if current_start < total_pages:
        segments.append((current_start, total_pages))

    if not segments:
        src.close()
        return [pdf_path]

    # Write each segment to a temp file
    output_paths = []
    temp_dir = Path(tempfile.mkdtemp(prefix="docvault_split_"))
    for i, (start, end) in enumerate(segments):
        pages_to_include = []
        for p in range(start, end):
            if not retain and p in separator_set:
                continue
            pages_to_include.append(p)

        if not pages_to_include:
            continue

        out_pdf = pikepdf.new()
        for p in pages_to_include:
            out_pdf.pages.append(src.pages[p])

        out_path = temp_dir / f"segment_{i:03d}.pdf"
        out_pdf.save(str(out_path))
        out_pdf.close()
        output_paths.append(out_path)

    src.close()
    return output_paths


def extract_asn(page_barcodes, asn_prefix=None):
    """Extract Archive Serial Number from barcodes.

    Looks for barcodes starting with the ASN prefix followed by
    a numeric value.

    Args:
        page_barcodes: Dict mapping page number to barcode results.
        asn_prefix: The prefix to look for (e.g., "ASN").

    Returns:
        The extracted ASN integer, or None if not found.
    """
    conf = get_barcode_settings()
    prefix = asn_prefix or conf["asn_prefix"]
    pattern = re.compile(rf"^{re.escape(prefix)}\s*(\d+)$", re.IGNORECASE)

    for _page_num, barcodes in sorted(page_barcodes.items()):
        for barcode in barcodes:
            match = pattern.match(barcode["text"].strip())
            if match:
                return int(match.group(1))

    return None


def extract_tags(page_barcodes, tag_mapping=None):
    """Extract tags from barcodes using configurable mapping.

    Args:
        page_barcodes: Dict mapping page number to barcode results.
        tag_mapping: Dict mapping regex patterns to tag names.
                     e.g., {"^TAG:(.+)$": "\\1", "^INVOICE$": "invoice"}

    Returns:
        Set of tag names extracted from barcodes.
    """
    conf = get_barcode_settings()
    mapping = tag_mapping or conf["tag_mapping"]

    if not mapping:
        return set()

    tags = set()
    for _page_num, barcodes in page_barcodes.items():
        for barcode in barcodes:
            text = barcode["text"].strip()
            for pattern, replacement in mapping.items():
                try:
                    match = re.match(pattern, text, re.IGNORECASE)
                    if match:
                        tag_name = match.expand(replacement)
                        if tag_name:
                            tags.add(tag_name)
                except re.error:
                    logger.warning("Invalid tag mapping regex: %s", pattern)

    return tags


def get_next_asn():
    """Get the next available Archive Serial Number.

    Returns:
        The next ASN (max existing + 1), or 1 if none exist.
    """
    from documents.models import Document

    result = Document.all_objects.order_by("-archive_serial_number").values_list(
        "archive_serial_number", flat=True
    ).first()

    if result is None:
        return 1
    return result + 1
