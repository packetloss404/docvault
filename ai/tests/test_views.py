"""Tests for the AI module API views."""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

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


@pytest.fixture
def api_client():
    """Return an APIClient instance."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create and return a regular user."""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="pass123!"
    )


@pytest.fixture
def admin_user(db):
    """Create and return a superuser."""
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass123!"
    )


@pytest.fixture
def sample_doc(user):
    """Create a sample document for testing."""
    return Document.objects.create(
        title="Test Invoice",
        content="Invoice for $500 from Acme Corp.",
        filename="test_invoice.pdf",
        owner=user,
    )


# --- SemanticSearchView ---


@pytest.mark.django_db
class TestSemanticSearchView:
    """Tests for the SemanticSearchView."""

    def test_requires_authentication(self, api_client):
        """Unauthenticated requests should return 401."""
        resp = api_client.get("/api/v1/ai/search/semantic/", {"query": "invoice"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("ai.search.semantic_search")
    def test_returns_results(self, mock_search, api_client, user):
        """Authenticated request with valid query returns results."""
        mock_search.return_value = [
            {"id": 1, "title": "Invoice", "score": 0.9, "correspondent": None,
             "document_type": None, "tags": [], "created": None},
        ]
        api_client.force_authenticate(user=user)
        resp = api_client.get("/api/v1/ai/search/semantic/", {"query": "invoice"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1
        assert len(resp.data["results"]) == 1


# --- HybridSearchView ---


@pytest.mark.django_db
class TestHybridSearchView:
    """Tests for the HybridSearchView."""

    @patch("ai.search.hybrid_search")
    def test_returns_results(self, mock_search, api_client, user):
        """Returns combined keyword + semantic results."""
        mock_search.return_value = [
            {"id": 1, "title": "Invoice", "hybrid_score": 0.85},
        ]
        api_client.force_authenticate(user=user)
        resp = api_client.get("/api/v1/ai/search/hybrid/", {"query": "invoice"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1


# --- SimilarDocumentsAIView ---


@pytest.mark.django_db
class TestSimilarDocumentsAIView:
    """Tests for the SimilarDocumentsAIView."""

    @patch("ai.search.find_similar_documents")
    def test_returns_results(self, mock_similar, api_client, user, sample_doc):
        """Returns similar document results for a given document."""
        mock_similar.return_value = [
            {"id": 2, "title": "Another Invoice", "score": 0.8},
        ]
        api_client.force_authenticate(user=user)
        resp = api_client.get(f"/api/v1/ai/similar/{sample_doc.pk}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1


# --- DocumentChatView ---


@pytest.mark.django_db
class TestDocumentChatView:
    """Tests for the DocumentChatView."""

    def test_requires_question(self, api_client, user, sample_doc):
        """POST without a question should return 400."""
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            f"/api/v1/ai/documents/{sample_doc.pk}/chat/",
            {},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch("ai.chat.chat_with_document")
    def test_returns_response(self, mock_chat, api_client, user, sample_doc):
        """POST with valid question returns chat answer."""
        mock_chat.return_value = {
            "answer": "The invoice is for $500.",
            "sources": [{"document_id": sample_doc.pk, "title": "Test Invoice", "chunk_count": 1}],
        }
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            f"/api/v1/ai/documents/{sample_doc.pk}/chat/",
            {"question": "How much is the invoice?"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["answer"] == "The invoice is for $500."


# --- GlobalChatView ---


@pytest.mark.django_db
class TestGlobalChatView:
    """Tests for the GlobalChatView."""

    @patch("ai.chat.chat_across_documents")
    def test_returns_response(self, mock_chat, api_client, user):
        """POST with valid question returns global chat answer."""
        mock_chat.return_value = {
            "answer": "You have several invoices.",
            "sources": [{"document_id": 1, "title": "Invoice 001", "score": 0.9}],
        }
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            "/api/v1/ai/chat/",
            {"question": "What invoices do I have?"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["answer"] == "You have several invoices."


# --- SummarizeView ---


@pytest.mark.django_db
class TestSummarizeView:
    """Tests for the SummarizeView."""

    @patch("ai.features.summarize_document")
    def test_returns_summary(self, mock_summarize, api_client, user, sample_doc):
        """Returns document summary."""
        mock_summarize.return_value = {"summary": "This is a test invoice for $500."}
        api_client.force_authenticate(user=user)
        resp = api_client.get(f"/api/v1/ai/documents/{sample_doc.pk}/summarize/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["summary"] == "This is a test invoice for $500."


# --- EntityExtractView ---


@pytest.mark.django_db
class TestEntityExtractView:
    """Tests for the EntityExtractView."""

    @patch("ai.features.extract_entities")
    def test_returns_entities(self, mock_extract, api_client, user, sample_doc):
        """Returns extracted entities."""
        mock_extract.return_value = {
            "entities": {
                "names": ["Acme Corp"],
                "amounts": ["$500"],
                "dates": [],
            },
        }
        api_client.force_authenticate(user=user)
        resp = api_client.get(f"/api/v1/ai/documents/{sample_doc.pk}/entities/")
        assert resp.status_code == status.HTTP_200_OK
        assert "Acme Corp" in resp.data["entities"]["names"]


# --- SmartTitleView ---


@pytest.mark.django_db
class TestSmartTitleView:
    """Tests for the SmartTitleView."""

    @patch("ai.features.suggest_title")
    def test_returns_suggestion(self, mock_suggest, api_client, user, sample_doc):
        """Returns a suggested title."""
        mock_suggest.return_value = {"suggested_title": "Acme Corp Invoice - $500"}
        api_client.force_authenticate(user=user)
        resp = api_client.get(f"/api/v1/ai/documents/{sample_doc.pk}/suggest-title/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["suggested_title"] == "Acme Corp Invoice - $500"


# --- AIConfigView ---


@pytest.mark.django_db
class TestAIConfigView:
    """Tests for the AIConfigView (admin only)."""

    def test_requires_admin(self, api_client, user):
        """Regular (non-admin) user should get 403."""
        api_client.force_authenticate(user=user)
        resp = api_client.get("/api/v1/ai/config/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @override_settings(
        LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_MODEL="gpt-4o-mini",
        EMBEDDING_MODEL="text-embedding-3-small",
    )
    @patch("ai.vector_store.VectorStore.load")
    def test_returns_config(self, mock_load, api_client, admin_user):
        """Admin user can retrieve AI configuration."""
        mock_store = MagicMock()
        mock_store.count = 42
        mock_load.return_value = mock_store

        api_client.force_authenticate(user=admin_user)
        resp = api_client.get("/api/v1/ai/config/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["llm_enabled"] is True
        assert resp.data["llm_provider"] == "openai"
        assert resp.data["llm_model"] == "gpt-4o-mini"
        assert resp.data["vector_store_count"] == 42


# --- AIStatusView ---


@pytest.mark.django_db
class TestAIStatusView:
    """Tests for the AIStatusView."""

    @override_settings(
        LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_MODEL="gpt-4o-mini",
        EMBEDDING_MODEL="text-embedding-3-small", LLM_API_KEY="test-key",
    )
    @patch("ai.vector_store.get_vector_store")
    @patch("ai.client.get_llm_client")
    def test_returns_status(self, mock_get_client, mock_get_store, api_client, user):
        """Returns AI system status including availability."""
        mock_get_client.return_value = MagicMock()
        mock_store = MagicMock()
        mock_store.count = 100
        mock_get_store.return_value = mock_store

        api_client.force_authenticate(user=user)
        resp = api_client.get("/api/v1/ai/status/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["llm_enabled"] is True
        assert resp.data["llm_available"] is True
        assert resp.data["vector_store_count"] == 100


# --- RebuildVectorIndexView ---


@pytest.mark.django_db
class TestRebuildVectorIndexView:
    """Tests for the RebuildVectorIndexView (admin only)."""

    def test_requires_admin(self, api_client, user):
        """Regular (non-admin) user should get 403."""
        api_client.force_authenticate(user=user)
        resp = api_client.post("/api/v1/ai/rebuild-index/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @patch("ai.tasks.rebuild_vector_index")
    def test_starts_rebuild_task(self, mock_task, api_client, admin_user):
        """Admin POST starts the rebuild task and returns 202."""
        mock_task.delay.return_value = MagicMock()
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post("/api/v1/ai/rebuild-index/")
        assert resp.status_code == status.HTTP_202_ACCEPTED
        assert resp.data["status"] == "started"
        mock_task.delay.assert_called_once()
