# Request status
REQUEST_PENDING = "pending"
REQUEST_PARTIALLY_FULFILLED = "partially_fulfilled"
REQUEST_FULFILLED = "fulfilled"
REQUEST_EXPIRED = "expired"
REQUEST_CANCELLED = "cancelled"

REQUEST_STATUS_CHOICES = [
    (REQUEST_PENDING, "Pending"),
    (REQUEST_PARTIALLY_FULFILLED, "Partially Fulfilled"),
    (REQUEST_FULFILLED, "Fulfilled"),
    (REQUEST_EXPIRED, "Expired"),
    (REQUEST_CANCELLED, "Cancelled"),
]

# Submission status
SUBMISSION_PENDING = "pending_review"
SUBMISSION_APPROVED = "approved"
SUBMISSION_REJECTED = "rejected"

SUBMISSION_STATUS_CHOICES = [
    (SUBMISSION_PENDING, "Pending Review"),
    (SUBMISSION_APPROVED, "Approved"),
    (SUBMISSION_REJECTED, "Rejected"),
]
