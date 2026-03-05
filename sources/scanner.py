"""SANE scanner integration for document ingestion."""

import io
import logging

logger = logging.getLogger(__name__)

_sane_available = None


def is_sane_available():
    """Check if SANE library is available."""
    global _sane_available
    if _sane_available is not None:
        return _sane_available

    try:
        import sane
        sane.init()
        _sane_available = True
    except (ImportError, Exception):
        _sane_available = False
    return _sane_available


def reset_sane():
    """Reset SANE availability check (for testing)."""
    global _sane_available
    _sane_available = None


def discover_scanners():
    """Discover available SANE scanners.

    Returns a list of dicts with scanner info.
    """
    if not is_sane_available():
        return []

    import sane

    try:
        devices = sane.get_devices()
        return [
            {
                "id": dev[0],
                "vendor": dev[1],
                "model": dev[2],
                "type": dev[3],
                "label": f"{dev[1]} {dev[2]}",
            }
            for dev in devices
        ]
    except Exception:
        logger.exception("Failed to discover SANE scanners")
        return []


def scan_document(device_id, dpi=300, color_mode="color", paper_size="a4"):
    """Scan a document from a SANE scanner.

    Returns the scanned image as PNG bytes, or None on failure.
    """
    if not is_sane_available():
        raise RuntimeError("SANE library not available")

    import sane

    try:
        scanner = sane.open(device_id)
    except Exception:
        logger.exception("Failed to open scanner: %s", device_id)
        raise RuntimeError(f"Cannot open scanner: {device_id}")

    try:
        # Set scanner options
        try:
            scanner.resolution = dpi
        except Exception:
            pass

        try:
            scanner.mode = color_mode
        except Exception:
            pass

        # Scan
        image = scanner.snap()

        # Convert to PNG bytes
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()

    except Exception:
        logger.exception("Scan failed on device %s", device_id)
        raise RuntimeError(f"Scan failed: {device_id}")
    finally:
        scanner.close()
