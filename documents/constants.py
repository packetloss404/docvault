"""Constants for the documents module."""

# Time units for retention policies
TIME_UNIT_DAYS = "days"
TIME_UNIT_WEEKS = "weeks"
TIME_UNIT_MONTHS = "months"
TIME_UNIT_YEARS = "years"

TIME_UNITS = [
    (TIME_UNIT_DAYS, "Days"),
    (TIME_UNIT_WEEKS, "Weeks"),
    (TIME_UNIT_MONTHS, "Months"),
    (TIME_UNIT_YEARS, "Years"),
]

# Matching algorithms
MATCH_NONE = 0
MATCH_ANY = 1
MATCH_ALL = 2
MATCH_LITERAL = 3
MATCH_REGEX = 4
MATCH_FUZZY = 5
MATCH_AUTO = 6

MATCHING_ALGORITHMS = [
    (MATCH_NONE, "None"),
    (MATCH_ANY, "Any word"),
    (MATCH_ALL, "All words"),
    (MATCH_LITERAL, "Literal"),
    (MATCH_REGEX, "Regular expression"),
    (MATCH_FUZZY, "Fuzzy match"),
    (MATCH_AUTO, "Auto (ML-based)"),
]
