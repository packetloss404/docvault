"""Action to set document metadata."""

from .base import WorkflowAction


class SetMetadataAction(WorkflowAction):
    """
    Set or update metadata on the workflow instance's document.

    Config keys:
    - metadata_type_id (int): MetadataType ID.
    - value (str): Metadata value.
    """

    def execute(self, instance, config):
        from organization.models import DocumentMetadata

        metadata_type_id = config.get("metadata_type_id")
        value = config.get("value", "")

        if metadata_type_id is not None:
            DocumentMetadata.objects.update_or_create(
                document=instance.document,
                metadata_type_id=metadata_type_id,
                defaults={"value": value},
            )

    def validate_config(self, config):
        errors = []
        if "metadata_type_id" not in config:
            errors.append("'metadata_type_id' is required.")
        return errors
