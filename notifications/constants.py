"""Constants for the notifications module."""

# Event types
EVENT_DOCUMENT_ADDED = "document_added"
EVENT_DOCUMENT_PROCESSED = "document_processed"
EVENT_PROCESSING_FAILED = "processing_failed"
EVENT_WORKFLOW_TRANSITION = "workflow_transition"
EVENT_COMMENT_ADDED = "comment_added"
EVENT_SHARE_ACCESSED = "share_accessed"
EVENT_RETENTION_WARNING = "retention_warning"
EVENT_QUOTA_WARNING = "quota_warning"

EVENT_TYPE_CHOICES = [
    (EVENT_DOCUMENT_ADDED, "Document Added"),
    (EVENT_DOCUMENT_PROCESSED, "Document Processed"),
    (EVENT_PROCESSING_FAILED, "Processing Failed"),
    (EVENT_WORKFLOW_TRANSITION, "Workflow Transition"),
    (EVENT_COMMENT_ADDED, "Comment Added"),
    (EVENT_SHARE_ACCESSED, "Share Accessed"),
    (EVENT_RETENTION_WARNING, "Retention Warning"),
    (EVENT_QUOTA_WARNING, "Quota Warning"),
]

ALL_EVENT_TYPES = [choice[0] for choice in EVENT_TYPE_CHOICES]

# Notification channels
CHANNEL_IN_APP = "in_app"
CHANNEL_EMAIL = "email"
CHANNEL_WEBHOOK = "webhook"

CHANNEL_CHOICES = [
    (CHANNEL_IN_APP, "In-App"),
    (CHANNEL_EMAIL, "Email"),
    (CHANNEL_WEBHOOK, "Webhook"),
]

ALL_CHANNELS = [choice[0] for choice in CHANNEL_CHOICES]
