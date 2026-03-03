"""Constants for the physical_records module."""

# Location types
BUILDING = "building"
ROOM = "room"
CABINET = "cabinet"
SHELF = "shelf"
BOX = "box"
LOCATION_TYPE_CHOICES = [
    (BUILDING, "Building"),
    (ROOM, "Room"),
    (CABINET, "Cabinet"),
    (SHELF, "Shelf"),
    (BOX, "Box"),
]

# Record conditions
GOOD = "good"
FAIR = "fair"
POOR = "poor"
DAMAGED = "damaged"
CONDITION_CHOICES = [
    (GOOD, "Good"),
    (FAIR, "Fair"),
    (POOR, "Poor"),
    (DAMAGED, "Damaged"),
]

# Charge-out status
CHECKED_OUT = "checked_out"
RETURNED = "returned"
OVERDUE = "overdue"
CHARGEOUT_STATUS_CHOICES = [
    (CHECKED_OUT, "Checked Out"),
    (RETURNED, "Returned"),
    (OVERDUE, "Overdue"),
]

# Destruction methods
SHREDDING = "shredding"
INCINERATION = "incineration"
PULPING = "pulping"
OTHER = "other"
DESTRUCTION_METHOD_CHOICES = [
    (SHREDDING, "Shredding"),
    (INCINERATION, "Incineration"),
    (PULPING, "Pulping"),
    (OTHER, "Other"),
]
