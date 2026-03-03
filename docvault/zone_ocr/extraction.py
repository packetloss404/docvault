"""
Zone OCR extraction helpers.

Provides template matching, field extraction, preprocessing, validation,
and custom field population utilities. Image-based OCR dependencies
(PIL, pytesseract) are lazily imported and gracefully degraded when
unavailable.
"""

import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .constants import (
    FIELD_BOOLEAN,
    FIELD_DATE,
    FIELD_FLOAT,
    FIELD_INTEGER,
    FIELD_MONETARY,
    FIELD_STRING,
    PREPROCESS_ALPHA_ONLY,
    PREPROCESS_CURRENCY_PARSE,
    PREPROCESS_DATE_PARSE,
    PREPROCESS_NONE,
    PREPROCESS_NUMERIC_ONLY,
)

logger = logging.getLogger(__name__)

# Common date formats to try when parsing dates
DATE_FORMATS = [
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%m-%d-%Y",
    "%d-%m-%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
    "%m.%d.%Y",
    "%d.%m.%Y",
]


def match_template(document, templates):
    """Select the best matching ZoneOCRTemplate for a document.

    Uses content-based heuristics when image matching is not available.
    Returns the first active template whose page_number is within the
    document's page_count, or None if no template matches.

    Args:
        document: A Document model instance (must have content, page_count).
        templates: QuerySet or iterable of ZoneOCRTemplate instances.

    Returns:
        The best matching ZoneOCRTemplate, or None.
    """
    from django.conf import settings

    threshold = getattr(settings, "ZONE_OCR_MATCH_THRESHOLD", 0.7)

    best_template = None
    best_score = 0.0

    for template in templates:
        # Basic eligibility: template page must exist in document
        if document.page_count and template.page_number > document.page_count:
            continue

        # Content-based scoring heuristic
        score = _score_template(document, template)
        if score >= threshold and score > best_score:
            best_score = score
            best_template = template

    # If no template exceeded the threshold, fall back to the first
    # eligible template (simple matching mode).
    if best_template is None and templates:
        for template in templates:
            if not document.page_count or template.page_number <= document.page_count:
                best_template = template
                break

    return best_template


def _score_template(document, template):
    """Score how well a template matches a document using content heuristics.

    Returns a float between 0.0 and 1.0.
    """
    if not document.content:
        return 0.0

    content_lower = document.content.lower()
    field_names = [f.name.lower() for f in template.fields.all()]

    if not field_names:
        return 0.5  # Template with no fields gets a neutral score

    # Count how many field names appear in the document content
    matches = sum(1 for name in field_names if name in content_lower)
    return matches / len(field_names)


def extract_field_value(image, bounding_box, field_type, preprocessing):
    """Extract a value from an image region using OCR.

    Attempts to use PIL and pytesseract for actual OCR. If those are
    not available, returns an empty result.

    Args:
        image: A PIL Image object, or None.
        bounding_box: Dict with keys x, y, width, height (as percentages 0-100).
        field_type: One of the FIELD_* constants.
        preprocessing: One of the PREPROCESS_* constants.

    Returns:
        Tuple of (extracted_value: str, confidence: float).
    """
    if image is None:
        return "", 0.0

    try:
        from PIL import Image  # noqa: F811

        # Crop the bounding box region
        img_width, img_height = image.size
        x = int(bounding_box.get("x", 0) / 100 * img_width)
        y = int(bounding_box.get("y", 0) / 100 * img_height)
        w = int(bounding_box.get("width", 100) / 100 * img_width)
        h = int(bounding_box.get("height", 100) / 100 * img_height)
        cropped = image.crop((x, y, x + w, y + h))

        # Try pytesseract
        try:
            import pytesseract

            ocr_data = pytesseract.image_to_data(
                cropped, output_type=pytesseract.Output.DICT,
            )
            texts = []
            confidences = []
            for i, text in enumerate(ocr_data.get("text", [])):
                text = text.strip()
                if text:
                    texts.append(text)
                    conf = ocr_data["conf"][i]
                    if isinstance(conf, (int, float)) and conf >= 0:
                        confidences.append(conf / 100.0)

            raw_value = " ".join(texts)
            avg_confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )

            cleaned = apply_preprocessing(raw_value, preprocessing)
            return cleaned, avg_confidence

        except ImportError:
            logger.debug("pytesseract not available, skipping image-based OCR")
            return "", 0.0
        except Exception as exc:
            logger.warning("pytesseract OCR failed: %s", exc)
            return "", 0.0

    except ImportError:
        logger.debug("PIL not available, skipping image-based OCR")
        return "", 0.0
    except Exception as exc:
        logger.warning("Image cropping failed: %s", exc)
        return "", 0.0


def extract_field_from_content(content, field_name, field_type, preprocessing):
    """Extract a field value from plain text content using heuristics.

    This is a fallback when image-based OCR is not available.
    Looks for patterns like "Field Name: value" or "Field Name value"
    in the document content.

    Args:
        content: Plain text content of the document.
        field_name: The name of the field to search for.
        field_type: One of the FIELD_* constants.
        preprocessing: One of the PREPROCESS_* constants.

    Returns:
        Tuple of (extracted_value: str, confidence: float).
    """
    if not content or not field_name:
        return "", 0.0

    # Build regex patterns to find the field value
    escaped_name = re.escape(field_name)
    patterns = [
        # "Field Name: value" or "Field Name : value"
        rf"(?i){escaped_name}\s*:\s*(.+?)(?:\n|$)",
        # "Field Name\tvalue"
        rf"(?i){escaped_name}\t+(.+?)(?:\n|$)",
        # "Field Name   value" (multiple spaces as separator)
        rf"(?i){escaped_name}\s{{2,}}(.+?)(?:\n|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            raw_value = match.group(1).strip()
            cleaned = apply_preprocessing(raw_value, preprocessing)
            # Content-based extraction gets moderate confidence
            confidence = 0.6
            if validate_value(cleaned, field_type, ""):
                confidence = 0.7
            return cleaned, confidence

    return "", 0.0


def apply_preprocessing(raw_value, preprocessing):
    """Apply a preprocessing step to the raw OCR text.

    Args:
        raw_value: The raw extracted text.
        preprocessing: One of the PREPROCESS_* constants.

    Returns:
        The cleaned value as a string.
    """
    if not raw_value:
        return raw_value

    if preprocessing == PREPROCESS_NONE:
        return raw_value.strip()

    if preprocessing == PREPROCESS_NUMERIC_ONLY:
        # Keep digits, decimal points, minus signs
        return re.sub(r"[^\d.\-]", "", raw_value)

    if preprocessing == PREPROCESS_ALPHA_ONLY:
        # Keep only alphabetic characters and spaces
        return re.sub(r"[^a-zA-Z\s]", "", raw_value).strip()

    if preprocessing == PREPROCESS_DATE_PARSE:
        return _parse_date(raw_value)

    if preprocessing == PREPROCESS_CURRENCY_PARSE:
        return _parse_currency(raw_value)

    return raw_value.strip()


def _parse_date(raw_value):
    """Attempt to parse a date string into ISO format (YYYY-MM-DD)."""
    cleaned = raw_value.strip()
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try extracting a date-like pattern from the string
    date_pattern = re.search(
        r"(\d{1,4}[-/.\s]\d{1,2}[-/.\s]\d{1,4})", cleaned,
    )
    if date_pattern:
        date_str = date_pattern.group(1)
        # Normalize separators to /
        normalized = re.sub(r"[-.\s]", "/", date_str)
        for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]:
            try:
                dt = datetime.strptime(normalized, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

    return cleaned


def _parse_currency(raw_value):
    """Extract a numeric value from a currency string.

    Examples: "$1,234.56" -> "1234.56", "EUR 100.00" -> "100.00"
    """
    # Remove currency symbols and whitespace
    cleaned = re.sub(r"[^\d.,\-]", "", raw_value)
    # Handle European format (1.234,56 -> 1234.56)
    if "," in cleaned and "." in cleaned:
        if cleaned.rindex(",") > cleaned.rindex("."):
            # European: periods are thousands, comma is decimal
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # US: commas are thousands, period is decimal
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Could be either thousands separator or decimal
        # If exactly 2 digits after the comma, treat as decimal
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) == 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    return cleaned


def validate_value(value, field_type, validation_regex):
    """Validate an extracted value against its expected type and optional regex.

    Args:
        value: The extracted string value.
        field_type: One of the FIELD_* constants.
        validation_regex: Optional regex pattern string.

    Returns:
        True if the value is valid, False otherwise.
    """
    if not value:
        return True  # Empty values are considered valid (field may be optional)

    # Check regex first
    if validation_regex:
        try:
            if not re.match(validation_regex, value):
                return False
        except re.error:
            logger.warning("Invalid validation regex: %s", validation_regex)

    # Type-specific validation
    if field_type == FIELD_INTEGER:
        try:
            int(value)
        except ValueError:
            return False

    elif field_type == FIELD_FLOAT:
        try:
            float(value)
        except ValueError:
            return False

    elif field_type == FIELD_MONETARY:
        try:
            Decimal(value)
        except (InvalidOperation, ValueError):
            return False

    elif field_type == FIELD_DATE:
        # Check if it looks like a date
        if not re.search(r"\d", value):
            return False

    elif field_type == FIELD_BOOLEAN:
        if value.lower() not in (
            "true", "false", "yes", "no", "1", "0",
            "t", "f", "y", "n",
        ):
            return False

    return True


def populate_custom_field(document, zone_field, extracted_value):
    """Create or update a CustomFieldInstance for the document.

    Maps the zone OCR extracted value to the linked CustomField,
    converting types as necessary.

    Args:
        document: The Document instance.
        zone_field: The ZoneOCRField instance (must have custom_field set).
        extracted_value: The string value to store.

    Returns:
        The created/updated CustomFieldInstance, or None on failure.
    """
    if not zone_field.custom_field:
        return None

    from organization.models.custom_field import (
        FIELD_TYPE_COLUMN_MAP,
        CustomFieldInstance,
    )

    custom_field = zone_field.custom_field
    column = FIELD_TYPE_COLUMN_MAP.get(custom_field.data_type, "value_text")

    try:
        instance, created = CustomFieldInstance.objects.get_or_create(
            document=document,
            field=custom_field,
        )

        # Convert the extracted value to the appropriate type
        converted_value = _convert_value(extracted_value, custom_field.data_type)
        setattr(instance, column, converted_value)
        instance.save()

        logger.info(
            "Populated custom field '%s' on document %d with value: %s",
            custom_field.name,
            document.pk,
            converted_value,
        )
        return instance

    except Exception as exc:
        logger.warning(
            "Failed to populate custom field '%s' on document %d: %s",
            custom_field.name,
            document.pk,
            exc,
        )
        return None


def _convert_value(value, data_type):
    """Convert a string value to the appropriate Python type for storage."""
    if not value:
        return None

    try:
        if data_type in ("string", "longtext", "url"):
            return str(value)
        elif data_type == "integer":
            return int(float(value))  # float first to handle "123.0"
        elif data_type == "float":
            return float(value)
        elif data_type == "monetary":
            return Decimal(value)
        elif data_type == "boolean":
            return value.lower() in ("true", "yes", "1", "t", "y")
        elif data_type == "date":
            from datetime import date as date_type

            # Try ISO format first
            try:
                return date_type.fromisoformat(value)
            except ValueError:
                # Try common formats
                for fmt in DATE_FORMATS:
                    try:
                        return datetime.strptime(value, fmt).date()
                    except ValueError:
                        continue
            return str(value)
        else:
            return str(value)
    except (ValueError, TypeError, InvalidOperation) as exc:
        logger.debug("Value conversion failed for %s (%s): %s", value, data_type, exc)
        return str(value)
