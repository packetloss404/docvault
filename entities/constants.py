"""Default entity type definitions for NER."""

# Mapping of spaCy NER labels to our canonical entity type names.
SPACY_LABEL_MAP = {
    "PERSON": "PERSON",
    "PER": "PERSON",
    "ORG": "ORGANIZATION",
    "NORP": "ORGANIZATION",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "FAC": "LOCATION",
    "DATE": "DATE",
    "TIME": "DATE",
    "MONEY": "MONETARY",
    "QUANTITY": "MONETARY",
}

# Seed data for the EntityType table.
# Each entry: (name, label, color, icon)
DEFAULT_ENTITY_TYPES = [
    ("PERSON", "Person", "#0d6efd", "bi-person"),
    ("ORGANIZATION", "Organization", "#6610f2", "bi-building"),
    ("LOCATION", "Location", "#198754", "bi-geo-alt"),
    ("DATE", "Date", "#fd7e14", "bi-calendar-event"),
    ("MONETARY", "Monetary Value", "#dc3545", "bi-currency-dollar"),
    ("CUSTOM", "Custom", "#6c757d", "bi-tag"),
]
