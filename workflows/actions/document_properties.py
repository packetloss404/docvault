"""Action to set document properties."""

from .base import WorkflowAction


class SetDocumentPropertiesAction(WorkflowAction):
    """
    Set properties on the workflow instance's document.

    Config keys:
    - title (str, optional): New title for the document.
    - language (str, optional): New language code.
    - document_type_id (int, optional): New document type ID.
    """

    def execute(self, instance, config):
        document = instance.document
        update_fields = []

        if "title" in config:
            document.title = config["title"]
            update_fields.append("title")

        if "language" in config:
            document.language = config["language"]
            update_fields.append("language")

        if "document_type_id" in config:
            document.document_type_id = config["document_type_id"]
            update_fields.append("document_type")

        if update_fields:
            document.save(update_fields=update_fields)

    def validate_config(self, config):
        errors = []
        if not any(k in config for k in ("title", "language", "document_type_id")):
            errors.append("At least one property must be specified.")
        return errors
