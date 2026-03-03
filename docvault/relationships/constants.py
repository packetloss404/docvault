"""Built-in relationship type definitions for DocVault."""

REL_SUPERSEDES = "supersedes"
REL_REFERENCES = "references"
REL_IS_ATTACHMENT_OF = "is_attachment_of"
REL_RESPONDS_TO = "responds_to"
REL_CONTRADICTS = "contradicts"
REL_RELATES_TO = "relates_to"
REL_AMENDS = "amends"
REL_DUPLICATES = "duplicates"

# Each tuple: (slug, label, icon, is_directional)
BUILTIN_TYPES = [
    (REL_SUPERSEDES, "Supersedes", "bi-arrow-up-circle", True),
    (REL_REFERENCES, "References", "bi-link-45deg", True),
    (REL_IS_ATTACHMENT_OF, "Is attachment of", "bi-paperclip", True),
    (REL_RESPONDS_TO, "Responds to", "bi-reply", True),
    (REL_CONTRADICTS, "Contradicts", "bi-exclamation-triangle", False),
    (REL_RELATES_TO, "Relates to", "bi-arrows-angle-expand", False),
    (REL_AMENDS, "Amends", "bi-pencil", True),
    (REL_DUPLICATES, "Duplicates", "bi-files", False),
]
