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

FIELD_TYPE_CHOICES = [
    (FIELD_TYPE_CHAR, "Character"),
    (FIELD_TYPE_INTEGER, "Integer"),
    (FIELD_TYPE_DATE, "Date"),
    (FIELD_TYPE_BOOLEAN, "Boolean"),
    (FIELD_TYPE_TEXT, "Text"),
]
