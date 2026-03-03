"""Tests for entity extraction helpers."""

import pytest
from unittest.mock import patch, MagicMock

from entities.extraction import (
    extract_entities_regex,
    get_spacy_model,
    normalize_entity_value,
)
from entities.models import EntityType


class TestNormalizeEntityValue:
    def test_person_title_case(self):
        assert normalize_entity_value("john doe", "PERSON") == "John Doe"

    def test_person_already_title(self):
        assert normalize_entity_value("John Doe", "PERSON") == "John Doe"

    def test_organization_upper_case(self):
        assert normalize_entity_value("acme corp", "ORGANIZATION") == "ACME CORP"

    def test_organization_already_upper(self):
        assert normalize_entity_value("ACME CORP", "ORGANIZATION") == "ACME CORP"

    def test_other_types_just_normalize_whitespace(self):
        assert normalize_entity_value("  new   york  ", "LOCATION") == "new york"

    def test_collapses_internal_whitespace(self):
        assert normalize_entity_value("John    Doe", "PERSON") == "John Doe"

    def test_strips_leading_trailing_whitespace(self):
        assert normalize_entity_value("  John Doe  ", "PERSON") == "John Doe"

    def test_empty_value(self):
        assert normalize_entity_value("", "PERSON") == ""


@pytest.mark.django_db
class TestExtractEntitiesRegex:
    def test_extracts_matching_patterns(self):
        et = EntityType.objects.create(
            name="EMAIL",
            label="Email",
            extraction_pattern=r"[\w.+-]+@[\w-]+\.[\w.]+",
        )
        content = "Contact us at support@example.com or sales@test.org"
        results = extract_entities_regex(content, [et])
        values = [r["value"] for r in results]
        assert "support@example.com" in values
        assert "sales@test.org" in values
        assert all(r["label"] == "EMAIL" for r in results)

    def test_empty_pattern_skipped(self):
        et = EntityType.objects.create(
            name="EMPTY_PAT", label="Empty", extraction_pattern="",
        )
        results = extract_entities_regex("anything", [et])
        assert results == []

    def test_whitespace_pattern_skipped(self):
        et = EntityType.objects.create(
            name="WS_PAT", label="WS", extraction_pattern="   ",
        )
        results = extract_entities_regex("anything", [et])
        assert results == []

    def test_invalid_regex_does_not_crash(self):
        et = EntityType.objects.create(
            name="BAD_RE", label="Bad", extraction_pattern="[invalid",
        )
        results = extract_entities_regex("anything", [et])
        assert results == []

    def test_result_includes_start_end(self):
        et = EntityType.objects.create(
            name="SSN", label="SSN",
            extraction_pattern=r"\d{3}-\d{2}-\d{4}",
        )
        content = "SSN is 123-45-6789"
        results = extract_entities_regex(content, [et])
        assert len(results) == 1
        assert results[0]["start"] == 7
        assert results[0]["end"] == 18

    def test_no_matches(self):
        et = EntityType.objects.create(
            name="PHONE", label="Phone",
            extraction_pattern=r"\(\d{3}\)\s?\d{3}-\d{4}",
        )
        results = extract_entities_regex("No phone numbers here", [et])
        assert results == []


class TestGetSpacyModel:
    def test_returns_none_when_spacy_not_installed(self):
        import entities.extraction as ext_module
        # Reset the cached model
        original = ext_module._spacy_model
        ext_module._spacy_model = None
        try:
            # Patch spacy out of sys.modules so the import inside get_spacy_model fails
            import sys
            spacy_backup = sys.modules.get("spacy")
            sys.modules["spacy"] = None  # This will cause ImportError on `import spacy`
            try:
                result = get_spacy_model()
                assert result is None
            finally:
                if spacy_backup is not None:
                    sys.modules["spacy"] = spacy_backup
                else:
                    sys.modules.pop("spacy", None)
        finally:
            ext_module._spacy_model = original

    def test_returns_cached_model(self):
        import entities.extraction as ext_module
        original = ext_module._spacy_model
        try:
            mock_model = MagicMock()
            ext_module._spacy_model = mock_model
            result = get_spacy_model()
            assert result is mock_model
        finally:
            ext_module._spacy_model = original
