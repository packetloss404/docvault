"""Processing plugin for workflow consumption triggers."""

import logging

from processing.context import PluginResult, ProcessingContext
from processing.plugins.base import ProcessingPlugin

logger = logging.getLogger(__name__)


class WorkflowTriggerPlugin(ProcessingPlugin):
    """Match consumption triggers and apply overrides during document processing."""

    name = "WorkflowTriggerPlugin"
    order = 30  # After preflight (10), before pre-consume hook (40)

    def can_run(self, context: ProcessingContext) -> bool:
        return True

    def process(self, context: ProcessingContext) -> PluginResult:
        from workflows.constants import TRIGGER_CONSUMPTION
        from workflows.rules import apply_consumption_overrides, get_matching_rules

        try:
            rules = get_matching_rules(
                TRIGGER_CONSUMPTION, document=None, context=context
            )
            if rules:
                apply_consumption_overrides(rules, context)
                logger.info("Applied %d consumption rule(s)", len(rules))
        except Exception:
            logger.exception("Error applying consumption triggers")

        return PluginResult(success=True)
