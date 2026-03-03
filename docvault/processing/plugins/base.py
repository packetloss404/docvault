"""Base class for document processing plugins."""

import logging
from abc import ABC, abstractmethod

from processing.context import PluginResult, ProcessingContext

logger = logging.getLogger(__name__)


class ProcessingPlugin(ABC):
    """Abstract base class for document processing plugins.

    Plugins are executed in order by the DocumentConsumer.
    Each plugin receives and can modify the ProcessingContext.
    """

    name: str = "BasePlugin"
    order: int = 0

    @abstractmethod
    def can_run(self, context: ProcessingContext) -> bool:
        """Check if this plugin should run for the given context."""

    @abstractmethod
    def process(self, context: ProcessingContext) -> PluginResult:
        """Execute plugin logic. May modify context."""

    def setup(self, context: ProcessingContext) -> None:
        """Optional setup before processing."""

    def cleanup(self, context: ProcessingContext) -> None:
        """Optional cleanup after processing."""

    def update_progress(self, context: ProcessingContext, progress: float, message: str) -> None:
        """Update progress on the processing context."""
        context.progress = progress
        context.status_message = message
        logger.debug("%s: %.0f%% - %s", self.name, progress * 100, message)
