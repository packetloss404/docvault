"""Tests for AI feature functions: summarize, extract entities, suggest title."""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.test import override_settings

from ai.client import reset_client
from ai.features import ENTITY_RESPONSE_SCHEMA, TITLE_RESPONSE_SCHEMA, _title_candidates
from documents.models import Document


@pytest.fixture(autouse=True)
def _reset_llm_client():
    """Reset client singleton between tests."""
    reset_client()
    yield
    reset_client()


@pytest.mark.django_db
class TestSummarizeDocument:
    """Tests for the summarize_document() function."""

    @override_settings(LLM_ENABLED=False)
    def test_returns_error_when_llm_disabled(self):
        """Returns error when LLM is not enabled."""
        from ai.features import summarize_document

        result = summarize_document(document_id=1)
        assert result["summary"] is None
        assert "not enabled" in result["error"].lower()

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.features.get_llm_client")
    def test_returns_summary_for_valid_doc(self, mock_get_client):
        """Returns a summary for a document with content."""
        mock_client = MagicMock()
        mock_client.generate.return_value = "This is a lease agreement for a property."
        mock_get_client.return_value = mock_client

        user = User.objects.create_user("sumuser", password="pass123!")
        doc = Document.objects.create(
            title="Lease Agreement",
            content="This lease is between landlord and tenant for property at 123 Main St.",
            filename="lease.pdf",
            owner=user,
        )

        from ai.features import summarize_document

        result = summarize_document(document_id=doc.pk)
        assert result["summary"] == "This is a lease agreement for a property."
        assert "error" not in result

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.features.get_llm_client")
    def test_returns_error_for_missing_doc(self, mock_get_client):
        """Returns error for a non-existent document."""
        mock_get_client.return_value = MagicMock()

        from ai.features import summarize_document

        result = summarize_document(document_id=99999)
        assert result["summary"] is None
        assert "not found" in result["error"].lower()


@pytest.mark.django_db
class TestExtractEntities:
    """Tests for the extract_entities() function."""

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.features.get_llm_client")
    def test_returns_parsed_json_entities(self, mock_get_client):
        """Returns parsed JSON entities when the LLM returns valid JSON."""
        mock_client = MagicMock()
        mock_client.generate.return_value = (
            '{"names": ["John Smith"], "organizations": ["Acme Corp"], '
            '"dates": ["2025-01-15"], "amounts": ["$500.00"], '
            '"addresses": [], "emails": [], "phone_numbers": []}'
        )
        mock_get_client.return_value = mock_client

        user = User.objects.create_user("entuser", password="pass123!")
        doc = Document.objects.create(
            title="Invoice",
            content="Invoice from Acme Corp to John Smith dated 2025-01-15 for $500.00",
            filename="inv.pdf",
            owner=user,
        )

        from ai.features import extract_entities

        result = extract_entities(document_id=doc.pk)
        assert result["entities"] is not None
        assert "names" in result["entities"]
        assert "John Smith" in result["entities"]["names"]
        assert "Acme Corp" in result["entities"]["organizations"]
        assert mock_client.generate.call_args.kwargs['temperature'] == 0
        assert mock_client.generate.call_args.kwargs['seed'] == 0
        assert mock_client.generate.call_args.kwargs['json_schema'] == ENTITY_RESPONSE_SCHEMA

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.features.get_llm_client")
    def test_rejects_json_parse_failure_instead_of_returning_raw_data(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.generate.return_value = "This is not valid JSON at all"
        mock_get_client.return_value = mock_client

        user = User.objects.create_user("entuser2", password="pass123!")
        doc = Document.objects.create(
            title="Some Doc",
            content="Some content for entity extraction.",
            filename="some.pdf",
            owner=user,
        )

        from ai.features import extract_entities

        result = extract_entities(document_id=doc.pk)
        assert result['entities'] is None
        assert result['error_code'] == 'invalid_model_output'
        assert 'raw' not in result

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.features.get_llm_client")
    def test_handles_markdown_wrapped_json(self, mock_get_client):
        """Correctly strips markdown code fences from JSON response."""
        mock_client = MagicMock()
        mock_client.generate.return_value = (
            '```json\n{"names": ["Alice"], "dates": ["2025-03-01"], "organizations": [], '
            '"amounts": [], "addresses": [], "emails": [], "phone_numbers": []}\n```'
        )
        mock_get_client.return_value = mock_client

        user = User.objects.create_user("entuser3", password="pass123!")
        doc = Document.objects.create(
            title="Doc",
            content="Alice signed the document on 2025-03-01.",
            filename="alice.pdf",
            owner=user,
        )

        from ai.features import extract_entities

        result = extract_entities(document_id=doc.pk)
        assert result["entities"] is not None
        assert "names" in result["entities"]
        assert "Alice" in result["entities"]["names"]

    @pytest.mark.parametrize('changes', [
        {'dates': ['2017-05-19', '2018-03-16']},
        {'names': ['Invented Person']},
        {'names': ['Mira Soland']},
        {'organizations': ['United States Government']},
        {'names': 'Barack Obama'},
        {'amounts': [1234]},
        {'names': ['']},
        {'unsupported': []},
    ])
    @patch('ai.features.get_llm_client')
    def test_rejects_unfounded_values_and_invalid_shapes(self, mock_get_client, changes):
        entities = {category: [] for category in ENTITY_RESPONSE_SCHEMA['required']}
        entities.update(changes)
        mock_get_client.return_value.generate.return_value = json.dumps(entities)
        document = Document.objects.create(
            title='Source grounding',
            content='Barack Obama approved the mission in London. Batteries cost 1234 dollars.',
        )
        from ai.features import extract_entities

        result = extract_entities(document.pk)
        assert result['entities'] is None
        assert result['error_code'] == 'invalid_model_output'

    @patch('ai.features.get_llm_client')
    def test_missing_categories_are_rejected(self, mock_get_client):
        mock_get_client.return_value.generate.return_value = '{"names": ["Alice"]}'
        document = Document.objects.create(title='Incomplete result', content='Alice signed.')
        from ai.features import extract_entities

        assert extract_entities(document.pk)['error_code'] == 'invalid_model_output'


@pytest.mark.django_db
class TestSuggestTitle:
    """Tests for the suggest_title() function."""

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.features.get_llm_client")
    def test_returns_suggestion(self, mock_get_client):
        """Returns a suggested title from the LLM."""
        mock_client = MagicMock()
        mock_client.generate.return_value = '{"title": "Invoice from Acme Corp"}'
        mock_get_client.return_value = mock_client

        user = User.objects.create_user("titleuser", password="pass123!")
        doc = Document.objects.create(
            title="scan_20250115.pdf",
            content="Invoice from Acme Corp for services in January 2025.",
            filename="scan_20250115.pdf",
            owner=user,
        )

        from ai.features import suggest_title

        result = suggest_title(document_id=doc.pk)
        assert result["suggested_title"] == "Invoice from Acme Corp"
        arguments = mock_client.generate.call_args
        assert doc.title not in arguments.args[0]
        assert arguments.kwargs['context'] == doc.content
        assert arguments.kwargs['temperature'] == 0
        assert arguments.kwargs['seed'] == 0
        assert arguments.kwargs['json_schema']['properties']['title'] == {
            **TITLE_RESPONSE_SCHEMA['properties']['title'], 'enum': [doc.content],
        }

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.features.get_llm_client")
    def test_cleans_up_quoted_response(self, mock_get_client):
        """Strips surrounding quotes from the suggested title."""
        mock_client = MagicMock()
        mock_client.generate.return_value = json.dumps({'title': '"Lease Agreement for 123 Main Street"'})
        mock_get_client.return_value = mock_client

        user = User.objects.create_user("titleuser2", password="pass123!")
        doc = Document.objects.create(
            title="document.pdf",
            content="Lease Agreement for 123 Main Street. The tenant agrees to the following terms.",
            filename="document.pdf",
            owner=user,
        )

        from ai.features import suggest_title

        result = suggest_title(document_id=doc.pk)
        assert result["suggested_title"] == "Lease Agreement for 123 Main Street"
        assert '"' not in result["suggested_title"]

    @pytest.mark.parametrize('response', [
        {'title': 'US President approves military operation in London'},
        {'title': 'Barack Obama approved military mission'},
        {'title': 'Mira Soland paid 75 dollars'},
        {'title': 'Acceptance document random'},
        {'title': ''},
        {'title': '.'},
        {'title': 'x' * 101},
        {'title': 1234},
        {'title': 'Barack Obama', 'reason': 'Known person'},
        ['Barack Obama'],
        'Barack Obama',
    ])
    @patch('ai.features.get_llm_client')
    def test_rejects_unfounded_or_invalid_title_without_fallback(self, mock_client, response):
        mock_client.return_value.generate.return_value = json.dumps(response)
        document = Document.objects.create(
            title='Acceptance document random',
            content=(
                'Barack Obama approved the mission in London. The mission code is ORBIT73491. '
                'Solar batteries cost 1234 dollars. ' + 'x' * 110
            ),
        )
        from ai.features import suggest_title

        result = suggest_title(document.pk)
        assert result['suggested_title'] is None
        assert result['error_code'] == 'invalid_model_output'

    @patch('ai.features.get_llm_client')
    def test_rejects_malformed_json(self, mock_client):
        mock_client.return_value.generate.return_value = '{"title": "Barack Obama'
        document = Document.objects.create(title='Untitled', content='Barack Obama approved the mission.')
        from ai.features import suggest_title

        assert suggest_title(document.pk)['error_code'] == 'invalid_model_output'

    @patch('ai.features.get_llm_client')
    def test_punctuation_only_content_does_not_invoke_model(self, mock_client):
        document = Document.objects.create(title='Untitled', content='...\n!!!')
        from ai.features import suggest_title

        result = suggest_title(document.pk)
        assert result['suggested_title'] is None
        assert 'suitable' in result['error']
        mock_client.return_value.generate.assert_not_called()

    @patch('ai.features.get_llm_client')
    def test_truncated_context_does_not_add_synthetic_source_text(self, mock_client):
        mock_client.return_value.generate.return_value = json.dumps({'title': 'x' * 100})
        document = Document.objects.create(title='Untitled', content='x' * 5001)
        from ai.features import suggest_title

        assert suggest_title(document.pk)['suggested_title'] == 'x' * 100
        assert mock_client.return_value.generate.call_args.kwargs['context'] == 'x' * 5000

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.features.get_llm_client")
    def test_returns_error_when_doc_not_found(self, mock_get_client):
        """Returns error when the document does not exist."""
        mock_get_client.return_value = MagicMock()

        from ai.features import suggest_title

        result = suggest_title(document_id=99999)
        assert result["suggested_title"] is None
        assert "not found" in result["error"].lower()

    @override_settings(LLM_ENABLED=False)
    def test_returns_error_when_llm_disabled(self):
        """Returns error when LLM is not enabled."""
        from ai.features import suggest_title

        result = suggest_title(document_id=1)
        assert result["suggested_title"] is None
        assert "not enabled" in result["error"].lower()


def test_title_candidates_are_bounded_verbatim_phrases():
    content = '!!!\nInvoice from Mira Soland.\nInvoice from Mira Soland.\n' + 'word ' * 30
    content += '\n' + '\n'.join(f'Other section {index}' for index in range(20))
    candidates = _title_candidates(content)
    assert len(candidates) == 8
    assert candidates.count('Invoice from Mira Soland.') == 1
    assert all(0 < len(phrase) <= 100 and any(char.isalnum() for char in phrase) for phrase in candidates)
    assert all(phrase in content for phrase in candidates)
    assert candidates[1] == 'word ' * 19 + 'word'


def test_long_unbroken_title_candidate_is_still_bounded():
    assert _title_candidates('x' * 110) == ['x' * 100]
