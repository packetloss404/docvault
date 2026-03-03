"""Parser plugin - routes documents to the appropriate format parser."""

import logging

from processing.context import PluginResult, ProcessingContext
from processing.parsers.base import get_parser_for_mime_type

from .base import ProcessingPlugin

logger = logging.getLogger(__name__)


class ParserPlugin(ProcessingPlugin):
    """Route documents to format-specific parsers based on MIME type."""

    name = "Parser"
    order = 50

    def can_run(self, context: ProcessingContext) -> bool:
        return bool(context.mime_type)

    def process(self, context: ProcessingContext) -> PluginResult:
        parser = get_parser_for_mime_type(context.mime_type)
        if not parser:
            logger.info("No parser registered for MIME type: %s", context.mime_type)
            return PluginResult(
                success=True,
                message=f"No parser for {context.mime_type}, skipping text extraction",
            )

        logger.info(
            "Parsing %s with %s",
            context.original_filename,
            type(parser).__name__,
        )

        result = parser.parse(
            context.source_path, context.mime_type,
            context.language or "eng",
        )

        context.content = result.content
        if result.archive_path:
            context.archive_path = result.archive_path
        context.page_count = result.page_count
        if result.date and not context.date_created:
            context.date_created = result.date

        self.update_progress(context, 0.50, f"Parsed {context.original_filename}")
        return PluginResult(success=True)
