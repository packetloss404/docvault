"""Tests for the NERPlugin."""

import pytest
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import override_settings

from documents.models import Document
from entities.models import Entity, EntityType
from entities.plugin import NERPlugin
from processing.context import ProcessingContext


@pytest.fixture
def user(db):
    return User.objects.create_user(username="nerpluginuser", password="testpass")


@pytest.fixture
def document(user):
    return Document.objects.create(
        title="NER Plugin Doc",
        content="John Doe works at Acme Corp in New York.",
        owner=user,
    )


@pytest.mark.django_db
class TestNERPluginCanRun:
    @override_settings(NER_ENABLED=False)
    def test_returns_false_when_disabled(self, document):
        plugin = NERPlugin()
        ctx = ProcessingContext(content="some content", document_id=document.pk)
        assert plugin.can_run(ctx) is False

    @override_settings(NER_ENABLED=True)
    def test_returns_false_when_no_content(self, document):
        plugin = NERPlugin()
        ctx = ProcessingContext(content="", document_id=document.pk)
        assert plugin.can_run(ctx) is False

    @override_settings(NER_ENABLED=True)
    def test_returns_false_when_whitespace_only(self, document):
        plugin = NERPlugin()
        ctx = ProcessingContext(content="   \n\t  ", document_id=document.pk)
        assert plugin.can_run(ctx) is False

    @override_settings(NER_ENABLED=True)
    def test_returns_false_when_no_document_id(self):
        plugin = NERPlugin()
        ctx = ProcessingContext(content="some content", document_id=None)
        assert plugin.can_run(ctx) is False

    @override_settings(NER_ENABLED=True)
    def test_returns_true_when_all_conditions_met(self, document):
        plugin = NERPlugin()
        ctx = ProcessingContext(content="some content", document_id=document.pk)
        assert plugin.can_run(ctx) is True


@pytest.mark.django_db
class TestNERPluginProcess:
    @override_settings(NER_ENABLED=True)
    def test_process_with_regex_extraction(self, document):
        """Test that process works with regex-only extraction (no spaCy)."""
        EntityType.objects.create(
            name="EMAIL",
            label="Email",
            extraction_pattern=r"[\w.+-]+@[\w-]+\.[\w.]+",
            enabled=True,
        )
        # Update document content to contain an email
        document.content = "Contact john@example.com for details."
        document.save()

        plugin = NERPlugin()
        ctx = ProcessingContext(
            content=document.content,
            document_id=document.pk,
        )

        # Mock spaCy to return empty list (simulate it not being installed)
        with patch("entities.extraction.extract_entities_spacy", return_value=[]):
            result = plugin.process(ctx)

        assert result.success is True
        entities = Entity.objects.filter(document=document)
        emails = entities.filter(entity_type__name="EMAIL")
        assert emails.count() == 1
        assert emails.first().value == "john@example.com"

    @override_settings(NER_ENABLED=True)
    def test_process_with_mocked_spacy(self, document):
        """Test process with mocked spaCy entities."""
        EntityType.seed_defaults()

        plugin = NERPlugin()
        ctx = ProcessingContext(
            content="John Doe works at Acme Corp.",
            document_id=document.pk,
        )

        mock_spacy_results = [
            {"label": "PERSON", "value": "John Doe", "start": 0, "end": 8},
            {"label": "ORG", "value": "Acme Corp", "start": 18, "end": 27},
        ]

        with patch("entities.extraction.extract_entities_spacy", return_value=mock_spacy_results):
            result = plugin.process(ctx)

        assert result.success is True
        assert "Extracted" in result.message

        entities = Entity.objects.filter(document=document)
        assert entities.count() >= 2
        person = entities.filter(entity_type__name="PERSON").first()
        assert person is not None
        assert person.value == "John Doe"

        org = entities.filter(entity_type__name="ORGANIZATION").first()
        assert org is not None
        assert org.value == "ACME CORP"  # normalized to upper

    @override_settings(NER_ENABLED=True)
    def test_process_deduplicates_entities(self, document):
        """Same entity from spaCy and regex should be deduplicated."""
        EntityType.seed_defaults()

        plugin = NERPlugin()
        ctx = ProcessingContext(
            content="John Doe is mentioned twice as John Doe",
            document_id=document.pk,
        )

        mock_spacy_results = [
            {"label": "PERSON", "value": "John Doe", "start": 0, "end": 8},
            {"label": "PERSON", "value": "John Doe", "start": 31, "end": 39},
        ]

        with patch("entities.extraction.extract_entities_spacy", return_value=mock_spacy_results):
            result = plugin.process(ctx)

        assert result.success is True
        person_count = Entity.objects.filter(
            document=document, entity_type__name="PERSON", value="John Doe",
        ).count()
        assert person_count == 1

    @override_settings(NER_ENABLED=True)
    def test_process_cleans_old_entities_on_reprocess(self, document):
        """Re-processing should delete old entities first when new entities are found."""
        EntityType.seed_defaults()
        et_old = EntityType.objects.create(name="CUSTOM_OLD", label="Old", enabled=True)
        Entity.objects.create(
            document=document, entity_type=et_old,
            value="Old Value", raw_value="Old Value",
        )
        assert Entity.objects.filter(document=document).count() == 1

        plugin = NERPlugin()
        ctx = ProcessingContext(
            content="John Doe works here.",
            document_id=document.pk,
        )

        # Mock spaCy to return a PERSON entity so the delete path is reached
        mock_spacy_results = [
            {"label": "PERSON", "value": "John Doe", "start": 0, "end": 8},
        ]

        with patch("entities.extraction.extract_entities_spacy", return_value=mock_spacy_results):
            result = plugin.process(ctx)

        assert result.success is True
        # Old CUSTOM_OLD entity should be deleted
        assert Entity.objects.filter(document=document, entity_type=et_old).count() == 0
        # New PERSON entity should exist
        assert Entity.objects.filter(document=document, entity_type__name="PERSON").count() == 1

    @override_settings(NER_ENABLED=True)
    def test_process_handles_errors_gracefully(self, document):
        """Plugin should not crash even if extraction fails."""
        plugin = NERPlugin()
        ctx = ProcessingContext(
            content="some content",
            document_id=document.pk,
        )

        with patch("entities.extraction.extract_entities_spacy", side_effect=Exception("boom")):
            result = plugin.process(ctx)

        # NER is non-fatal; it catches exceptions
        assert result.success is True
        assert "NER failed" in result.message

    def test_plugin_metadata(self):
        plugin = NERPlugin()
        assert plugin.name == "NERPlugin"
        assert plugin.order == 115
