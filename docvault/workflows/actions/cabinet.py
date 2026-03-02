"""Action to assign a document to a cabinet."""

from .base import WorkflowAction


class AddToCabinetAction(WorkflowAction):
    """
    Set the cabinet on the workflow instance's document.

    Config keys:
    - cabinet_id (int): Cabinet ID to assign.
    """

    def execute(self, instance, config):
        cabinet_id = config.get("cabinet_id")
        if cabinet_id is not None:
            instance.document.cabinet_id = cabinet_id
            instance.document.save(update_fields=["cabinet"])

    def validate_config(self, config):
        errors = []
        if "cabinet_id" not in config:
            errors.append("'cabinet_id' is required.")
        return errors
