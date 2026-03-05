"""Tests for the AI embeddings module (chunking, embedding generation)."""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from ai.client import reset_client
from ai.embeddings import (
    build_embedding_text,
    chunk_text,
    generate_chunk_embeddings,
    generate_document_embedding,
    generate_query_embedding,
)


@pytest.fixture(autouse=True)
def _reset_llm_client():
    """Reset client singleton between tests."""
    reset_client()
    yield
    reset_client()


class TestChunkText:
    """Tests for the chunk_text() function."""

    def test_short_text_no_split(self):
        """Short text that fits within chunk_size should return a single chunk."""
        text = "This is a short sentence."
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self):
        """Long text exceeding chunk_size should be split into multiple chunks."""
        words = ["word"] * 200
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=50, overlap=10)
        assert len(chunks) > 1
        # Each chunk should have at most 50 words
        for chunk in chunks:
            assert len(chunk.split()) <= 50

    def test_empty_text_returns_empty(self):
        """Empty text should return an empty list."""
        chunks = chunk_text("", chunk_size=100, overlap=10)
        assert chunks == []

    def test_whitespace_only_returns_empty(self):
        """Whitespace-only text should return empty."""
        chunks = chunk_text("   \n\t  ", chunk_size=100, overlap=10)
        assert chunks == []

    def test_overlap_works_correctly(self):
        """Consecutive chunks should share overlapping words."""
        # Create text with exactly 20 distinct words
        words = [f"word{i}" for i in range(20)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=10, overlap=3)

        assert len(chunks) >= 2
        # The second chunk should start 7 words (10-3) into the first chunk
        chunk1_words = chunks[0].split()
        chunk2_words = chunks[1].split()
        # Last 3 words of chunk1 should be first 3 words of chunk2
        assert chunk1_words[-3:] == chunk2_words[:3]


class TestBuildEmbeddingText:
    """Tests for build_embedding_text()."""

    @override_settings(LLM_ENABLED=False)
    def test_includes_title_and_content(self):
        """build_embedding_text includes title and content fields."""
        doc = MagicMock()
        doc.title = "Invoice from Acme"
        doc.correspondent = None
        doc.document_type = None
        doc.tags.all.return_value = []
        doc.content = "This is the invoice content."

        result = build_embedding_text(doc)
        assert "Title: Invoice from Acme" in result
        assert "This is the invoice content." in result

    @override_settings(LLM_ENABLED=False)
    def test_includes_correspondent_type_tags(self):
        """build_embedding_text includes correspondent, type, and tags."""
        doc = MagicMock()
        doc.title = "Test Doc"
        doc.correspondent = MagicMock()
        doc.correspondent.name = "Acme Corp"
        doc.document_type = MagicMock()
        doc.document_type.name = "Invoice"

        tag1 = MagicMock()
        tag1.name = "Finance"
        tag2 = MagicMock()
        tag2.name = "2025"
        doc.tags.all.return_value = [tag1, tag2]
        doc.content = "Invoice content text."

        result = build_embedding_text(doc)
        assert "Correspondent: Acme Corp" in result
        assert "Type: Invoice" in result
        assert "Tags: Finance, 2025" in result

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.embeddings.get_llm_client")
    def test_truncates_long_content(self, mock_get_client):
        """build_embedding_text truncates content that exceeds token limits."""
        mock_client = MagicMock()
        # Make header use 100 tokens and content 10000 tokens (exceeds limit)
        mock_client.count_tokens.side_effect = lambda t: len(t) // 4
        mock_get_client.return_value = mock_client

        doc = MagicMock()
        doc.title = "Short Title"
        doc.correspondent = None
        doc.document_type = None
        doc.tags.all.return_value = []
        doc.content = "x " * 50000  # Very long content

        result = build_embedding_text(doc)
        # Result should be shorter than the original full content
        assert len(result) < len(doc.content)


class TestGenerateDocumentEmbedding:
    """Tests for generate_document_embedding()."""

    @override_settings(LLM_ENABLED=False)
    def test_returns_none_when_llm_disabled(self):
        """Returns None when LLM is not enabled."""
        doc = MagicMock()
        doc.title = "Test"
        doc.content = "Content"
        result = generate_document_embedding(doc)
        assert result is None

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.embeddings.get_llm_client")
    def test_returns_embedding_when_llm_available(self, mock_get_client):
        """Returns an embedding vector when the LLM client is available."""
        mock_client = MagicMock()
        mock_client.embed.return_value = [0.1, 0.2, 0.3, 0.4]
        mock_client.count_tokens.return_value = 10
        mock_get_client.return_value = mock_client

        doc = MagicMock()
        doc.title = "Test Invoice"
        doc.correspondent = None
        doc.document_type = None
        doc.tags.all.return_value = []
        doc.content = "This is an invoice."

        result = generate_document_embedding(doc)
        assert result == [0.1, 0.2, 0.3, 0.4]
        mock_client.embed.assert_called_once()


class TestGenerateQueryEmbedding:
    """Tests for generate_query_embedding()."""

    @override_settings(LLM_ENABLED=False)
    def test_returns_none_when_llm_disabled(self):
        """Returns None when LLM is not enabled."""
        result = generate_query_embedding("search query")
        assert result is None

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.embeddings.get_llm_client")
    def test_returns_embedding_for_query(self, mock_get_client):
        """Returns an embedding vector for a search query."""
        mock_client = MagicMock()
        mock_client.embed.return_value = [0.5, 0.6, 0.7]
        mock_get_client.return_value = mock_client

        result = generate_query_embedding("find invoices")
        assert result == [0.5, 0.6, 0.7]
        mock_client.embed.assert_called_once_with("find invoices")


class TestGenerateChunkEmbeddings:
    """Tests for generate_chunk_embeddings()."""

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.embeddings.get_llm_client")
    def test_returns_chunk_embedding_pairs(self, mock_get_client):
        """Returns list of (chunk_text, embedding) tuples."""
        mock_client = MagicMock()
        mock_client.embed_batch.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_get_client.return_value = mock_client

        # Create text that is short enough to be a single chunk
        result = generate_chunk_embeddings("Hello world")
        assert len(result) == 1
        assert result[0][0] == "Hello world"
        assert result[0][1] == [0.1, 0.2]

    @override_settings(LLM_ENABLED=False)
    def test_returns_empty_when_llm_disabled(self):
        """Returns empty list when LLM client is not available."""
        result = generate_chunk_embeddings("some text")
        assert result == []
