"""Constants for the e-signatures app."""

# ---------------------------------------------------------------------------
# Signature Request status
# ---------------------------------------------------------------------------
REQUEST_DRAFT = "draft"
REQUEST_SENT = "sent"
REQUEST_IN_PROGRESS = "in_progress"
REQUEST_COMPLETED = "completed"
REQUEST_CANCELLED = "cancelled"
REQUEST_EXPIRED = "expired"

REQUEST_STATUS_CHOICES = [
    (REQUEST_DRAFT, "Draft"),
    (REQUEST_SENT, "Sent"),
    (REQUEST_IN_PROGRESS, "In Progress"),
    (REQUEST_COMPLETED, "Completed"),
    (REQUEST_CANCELLED, "Cancelled"),
    (REQUEST_EXPIRED, "Expired"),
]

# ---------------------------------------------------------------------------
# Signing order
# ---------------------------------------------------------------------------
ORDER_SEQUENTIAL = "sequential"
ORDER_PARALLEL = "parallel"

SIGNING_ORDER_CHOICES = [
    (ORDER_SEQUENTIAL, "Sequential"),
    (ORDER_PARALLEL, "Parallel"),
]

# ---------------------------------------------------------------------------
# Signer status
# ---------------------------------------------------------------------------
SIGNER_PENDING = "pending"
SIGNER_VIEWED = "viewed"
SIGNER_SIGNED = "signed"
SIGNER_DECLINED = "declined"

SIGNER_STATUS_CHOICES = [
    (SIGNER_PENDING, "Pending"),
    (SIGNER_VIEWED, "Viewed"),
    (SIGNER_SIGNED, "Signed"),
    (SIGNER_DECLINED, "Declined"),
]

# ---------------------------------------------------------------------------
# Signature field types
# ---------------------------------------------------------------------------
FIELD_SIGNATURE = "signature"
FIELD_INITIALS = "initials"
FIELD_DATE = "date"
FIELD_TEXT = "text"
FIELD_CHECKBOX = "checkbox"

FIELD_TYPE_CHOICES = [
    (FIELD_SIGNATURE, "Signature"),
    (FIELD_INITIALS, "Initials"),
    (FIELD_DATE, "Date"),
    (FIELD_TEXT, "Text"),
    (FIELD_CHECKBOX, "Checkbox"),
]

# ---------------------------------------------------------------------------
# Verification methods
# ---------------------------------------------------------------------------
VERIFY_EMAIL = "email"
VERIFY_SMS = "sms"
VERIFY_NONE = "none"

VERIFICATION_METHOD_CHOICES = [
    (VERIFY_EMAIL, "Email"),
    (VERIFY_SMS, "SMS"),
    (VERIFY_NONE, "None"),
]

# ---------------------------------------------------------------------------
# Audit event types
# ---------------------------------------------------------------------------
EVENT_CREATED = "created"
EVENT_SENT = "sent"
EVENT_VIEWED = "viewed"
EVENT_PAGE_VIEWED = "page_viewed"
EVENT_SIGNED = "signed"
EVENT_DECLINED = "declined"
EVENT_COMPLETED = "completed"
EVENT_CANCELLED = "cancelled"
EVENT_EXPIRED = "expired"
EVENT_REMINDER_SENT = "reminder_sent"

AUDIT_EVENT_TYPE_CHOICES = [
    (EVENT_CREATED, "Created"),
    (EVENT_SENT, "Sent"),
    (EVENT_VIEWED, "Viewed"),
    (EVENT_PAGE_VIEWED, "Page Viewed"),
    (EVENT_SIGNED, "Signed"),
    (EVENT_DECLINED, "Declined"),
    (EVENT_COMPLETED, "Completed"),
    (EVENT_CANCELLED, "Cancelled"),
    (EVENT_EXPIRED, "Expired"),
    (EVENT_REMINDER_SENT, "Reminder Sent"),
]

# ---------------------------------------------------------------------------
# Stamp types (reserved for future rubber-stamp feature)
# ---------------------------------------------------------------------------
STAMP_APPROVED = "approved"
STAMP_REJECTED = "rejected"
STAMP_RECEIVED = "received"
STAMP_REVIEWED = "reviewed"
STAMP_CONFIDENTIAL = "confidential"

STAMP_TYPE_CHOICES = [
    (STAMP_APPROVED, "Approved"),
    (STAMP_REJECTED, "Rejected"),
    (STAMP_RECEIVED, "Received"),
    (STAMP_REVIEWED, "Reviewed"),
    (STAMP_CONFIDENTIAL, "Confidential"),
]
