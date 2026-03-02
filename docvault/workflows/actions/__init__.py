"""Built-in workflow action backends registry."""

BUILTIN_ACTIONS = {
    "workflows.actions.document_properties.SetDocumentPropertiesAction": {
        "label": "Set Document Properties",
        "description": "Set title, language, or document type on the document.",
    },
    "workflows.actions.tags.AddTagAction": {
        "label": "Add Tags",
        "description": "Add tags to the document.",
    },
    "workflows.actions.cabinet.AddToCabinetAction": {
        "label": "Add to Cabinet",
        "description": "Assign the document to a cabinet.",
    },
    "workflows.actions.metadata.SetMetadataAction": {
        "label": "Set Metadata",
        "description": "Set or update a metadata value on the document.",
    },
    "workflows.actions.launch_workflow.LaunchWorkflowAction": {
        "label": "Launch Workflow",
        "description": "Launch another workflow for the same document.",
    },
    "workflows.actions.email.SendEmailAction": {
        "label": "Send Email",
        "description": "Send an email notification.",
    },
    "workflows.actions.webhook.WebhookAction": {
        "label": "Send Webhook",
        "description": "Send an HTTP webhook request.",
    },
}
