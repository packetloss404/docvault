"""Tests for the AI semantic and hybrid search functions."""

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
class TestSemanticSearch:
    """Tests for the semantic_search() function."""

    @override_settings(LLM_ENABLED=False)
    def test_returns_empty_when_llm_disabled(self):
        """Returns empty list when LLM is disabled (no query embedding)."""
        from ai.search import semantic_search

        results = semantic_search("find invoices")
        assert results == []

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.search.get_vector_store")
    @patch("ai.search.generate_query_embedding")
    def test_returns_results_with_mocked_dependencies(
        self, mock_gen_embed, mock_get_store
    ):
        """Returns formatted results when embedding and store are available."""
        user = User.objects.create_user("searcher", password="pass123!")
        doc = Document.objects.create(
            title="Acme Invoice",
            content="Invoice for services rendered",
            filename="invoice.pdf",
            owner=user,
        )

        mock_gen_embed.return_value = [0.1] * 128
        mock_store = MagicMock()
        mock_store.search.return_value = [(doc.pk, 0.95)]
        mock_get_store.return_value = mock_store

        from ai.search import semantic_search

        results = semantic_search("invoices", k=5)
        assert len(results) == 1
        assert results[0]["id"] == doc.pk
        assert results[0]["title"] == "Acme Invoice"
        assert results[0]["score"] == 0.95

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.search.get_vector_store")
    @patch("ai.search.generate_query_embedding")
    def test_filters_by_user_id(self, mock_gen_embed, mock_get_store):
        """When user_id is provided, only that user's documents appear."""
        user1 = User.objects.create_user("user1", password="pass123!")
        user2 = User.objects.create_user("user2", password="pass123!")
        doc1 = Document.objects.create(
            title="User1 Doc", content="Content", filename="d1.pdf", owner=user1,
        )
        doc2 = Document.objects.create(
            title="User2 Doc", content="Content", filename="d2.pdf", owner=user2,
        )

        mock_gen_embed.return_value = [0.1] * 128
        mock_store = MagicMock()
        mock_store.search.return_value = [(doc1.pk, 0.9), (doc2.pk, 0.8)]
        mock_get_store.return_value = mock_store

        from ai.search import semantic_search

        results = semantic_search("test", k=10, user_id=user1.pk)
        result_ids = [r["id"] for r in results]
        assert doc1.pk in result_ids
        assert doc2.pk not in result_ids


@pytest.mark.django_db
class TestFindSimilarDocuments:
    """Tests for the find_similar_documents() function."""

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.search.get_vector_store")
    @patch("ai.embeddings.generate_document_embedding")
    def test_excludes_source_document(self, mock_gen_embed, mock_get_store):
        """The source document should not appear in similar results."""
        user = User.objects.create_user("simuser", password="pass123!")
        source = Document.objects.create(
            title="Source Doc", content="Content A", filename="source.pdf", owner=user,
        )
        similar = Document.objects.create(
            title="Similar Doc", content="Content B", filename="similar.pdf", owner=user,
        )

        mock_gen_embed.return_value = [0.1] * 128
        mock_store = MagicMock()
        mock_store.search.return_value = [
            (source.pk, 1.0),  # source document (should be excluded)
            (similar.pk, 0.85),
        ]
        mock_get_store.return_value = mock_store

        from ai.search import find_similar_documents

        results = find_similar_documents(source.pk, k=5)
        result_ids = [r["id"] for r in results]
        assert source.pk not in result_ids
        assert similar.pk in result_ids

    def test_returns_empty_for_nonexistent_doc(self):
        """Returns empty when the document ID does not exist."""
        from ai.search import find_similar_documents

        results = find_similar_documents(99999, k=5)
        assert results == []


@pytest.mark.django_db
class TestHybridSearch:
    """Tests for the hybrid_search() function."""

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.search.semantic_search")
    @patch("search.query.execute_search")
    def test_combines_keyword_and_semantic_results(self, mock_keyword, mock_semantic):
        """hybrid_search merges keyword and semantic results using RRF."""
        user = User.objects.create_user("hybriduser", password="pass123!")
        doc1 = Document.objects.create(
            title="Doc One", content="Content", filename="d1.pdf", owner=user,
        )
        doc2 = Document.objects.create(
            title="Doc Two", content="Content", filename="d2.pdf", owner=user,
        )
        doc3 = Document.objects.create(
            title="Doc Three", content="Content", filename="d3.pdf", owner=user,
        )

        mock_keyword.return_value = {
            "results": [
                {"id": doc1.pk, "title": "Doc One", "score": 5.0},
                {"id": doc2.pk, "title": "Doc Two", "score": 3.0},
            ],
        }
        mock_semantic.return_value = [
            {"id": doc2.pk, "title": "Doc Two", "score": 0.9},
            {"id": doc3.pk, "title": "Doc Three", "score": 0.8},
        ]

        from ai.search import hybrid_search

        results = hybrid_search("test query", k=10)
        assert len(results) > 0
        # doc2 appears in both, so it should rank highest
        result_ids = [r["id"] for r in results]
        assert doc2.pk in result_ids
        # All results should have a hybrid_score
        for r in results:
            assert "hybrid_score" in r
            assert r["hybrid_score"] > 0

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.search.semantic_search")
    @patch("search.query.execute_search")
    def test_returns_empty_when_both_empty(self, mock_keyword, mock_semantic):
        """Returns empty list when both keyword and semantic return no results."""
        mock_keyword.return_value = {"results": []}
        mock_semantic.return_value = []

        from ai.search import hybrid_search

        results = hybrid_search("nonexistent query", k=10)
        assert results == []

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.search.semantic_search")
    @patch("search.query.execute_search")
    def test_rrf_ranking(self, mock_keyword, mock_semantic):
        """Documents appearing in both sets should score higher via RRF."""
        user = User.objects.create_user("rrfuser", password="pass123!")
        doc_both = Document.objects.create(
            title="Both Sources", content="C", filename="both.pdf", owner=user,
        )
        doc_kw_only = Document.objects.create(
            title="Keyword Only", content="C", filename="kw.pdf", owner=user,
        )
        doc_sem_only = Document.objects.create(
            title="Semantic Only", content="C", filename="sem.pdf", owner=user,
        )

        mock_keyword.return_value = {
            "results": [
                {"id": doc_both.pk, "title": "Both Sources", "score": 5.0},
                {"id": doc_kw_only.pk, "title": "Keyword Only", "score": 3.0},
            ],
        }
        mock_semantic.return_value = [
            {"id": doc_both.pk, "title": "Both Sources", "score": 0.95},
            {"id": doc_sem_only.pk, "title": "Semantic Only", "score": 0.80},
        ]

        from ai.search import hybrid_search

        results = hybrid_search("test", k=10)
        # doc_both should have the highest hybrid score (appears in both)
        assert results[0]["id"] == doc_both.pk
        assert results[0]["hybrid_score"] > results[1]["hybrid_score"]
