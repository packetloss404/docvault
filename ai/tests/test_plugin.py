"""Tests for the AIPlugin processing pipeline plugin."""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.test import override_settings

from ai.client import reset_client
from ai.plugin import AIPlugin
from ai.vector_store import reset_vector_store
from documents.models import Document
from processing.context import ProcessingContext


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons between tests."""
    reset_client()
    reset_vector_store()
    yield
    reset_client()
    reset_vector_store()


class TestAIPluginCanRun:
    """Tests for AIPlugin.can_run()."""

    def _make_context(self, content="", document_id=None):
        """Helper to create a ProcessingContext with given content."""
        ctx = ProcessingContext()
        ctx.content = content
        ctx.document_id = document_id
        return ctx

    @override_settings(LLM_ENABLED=False)
    def test_returns_false_when_llm_disabled(self):
        """can_run should return False when LLM_ENABLED is False."""
        plugin = AIPlugin()
        ctx = self._make_context(content="Some content")
        assert plugin.can_run(ctx) is False

    @override_settings(LLM_ENABLED=True)
    def test_returns_true_when_llm_enabled_with_content(self):
        """can_run should return True when LLM is enabled and content is present."""
        plugin = AIPlugin()
        ctx = self._make_context(content="This is some document content")
        assert plugin.can_run(ctx) is True

    @override_settings(LLM_ENABLED=True)
    def test_returns_false_when_no_content(self):
        """can_run should return False when content is empty."""
        plugin = AIPlugin()
        ctx = self._make_context(content="")
        assert plugin.can_run(ctx) is False

    @override_settings(LLM_ENABLED=True)
    def test_returns_false_when_whitespace_only_content(self):
        """can_run should return False when content is whitespace-only."""
        plugin = AIPlugin()
        ctx = self._make_context(content="   \n\t  ")
        assert plugin.can_run(ctx) is False


@pytest.mark.django_db
class TestAIPluginProcess:
    """Tests for AIPlugin.process()."""

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.vector_store.get_vector_store")
    @patch("ai.embeddings.generate_document_embedding")
    def test_generates_embedding_and_stores(self, mock_gen_embed, mock_get_store):
        """process() generates an embedding and adds it to the vector store."""
        user = User.objects.create_user("pluginuser", password="pass123!")
        doc = Document.objects.create(
            title="Plugin Test Doc",
            content="Content for the processing pipeline.",
            filename="plugin_test.pdf",
            owner=user,
        )

        mock_gen_embed.return_value = [0.1] * 128
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        plugin = AIPlugin()
        ctx = ProcessingContext()
        ctx.content = "Content for the processing pipeline."
        ctx.document_id = doc.pk

        result = plugin.process(ctx)
        assert result.success is True
        mock_gen_embed.assert_called_once()
        mock_store.add.assert_called_once_with(doc.pk, [0.1] * 128)
        mock_store.save.assert_called_once()

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.embeddings.generate_document_embedding")
    def test_handles_errors_gracefully(self, mock_gen_embed):
        """process() returns success even when embedding generation fails."""
        user = User.objects.create_user("pluginerr", password="pass123!")
        doc = Document.objects.create(
            title="Error Doc",
            content="Some content.",
            filename="error_test.pdf",
            owner=user,
        )

        mock_gen_embed.side_effect = Exception("LLM API error")

        plugin = AIPlugin()
        ctx = ProcessingContext()
        ctx.content = "Some content."
        ctx.document_id = doc.pk

        result = plugin.process(ctx)
        # Should still return success=True (non-fatal error)
        assert result.success is True
        assert "failed" in result.message.lower() or "Embedding failed" in result.message
