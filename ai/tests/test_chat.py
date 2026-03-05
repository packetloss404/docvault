"""Tests for the AI chat (document Q&A and RAG) functions."""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.test import override_settings

from ai.client import reset_client
from ai.vector_store import reset_vector_store
from documents.models import Document


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons between tests."""
    reset_client()
    reset_vector_store()
    yield
    reset_client()
    reset_vector_store()


@pytest.mark.django_db
class TestChatWithDocument:
    """Tests for the chat_with_document() function."""

    @override_settings(LLM_ENABLED=False)
    def test_returns_disabled_message_when_llm_off(self):
        """Returns a disabled message when LLM is not enabled."""
        from ai.chat import chat_with_document

        result = chat_with_document(document_id=1, question="What is this?")
        assert result["answer"] == "AI features are not enabled."
        assert result["sources"] == []

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.chat.get_llm_client")
    def test_returns_not_found_for_missing_doc(self, mock_get_client):
        """Returns not-found message for a non-existent document."""
        mock_get_client.return_value = MagicMock()

        from ai.chat import chat_with_document

        result = chat_with_document(document_id=99999, question="What is this?")
        assert result["answer"] == "Document not found."
        assert result["sources"] == []

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.chat.get_llm_client")
    def test_returns_no_content_for_empty_doc(self, mock_get_client):
        """Returns no-content message when the document has no text."""
        mock_get_client.return_value = MagicMock()
        user = User.objects.create_user("chatuser1", password="pass123!")
        doc = Document.objects.create(
            title="Empty Doc", content="", filename="empty.pdf", owner=user,
        )

        from ai.chat import chat_with_document

        result = chat_with_document(document_id=doc.pk, question="What is this?")
        assert "no text content" in result["answer"].lower()

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.chat.generate_query_embedding")
    @patch("ai.chat.get_llm_client")
    def test_returns_answer_from_llm(self, mock_get_client, mock_query_embed):
        """Returns the LLM-generated answer for a document with content."""
        mock_client = MagicMock()
        mock_client.generate.return_value = "The invoice is for $500."
        mock_client.embed.return_value = [0.1] * 128
        mock_get_client.return_value = mock_client
        mock_query_embed.return_value = [0.1] * 128

        user = User.objects.create_user("chatuser2", password="pass123!")
        doc = Document.objects.create(
            title="Invoice",
            content="This invoice is for services rendered totaling $500. Payment due in 30 days. "
                    "The services were provided by Acme Corp during the month of January.",
            filename="invoice.pdf",
            owner=user,
        )

        from ai.chat import chat_with_document

        result = chat_with_document(document_id=doc.pk, question="How much is the invoice?")
        assert result["answer"] == "The invoice is for $500."
        assert len(result["sources"]) == 1
        assert result["sources"][0]["document_id"] == doc.pk

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.chat.generate_query_embedding")
    @patch("ai.chat.get_llm_client")
    def test_uses_conversation_history(self, mock_get_client, mock_query_embed):
        """Conversation history is passed to the LLM prompt."""
        mock_client = MagicMock()
        mock_client.generate.return_value = "Follow-up answer"
        mock_client.embed.return_value = [0.1] * 128
        mock_get_client.return_value = mock_client
        mock_query_embed.return_value = [0.1] * 128

        user = User.objects.create_user("chatuser3", password="pass123!")
        doc = Document.objects.create(
            title="Contract",
            content="This is a lease agreement between landlord John Smith and tenant Jane Doe "
                    "for property at 123 Main Street. Monthly rent is $1200 for 12 months.",
            filename="contract.pdf",
            owner=user,
        )

        history = [
            {"role": "user", "content": "Who are the parties?"},
            {"role": "assistant", "content": "John Smith and Jane Doe"},
        ]

        from ai.chat import chat_with_document

        result = chat_with_document(
            document_id=doc.pk,
            question="What is the monthly rent?",
            history=history,
        )
        assert result["answer"] == "Follow-up answer"
        # Verify the generate call included the history in the prompt
        call_args = mock_client.generate.call_args
        prompt_text = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "history" in prompt_text.lower() or "John Smith" in prompt_text


@pytest.mark.django_db
class TestChatAcrossDocuments:
    """Tests for the chat_across_documents() function."""

    @override_settings(LLM_ENABLED=False)
    def test_returns_disabled_when_llm_off(self):
        """Returns disabled message when LLM is not enabled."""
        from ai.chat import chat_across_documents

        result = chat_across_documents(question="What invoices do I have?")
        assert result["answer"] == "AI features are not enabled."
        assert result["sources"] == []

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.chat.get_vector_store")
    @patch("ai.chat.generate_query_embedding")
    @patch("ai.chat.get_llm_client")
    def test_with_mocked_client_and_store(
        self, mock_get_client, mock_query_embed, mock_get_store
    ):
        """Returns answer from LLM with source references."""
        mock_client = MagicMock()
        mock_client.generate.return_value = "You have 2 invoices totaling $1500."
        mock_get_client.return_value = mock_client
        mock_query_embed.return_value = [0.1] * 128

        user = User.objects.create_user("globalchat1", password="pass123!")
        doc1 = Document.objects.create(
            title="Invoice 001", content="Invoice for $500", filename="i1.pdf", owner=user,
        )
        doc2 = Document.objects.create(
            title="Invoice 002", content="Invoice for $1000", filename="i2.pdf", owner=user,
        )

        mock_store = MagicMock()
        mock_store.search.return_value = [(doc1.pk, 0.9), (doc2.pk, 0.8)]
        mock_get_store.return_value = mock_store

        from ai.chat import chat_across_documents

        result = chat_across_documents(question="Sum of all invoices?")
        assert result["answer"] == "You have 2 invoices totaling $1500."
        assert len(result["sources"]) == 2

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.chat.get_vector_store")
    @patch("ai.chat.generate_query_embedding")
    @patch("ai.chat.get_llm_client")
    def test_filters_by_user_id(
        self, mock_get_client, mock_query_embed, mock_get_store
    ):
        """Only documents belonging to the given user_id should be included."""
        mock_client = MagicMock()
        mock_client.generate.return_value = "Answer filtered by user."
        mock_get_client.return_value = mock_client
        mock_query_embed.return_value = [0.1] * 128

        user1 = User.objects.create_user("chatowner1", password="pass123!")
        user2 = User.objects.create_user("chatowner2", password="pass123!")
        doc1 = Document.objects.create(
            title="User1 Doc", content="Content A", filename="u1.pdf", owner=user1,
        )
        doc2 = Document.objects.create(
            title="User2 Doc", content="Content B", filename="u2.pdf", owner=user2,
        )

        mock_store = MagicMock()
        mock_store.search.return_value = [(doc1.pk, 0.9), (doc2.pk, 0.8)]
        mock_get_store.return_value = mock_store

        from ai.chat import chat_across_documents

        result = chat_across_documents(
            question="What do I have?", user_id=user1.pk,
        )
        # Only user1's document should be in sources
        source_ids = [s["document_id"] for s in result["sources"]]
        assert doc1.pk in source_ids
        assert doc2.pk not in source_ids
