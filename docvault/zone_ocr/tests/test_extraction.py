"""Tests for Zone OCR extraction helpers."""

import pytest

from zone_ocr.constants import (
    FIELD_BOOLEAN,
    FIELD_DATE,
    FIELD_FLOAT,
    FIELD_INTEGER,
    FIELD_MONETARY,
    FIELD_STRING,
    PREPROCESS_ALPHA_ONLY,
    PREPROCESS_CURRENCY_PARSE,
    PREPROCESS_DATE_PARSE,
    PREPROCESS_NONE,
    PREPROCESS_NUMERIC_ONLY,
)
from zone_ocr.extraction import (
    apply_preprocessing,
    extract_field_from_content,
    validate_value,
)


class TestApplyPreprocessing:
    def test_none_strips_whitespace(self):
        assert apply_preprocessing("  hello world  ", PREPROCESS_NONE) == "hello world"

    def test_none_returns_empty_string_as_is(self):
        result = apply_preprocessing("", PREPROCESS_NONE)
        assert result == ""

    def test_numeric_only_keeps_digits_and_decimal(self):
        assert apply_preprocessing("$1,234.56", PREPROCESS_NUMERIC_ONLY) == "1234.56"

    def test_numeric_only_keeps_negative(self):
        assert apply_preprocessing("-42.5 USD", PREPROCESS_NUMERIC_ONLY) == "-42.5"

    def test_numeric_only_empty_input(self):
        result = apply_preprocessing("abc", PREPROCESS_NUMERIC_ONLY)
        assert result == ""

    def test_alpha_only_keeps_letters_and_spaces(self):
        assert apply_preprocessing("Hello 123 World!", PREPROCESS_ALPHA_ONLY) == "Hello  World"

    def test_alpha_only_strips_result(self):
        result = apply_preprocessing("  abc123  ", PREPROCESS_ALPHA_ONLY)
        assert result == "abc"

    def test_date_parse_iso_format(self):
        assert apply_preprocessing("2025-01-15", PREPROCESS_DATE_PARSE) == "2025-01-15"

    def test_date_parse_us_format(self):
        assert apply_preprocessing("01/15/2025", PREPROCESS_DATE_PARSE) == "2025-01-15"

    def test_date_parse_long_format(self):
        assert apply_preprocessing("January 15, 2025", PREPROCESS_DATE_PARSE) == "2025-01-15"

    def test_date_parse_unparseable_returns_cleaned(self):
        result = apply_preprocessing("not a date", PREPROCESS_DATE_PARSE)
        assert result == "not a date"

    def test_currency_parse_us_dollar(self):
        assert apply_preprocessing("$1,234.56", PREPROCESS_CURRENCY_PARSE) == "1234.56"

    def test_currency_parse_euro(self):
        # European: 1.234,56 -> 1234.56
        assert apply_preprocessing("EUR 1.234,56", PREPROCESS_CURRENCY_PARSE) == "1234.56"

    def test_currency_parse_simple(self):
        assert apply_preprocessing("$100.00", PREPROCESS_CURRENCY_PARSE) == "100.00"

    def test_currency_parse_comma_as_decimal(self):
        # Two decimal digits after comma -> treat comma as decimal
        assert apply_preprocessing("100,50", PREPROCESS_CURRENCY_PARSE) == "100.50"

    def test_currency_parse_comma_as_thousands(self):
        # More or fewer than 2 digits after comma -> treat as thousands
        assert apply_preprocessing("1,000", PREPROCESS_CURRENCY_PARSE) == "1000"

    def test_empty_input_returns_as_is(self):
        assert apply_preprocessing("", PREPROCESS_NUMERIC_ONLY) == ""
        assert apply_preprocessing("", PREPROCESS_ALPHA_ONLY) == ""
        assert apply_preprocessing(None, PREPROCESS_NONE) is None


class TestValidateValue:
    def test_empty_value_is_valid(self):
        assert validate_value("", FIELD_STRING, "") is True

    def test_string_always_valid(self):
        assert validate_value("anything", FIELD_STRING, "") is True

    def test_integer_valid(self):
        assert validate_value("42", FIELD_INTEGER, "") is True

    def test_integer_invalid(self):
        assert validate_value("abc", FIELD_INTEGER, "") is False

    def test_float_valid(self):
        assert validate_value("3.14", FIELD_FLOAT, "") is True

    def test_float_invalid(self):
        assert validate_value("not_a_float", FIELD_FLOAT, "") is False

    def test_monetary_valid(self):
        assert validate_value("1234.56", FIELD_MONETARY, "") is True

    def test_monetary_invalid(self):
        assert validate_value("abc", FIELD_MONETARY, "") is False

    def test_date_valid_has_digits(self):
        assert validate_value("2025-01-15", FIELD_DATE, "") is True

    def test_date_invalid_no_digits(self):
        assert validate_value("no date here", FIELD_DATE, "") is False

    def test_boolean_valid_values(self):
        for val in ("true", "false", "yes", "no", "1", "0", "t", "f", "y", "n"):
            assert validate_value(val, FIELD_BOOLEAN, "") is True

    def test_boolean_invalid(self):
        assert validate_value("maybe", FIELD_BOOLEAN, "") is False

    def test_regex_validation_pass(self):
        assert validate_value("INV-001", FIELD_STRING, r"^INV-\d+$") is True

    def test_regex_validation_fail(self):
        assert validate_value("RECEIPT-001", FIELD_STRING, r"^INV-\d+$") is False

    def test_invalid_regex_does_not_crash(self):
        # An invalid regex should not raise; it logs a warning and passes
        result = validate_value("anything", FIELD_STRING, r"[invalid")
        assert result is True


class TestExtractFieldFromContent:
    def test_extract_colon_separated(self):
        content = "Invoice Number: INV-001\nDate: 2025-01-15"
        value, confidence = extract_field_from_content(
            content, "Invoice Number", FIELD_STRING, PREPROCESS_NONE,
        )
        assert value == "INV-001"
        assert confidence > 0

    def test_extract_tab_separated(self):
        content = "Total\t1500.00\nTax\t150.00"
        value, confidence = extract_field_from_content(
            content, "Total", FIELD_FLOAT, PREPROCESS_NONE,
        )
        assert value == "1500.00"
        assert confidence > 0

    def test_extract_multiple_spaces(self):
        content = "Amount Due    $500.00\nPaid    $500.00"
        value, confidence = extract_field_from_content(
            content, "Amount Due", FIELD_STRING, PREPROCESS_NONE,
        )
        assert value == "$500.00"

    def test_extract_not_found(self):
        content = "This is random content."
        value, confidence = extract_field_from_content(
            content, "Invoice Number", FIELD_STRING, PREPROCESS_NONE,
        )
        assert value == ""
        assert confidence == 0.0

    def test_extract_empty_content(self):
        value, confidence = extract_field_from_content(
            "", "anything", FIELD_STRING, PREPROCESS_NONE,
        )
        assert value == ""
        assert confidence == 0.0

    def test_extract_none_content(self):
        value, confidence = extract_field_from_content(
            None, "anything", FIELD_STRING, PREPROCESS_NONE,
        )
        assert value == ""
        assert confidence == 0.0

    def test_extract_empty_field_name(self):
        value, confidence = extract_field_from_content(
            "some content", "", FIELD_STRING, PREPROCESS_NONE,
        )
        assert value == ""
        assert confidence == 0.0

    def test_extract_with_preprocessing(self):
        content = "Total: $1,234.56"
        value, confidence = extract_field_from_content(
            content, "Total", FIELD_MONETARY, PREPROCESS_CURRENCY_PARSE,
        )
        assert value == "1234.56"

    def test_extract_case_insensitive(self):
        content = "invoice number: INV-100"
        value, confidence = extract_field_from_content(
            content, "Invoice Number", FIELD_STRING, PREPROCESS_NONE,
        )
        assert value == "INV-100"

    def test_higher_confidence_when_valid(self):
        content = "Count: 42"
        value, confidence = extract_field_from_content(
            content, "Count", FIELD_INTEGER, PREPROCESS_NONE,
        )
        assert value == "42"
        assert confidence == 0.7  # valid value gets 0.7

    def test_lower_confidence_when_type_mismatch(self):
        content = "Count: abc"
        value, confidence = extract_field_from_content(
            content, "Count", FIELD_INTEGER, PREPROCESS_NONE,
        )
        assert value == "abc"
        assert confidence == 0.6  # invalid type gets 0.6
