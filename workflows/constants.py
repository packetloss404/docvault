"""Constants for the workflows module."""

# Action trigger timing
ON_ENTRY = "on_entry"
ON_EXIT = "on_exit"

ACTION_WHEN_CHOICES = [
    (ON_ENTRY, "On entry"),
    (ON_EXIT, "On exit"),
]

# Escalation time units
UNIT_MINUTES = "minutes"
UNIT_HOURS = "hours"
UNIT_DAYS = "days"
UNIT_WEEKS = "weeks"

ESCALATION_UNIT_CHOICES = [
    (UNIT_MINUTES, "Minutes"),
    (UNIT_HOURS, "Hours"),
    (UNIT_DAYS, "Days"),
    (UNIT_WEEKS, "Weeks"),
]

# Transition field types
FIELD_TYPE_CHAR = "char"
FIELD_TYPE_INTEGER = "integer"
FIELD_TYPE_DATE = "date"
FIELD_TYPE_BOOLEAN = "boolean"
FIELD_TYPE_TEXT = "text"
FIELD_TYPE_SELECT = "select"

FIELD_TYPE_CHOICES = [
    (FIELD_TYPE_CHAR, "Character"),
    (FIELD_TYPE_INTEGER, "Integer"),
    (FIELD_TYPE_DATE, "Date"),
    (FIELD_TYPE_BOOLEAN, "Boolean"),
    (FIELD_TYPE_TEXT, "Text"),
    (FIELD_TYPE_SELECT, "Select"),
]

# --------------------------------------------------------------------------
# Trigger-Action Rule constants (Sprint 11)
# --------------------------------------------------------------------------

# Trigger types
TRIGGER_CONSUMPTION = "consumption"
TRIGGER_DOCUMENT_ADDED = "document_added"
TRIGGER_DOCUMENT_UPDATED = "document_updated"
TRIGGER_SCHEDULED = "scheduled"

TRIGGER_TYPE_CHOICES = [
    (TRIGGER_CONSUMPTION, "Consumption"),
    (TRIGGER_DOCUMENT_ADDED, "Document Added"),
    (TRIGGER_DOCUMENT_UPDATED, "Document Updated"),
    (TRIGGER_SCHEDULED, "Scheduled"),
]

# Action types
ACTION_ADD_TAG = "add_tag"
ACTION_REMOVE_TAG = "remove_tag"
ACTION_SET_CORRESPONDENT = "set_correspondent"
ACTION_SET_TYPE = "set_document_type"
ACTION_SET_STORAGE_PATH = "set_storage_path"
ACTION_SET_CUSTOM_FIELD = "set_custom_field"
ACTION_ASSIGN_PERMISSIONS = "assign_permissions"
ACTION_SEND_EMAIL = "send_email"
ACTION_WEBHOOK = "webhook"
ACTION_LAUNCH_WORKFLOW = "launch_workflow"
ACTION_RUN_SCRIPT = "run_script"

ACTION_TYPE_CHOICES = [
    (ACTION_ADD_TAG, "Add Tag"),
    (ACTION_REMOVE_TAG, "Remove Tag"),
    (ACTION_SET_CORRESPONDENT, "Set Correspondent"),
    (ACTION_SET_TYPE, "Set Document Type"),
    (ACTION_SET_STORAGE_PATH, "Set Storage Path"),
    (ACTION_SET_CUSTOM_FIELD, "Set Custom Field"),
    (ACTION_ASSIGN_PERMISSIONS, "Assign Permissions"),
    (ACTION_SEND_EMAIL, "Send Email"),
    (ACTION_WEBHOOK, "Webhook"),
    (ACTION_LAUNCH_WORKFLOW, "Launch Workflow"),
    (ACTION_RUN_SCRIPT, "Run Script"),
]

# Matching algorithms for triggers
MATCH_NONE = 0
MATCH_ANY = 1
MATCH_ALL = 2
MATCH_LITERAL = 3
MATCH_REGEX = 4
MATCH_FUZZY = 5

MATCHING_ALGORITHM_CHOICES = [
    (MATCH_NONE, "None"),
    (MATCH_ANY, "Any word"),
    (MATCH_ALL, "All words"),
    (MATCH_LITERAL, "Exact match"),
    (MATCH_REGEX, "Regular expression"),
    (MATCH_FUZZY, "Fuzzy match"),
]
