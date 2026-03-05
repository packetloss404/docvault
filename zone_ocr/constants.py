"""Constants for the Zone OCR module."""

# Field types (mirrors CustomField data types for compatibility)
FIELD_STRING = "string"
FIELD_DATE = "date"
FIELD_INTEGER = "integer"
FIELD_FLOAT = "float"
FIELD_MONETARY = "monetary"
FIELD_BOOLEAN = "boolean"

FIELD_TYPE_CHOICES = [
    (FIELD_STRING, "String"),
    (FIELD_DATE, "Date"),
    (FIELD_INTEGER, "Integer"),
    (FIELD_FLOAT, "Float"),
    (FIELD_MONETARY, "Monetary"),
    (FIELD_BOOLEAN, "Boolean"),
]

# Preprocessing choices
PREPROCESS_NONE = "none"
PREPROCESS_NUMERIC_ONLY = "numeric_only"
PREPROCESS_ALPHA_ONLY = "alpha_only"
PREPROCESS_DATE_PARSE = "date_parse"
PREPROCESS_CURRENCY_PARSE = "currency_parse"

PREPROCESSING_CHOICES = [
    (PREPROCESS_NONE, "None"),
    (PREPROCESS_NUMERIC_ONLY, "Numeric Only"),
    (PREPROCESS_ALPHA_ONLY, "Alpha Only"),
    (PREPROCESS_DATE_PARSE, "Date Parse"),
    (PREPROCESS_CURRENCY_PARSE, "Currency Parse"),
]

# Map zone_ocr field types to CustomField data types
ZONE_TO_CUSTOM_FIELD_TYPE = {
    FIELD_STRING: "string",
    FIELD_DATE: "date",
    FIELD_INTEGER: "integer",
    FIELD_FLOAT: "float",
    FIELD_MONETARY: "monetary",
    FIELD_BOOLEAN: "boolean",
}
