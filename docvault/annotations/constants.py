"""Constants for the annotations module."""

# Annotation types
HIGHLIGHT = "highlight"
UNDERLINE = "underline"
STRIKETHROUGH = "strikethrough"
STICKY_NOTE = "sticky_note"
FREEHAND = "freehand"
RECTANGLE = "rectangle"
TEXT_BOX = "text_box"
RUBBER_STAMP = "rubber_stamp"

ANNOTATION_TYPE_CHOICES = [
    (HIGHLIGHT, "Highlight"),
    (UNDERLINE, "Underline"),
    (STRIKETHROUGH, "Strikethrough"),
    (STICKY_NOTE, "Sticky Note"),
    (FREEHAND, "Freehand"),
    (RECTANGLE, "Rectangle"),
    (TEXT_BOX, "Text Box"),
    (RUBBER_STAMP, "Rubber Stamp"),
]

# Built-in stamp types
STAMP_APPROVED = "APPROVED"
STAMP_REJECTED = "REJECTED"
STAMP_DRAFT = "DRAFT"
STAMP_CONFIDENTIAL = "CONFIDENTIAL"
STAMP_FINAL = "FINAL"
STAMP_REVIEWED = "REVIEWED"
STAMP_VOID = "VOID"

STAMP_TYPE_CHOICES = [
    (STAMP_APPROVED, "Approved"),
    (STAMP_REJECTED, "Rejected"),
    (STAMP_DRAFT, "Draft"),
    (STAMP_CONFIDENTIAL, "Confidential"),
    (STAMP_FINAL, "Final"),
    (STAMP_REVIEWED, "Reviewed"),
    (STAMP_VOID, "Void"),
]
