"""Barcode plugin - detects barcodes, splits documents, extracts ASN and tags."""

import logging

from processing.context import PluginResult, ProcessingContext

from .base import ProcessingPlugin

logger = logging.getLogger(__name__)


class BarcodePlugin(ProcessingPlugin):
    """Barcode detection and processing plugin.

    Order 20: runs after preflight (10) but before workflow triggers (30).

    Responsibilities:
    1. Scan PDF pages for barcodes
    2. If separator barcodes found: split document, submit segments
    3. Extract ASN from barcode content
    4. Extract tags from barcode content
    """

    name = "BarcodePlugin"
    order = 20

    def can_run(self, context: ProcessingContext) -> bool:
        """Only run on PDF files that have a source path."""
        from processing.barcode_utils import get_barcode_settings

        conf = get_barcode_settings()
        if not conf["enabled"]:
            return False

        if not context.source_path or not context.source_path.is_file():
            return False

        # Only scan PDFs (barcodes are extracted from rendered pages)
        mime = context.mime_type or ""
        return mime in (
            "application/pdf",
            "image/png", "image/jpeg", "image/tiff",
            "image/bmp", "image/gif",
        )

    def process(self, context: ProcessingContext) -> PluginResult:
        from processing.barcode_utils import (
            extract_asn,
            extract_tags,
            find_separator_pages,
            get_barcode_settings,
            scan_page_for_barcodes,
            scan_pdf_for_barcodes,
            split_pdf_at_separators,
        )

        self.update_progress(context, 0.03, "Scanning for barcodes...")
        conf = get_barcode_settings()

        # Scan for barcodes
        if context.mime_type == "application/pdf":
            page_barcodes = scan_pdf_for_barcodes(context.source_path)
        else:
            # For images, scan directly
            try:
                from PIL import Image
                img = Image.open(context.source_path)
                barcodes = scan_page_for_barcodes(img)
                page_barcodes = {0: barcodes} if barcodes else {}
            except Exception:
                logger.exception("Failed to scan image for barcodes")
                page_barcodes = {}

        if not page_barcodes:
            return PluginResult(success=True, message="No barcodes found")

        total_barcodes = sum(len(v) for v in page_barcodes.values())
        logger.info("Found %d barcode(s) across %d page(s)",
                     total_barcodes, len(page_barcodes))

        # 1. Check for separator barcodes → document splitting
        separator_pages = find_separator_pages(page_barcodes)
        if separator_pages and context.mime_type == "application/pdf":
            segments = split_pdf_at_separators(
                context.source_path, separator_pages
            )
            if len(segments) > 1:
                # Submit additional segments as new documents
                self._submit_split_segments(segments[1:], context)
                # Continue processing with the first segment
                context.source_path = segments[0]
                logger.info(
                    "Document split into %d segments at separator pages %s",
                    len(segments), separator_pages,
                )

        # 2. Extract ASN
        if not context.override_asn:
            asn = extract_asn(page_barcodes)
            if asn is not None:
                # Check for duplicate ASN
                from documents.models import Document
                if not Document.all_objects.filter(
                    archive_serial_number=asn
                ).exists():
                    context.override_asn = asn
                    logger.info("Extracted ASN from barcode: %d", asn)
                else:
                    logger.warning(
                        "ASN %d already exists, skipping assignment", asn
                    )

        # 3. Extract tags
        tag_names = extract_tags(page_barcodes)
        if tag_names:
            from organization.models import Tag
            tag_ids = []
            for name in tag_names:
                tag, _created = Tag.objects.get_or_create(
                    name=name,
                    defaults={"slug": name.lower().replace(" ", "-"), "color": "#6b7280"},
                )
                tag_ids.append(tag.pk)

            if context.override_tags:
                context.override_tags.extend(tag_ids)
            else:
                context.override_tags = tag_ids
            logger.info("Extracted tags from barcodes: %s", tag_names)

        return PluginResult(
            success=True,
            message=f"Processed {total_barcodes} barcode(s)",
        )

    def _submit_split_segments(self, segment_paths, context):
        """Submit split document segments as new processing tasks."""
        from processing.tasks import consume_document

        for i, segment_path in enumerate(segment_paths):
            logger.info(
                "Submitting split segment %d: %s",
                i + 1, segment_path,
            )
            from processing.models import ProcessingTask
            task = ProcessingTask.objects.create(
                task_name="document_consumption",
                status_message=f"Split segment {i + 1} from {context.original_filename}",
            )
            consume_document.delay(
                source_path=str(segment_path),
                original_filename=f"{context.original_filename}_segment_{i + 1}",
                task_id=str(task.task_id),
                user_id=context.user_id,
            )
