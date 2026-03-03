"""Constants for the legal_hold module."""

# Hold status
DRAFT = "draft"
ACTIVE = "active"
RELEASED = "released"
HOLD_STATUS_CHOICES = [(DRAFT, "Draft"), (ACTIVE, "Active"), (RELEASED, "Released")]

# Criteria types
CUSTODIAN = "custodian"
DATE_RANGE = "date_range"
TAG = "tag"
DOCUMENT_TYPE = "document_type"
SEARCH_QUERY = "search_query"
CABINET = "cabinet"
SPECIFIC_DOCUMENTS = "specific_documents"
CRITERIA_TYPE_CHOICES = [
    (CUSTODIAN, "Custodian"),
    (DATE_RANGE, "Date Range"),
    (TAG, "Tag"),
    (DOCUMENT_TYPE, "Document Type"),
    (SEARCH_QUERY, "Search Query"),
    (CABINET, "Cabinet"),
    (SPECIFIC_DOCUMENTS, "Specific Documents"),
]
