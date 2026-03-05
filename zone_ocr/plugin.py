"""Zone OCR plugin for the document processing pipeline."""

import logging

from processing.context import PluginResult, ProcessingContext
from processing.plugins.base import ProcessingPlugin

logger = logging.getLogger(__name__)


class ZoneOCRPlugin(ProcessingPlugin):
    """Zone-based OCR extraction plugin.

    Runs after document storage and classification (order=107) to extract
    structured field values from predefined page regions. Results are
    stored as ZoneOCRResult records and optionally mapped to CustomField
    instances.

    The plugin gracefully degrades when image processing libraries
    (PIL, pytesseract) are not available, falling back to content-based
    extraction using text heuristics.
    """

    name = "ZoneOCRPlugin"
    order = 107

    def can_run(self, context: ProcessingContext) -> bool:
        """Only run if active templates exist and we have a stored document with content."""
        if not context.document_id:
            return False
        if not context.content:
            return False

        from .models import ZoneOCRTemplate

        return ZoneOCRTemplate.objects.filter(is_active=True).exists()

    def process(self, context: ProcessingContext) -> PluginResult:
        self.update_progress(context, 0.78, "Running zone OCR extraction...")

        from documents.models import Document

        from .extraction import (
            apply_preprocessing,
            extract_field_from_content,
            extract_field_value,
            match_template,
            populate_custom_field,
            validate_value,
        )
        from .models import ZoneOCRResult, ZoneOCRTemplate

        try:
            document = Document.objects.get(pk=context.document_id)
        except Document.DoesNotExist:
            return PluginResult(
                success=False,
                message=f"Document {context.document_id} not found",
            )

        templates = ZoneOCRTemplate.objects.filter(
            is_active=True,
        ).prefetch_related("fields", "fields__custom_field")

        if not templates.exists():
            return PluginResult(
                success=True,
                message="No active zone OCR templates",
            )

        # Find the best matching template
        template = match_template(document, templates)
        if template is None:
            logger.debug("No matching zone OCR template for document %d", document.pk)
            return PluginResult(
                success=True,
                message="No matching template found",
            )

        logger.info(
            "Matched zone OCR template '%s' for document %d",
            template.name,
            document.pk,
        )

        # Try image-based extraction first, fall back to content-based
        page_image = self._load_page_image(context, template.page_number)

        results_created = 0
        fields_with_errors = 0

        for zone_field in template.fields.all():
            try:
                extracted_value = ""
                confidence = 0.0

                # Attempt image-based OCR if we have a page image
                if page_image is not None:
                    extracted_value, confidence = extract_field_value(
                        image=page_image,
                        bounding_box=zone_field.bounding_box,
                        field_type=zone_field.field_type,
                        preprocessing=zone_field.preprocessing,
                    )

                # Fall back to content-based extraction
                if not extracted_value and context.content:
                    extracted_value, confidence = extract_field_from_content(
                        content=context.content,
                        field_name=zone_field.name,
                        field_type=zone_field.field_type,
                        preprocessing=zone_field.preprocessing,
                    )

                # Validate the extracted value
                is_valid = validate_value(
                    extracted_value,
                    zone_field.field_type,
                    zone_field.validation_regex,
                )

                if not is_valid:
                    logger.warning(
                        "Extracted value '%s' failed validation for field '%s'",
                        extracted_value,
                        zone_field.name,
                    )
                    confidence *= 0.5  # Reduce confidence for invalid values

                # Store the result
                result, created = ZoneOCRResult.objects.update_or_create(
                    document=document,
                    template=template,
                    field=zone_field,
                    defaults={
                        "extracted_value": extracted_value,
                        "confidence": confidence,
                        "reviewed": False,
                    },
                )

                if created:
                    results_created += 1

                # Populate custom field if mapped and confidence is sufficient
                from django.conf import settings

                confidence_threshold = getattr(
                    settings, "ZONE_OCR_CONFIDENCE_THRESHOLD", 0.8,
                )
                if (
                    zone_field.custom_field
                    and extracted_value
                    and confidence >= confidence_threshold
                    and is_valid
                ):
                    populate_custom_field(document, zone_field, extracted_value)

            except Exception as exc:
                fields_with_errors += 1
                logger.warning(
                    "Error extracting field '%s' for document %d: %s",
                    zone_field.name,
                    document.pk,
                    exc,
                )

        message = (
            f"Zone OCR complete: template='{template.name}', "
            f"results={results_created}, errors={fields_with_errors}"
        )
        logger.info(message)

        return PluginResult(
            success=fields_with_errors == 0,
            message=message,
        )

    def _load_page_image(self, context, page_number):
        """Attempt to load a page image for OCR.

        Tries to render the source document's page as an image using
        available libraries. Returns a PIL Image or None.
        """
        if not context.source_path:
            return None

        try:
            from PIL import Image

            source = str(context.source_path)

            # If the source is an image file, load it directly
            if context.mime_type and context.mime_type.startswith("image/"):
                return Image.open(source)

            # Try pdf2image for PDF files
            if context.mime_type == "application/pdf":
                try:
                    from pdf2image import convert_from_path

                    images = convert_from_path(
                        source,
                        first_page=page_number,
                        last_page=page_number,
                        dpi=300,
                    )
                    if images:
                        return images[0]
                except ImportError:
                    logger.debug("pdf2image not available for page rendering")
                except Exception as exc:
                    logger.debug("pdf2image rendering failed: %s", exc)

        except ImportError:
            logger.debug("PIL not available, skipping image loading")
        except Exception as exc:
            logger.debug("Failed to load page image: %s", exc)

        return None
