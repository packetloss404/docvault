"""Action to add tags to a document."""

from .base import WorkflowAction


class AddTagAction(WorkflowAction):
    """
    Add tags to the workflow instance's document.

    Config keys:
    - tag_ids (list[int]): List of tag IDs to add.
    """

    def execute(self, instance, config):
        tag_ids = config.get("tag_ids", [])
        if tag_ids:
            instance.document.tags.add(*tag_ids)

    def validate_config(self, config):
        errors = []
        if "tag_ids" not in config:
            errors.append("'tag_ids' is required.")
        elif not isinstance(config["tag_ids"], list):
            errors.append("'tag_ids' must be a list.")
        return errors
