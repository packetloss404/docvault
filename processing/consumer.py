"""Document consumer - orchestrates the processing pipeline."""

import logging

from .context import ProcessingContext

logger = logging.getLogger(__name__)


class DocumentConsumer:
    """Orchestrates document processing via an ordered plugin chain."""

    def __init__(self):
        self.plugins = self._discover_plugins()

    def _discover_plugins(self) -> list:
        """Discover and instantiate plugins sorted by order."""
        from .plugins.date_extraction import DateExtractionPlugin
        from .plugins.hooks import PostConsumeHookPlugin, PreConsumeHookPlugin
        from .plugins.language import LanguageDetectionPlugin
        from .plugins.parser import ParserPlugin
        from .plugins.preflight import PreflightPlugin
        from .plugins.store import StorePlugin
        from .plugins.thumbnail import ThumbnailPlugin
        from ai.plugin import AIPlugin
        from ml.plugin import ClassificationPlugin
        from workflows.plugins import WorkflowTriggerPlugin

        from .plugins.barcode import BarcodePlugin
        from entities.plugin import NERPlugin
        from zone_ocr.plugin import ZoneOCRPlugin

        plugin_classes = [
            PreflightPlugin,         # order=10
            BarcodePlugin,           # order=20
            WorkflowTriggerPlugin,   # order=30
            PreConsumeHookPlugin,    # order=40
            ParserPlugin,            # order=50
            LanguageDetectionPlugin, # order=60
            DateExtractionPlugin,    # order=70
            StorePlugin,             # order=90
            ClassificationPlugin,   # order=100
            ZoneOCRPlugin,           # order=107
            AIPlugin,               # order=110
            NERPlugin,              # order=115
            ThumbnailPlugin,         # order=130
            PostConsumeHookPlugin,   # order=140
        ]
        return sorted(plugin_classes, key=lambda cls: cls.order)

    def consume(self, context: ProcessingContext) -> ProcessingContext:
        """Run all applicable plugins on the document."""
        logger.info(
            "Starting document consumption: %s",
            context.original_filename,
        )

        for plugin_class in self.plugins:
            plugin = plugin_class()
            if not plugin.can_run(context):
                logger.debug("Skipping plugin %s (can_run=False)", plugin.name)
                continue

            logger.info("Running plugin: %s", plugin.name)
            plugin.setup(context)
            try:
                result = plugin.process(context)
                if not result.success:
                    context.errors.append(f"{plugin.name}: {result.message}")
                    logger.warning("Plugin %s failed: %s", plugin.name, result.message)
                if result.should_stop:
                    logger.info("Plugin %s requested pipeline stop", plugin.name)
                    break
            except Exception as e:
                context.errors.append(f"{plugin.name}: {e}")
                logger.exception("Plugin %s raised an exception", plugin.name)
                raise
            finally:
                plugin.cleanup(context)

        logger.info(
            "Document consumption complete: %s (errors: %d)",
            context.original_filename,
            len(context.errors),
        )
        return context
