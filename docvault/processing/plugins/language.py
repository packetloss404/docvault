"""Language detection plugin."""

import logging

from processing.context import PluginResult, ProcessingContext

from .base import ProcessingPlugin

logger = logging.getLogger(__name__)


class LanguageDetectionPlugin(ProcessingPlugin):
    """Detect document language from extracted text content."""

    name = "LanguageDetection"
    order = 60

    def can_run(self, context: ProcessingContext) -> bool:
        return bool(context.content) and not context.language

    def process(self, context: ProcessingContext) -> PluginResult:
        try:
            from langdetect import detect
            # Use first 5000 chars for performance
            context.language = detect(context.content[:5000])
        except Exception:
            context.language = "en"
            logger.debug("Language detection failed, defaulting to 'en'")

        self.update_progress(
            context, 0.60,
            f"Detected language: {context.language}",
        )
        return PluginResult(success=True)
