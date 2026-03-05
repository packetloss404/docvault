"""Action to launch another workflow."""

import logging

from .base import WorkflowAction

logger = logging.getLogger(__name__)

# Guard against infinite recursion
_LAUNCH_DEPTH = 0
MAX_LAUNCH_DEPTH = 5


class LaunchWorkflowAction(WorkflowAction):
    """
    Launch another workflow for the same document.

    Config keys:
    - workflow_template_id (int): WorkflowTemplate ID to launch.
    """

    def execute(self, instance, config):
        global _LAUNCH_DEPTH

        from workflows.models import WorkflowTemplate

        template_id = config.get("workflow_template_id")
        if not template_id:
            return

        if _LAUNCH_DEPTH >= MAX_LAUNCH_DEPTH:
            logger.warning(
                "Maximum workflow launch depth (%d) reached. "
                "Skipping launch of template %s for document %s.",
                MAX_LAUNCH_DEPTH,
                template_id,
                instance.document_id,
            )
            return

        try:
            template = WorkflowTemplate.objects.get(pk=template_id)
        except WorkflowTemplate.DoesNotExist:
            logger.warning("Workflow template %s not found.", template_id)
            return

        from workflows.engine import launch

        _LAUNCH_DEPTH += 1
        try:
            launch(instance.document, template)
        finally:
            _LAUNCH_DEPTH -= 1

    def validate_config(self, config):
        errors = []
        if "workflow_template_id" not in config:
            errors.append("'workflow_template_id' is required.")
        return errors
