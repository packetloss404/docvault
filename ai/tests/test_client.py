"""Tests for the AI LLM client abstraction layer."""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from ai.client import LLMClient, get_llm_client, reset_client


@pytest.fixture(autouse=True)
def _reset_client():
    """Ensure the client singleton is reset between tests."""
    reset_client()
    yield
    reset_client()


class TestGetLLMClient:
    """Tests for the get_llm_client() factory function."""

    @override_settings(LLM_ENABLED=False)
    def test_returns_none_when_disabled(self):
        """When LLM_ENABLED=False, get_llm_client returns None."""
        client = get_llm_client()
        assert client is None

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.providers.openai_client.openai")
    def test_returns_openai_client_when_provider_openai(self, mock_openai):
        """When provider is openai, returns an OpenAIClient instance."""
        mock_openai.OpenAI.return_value = MagicMock()
        client = get_llm_client()
        assert client is not None
        from ai.providers.openai_client import OpenAIClient

        assert isinstance(client, OpenAIClient)

    @override_settings(
        LLM_ENABLED=True, LLM_PROVIDER="ollama", LLM_API_ENDPOINT="http://localhost:11434"
    )
    @patch("ai.providers.ollama_client.ollama")
    def test_returns_ollama_client_when_provider_ollama(self, mock_ollama):
        """When provider is ollama, returns an OllamaClient instance."""
        mock_ollama.Client.return_value = MagicMock()
        client = get_llm_client()
        assert client is not None
        from ai.providers.ollama_client import OllamaClient

        assert isinstance(client, OllamaClient)

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="unknown_provider")
    def test_returns_none_for_unknown_provider(self):
        """Unknown LLM_PROVIDER should result in None."""
        client = get_llm_client()
        assert client is None

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai", LLM_API_KEY="test-key")
    @patch("ai.providers.openai_client.openai")
    def test_reset_client_clears_singleton(self, mock_openai):
        """reset_client() clears the cached singleton so next call creates fresh."""
        mock_openai.OpenAI.return_value = MagicMock()
        client1 = get_llm_client()
        assert client1 is not None

        reset_client()

        client2 = get_llm_client()
        assert client2 is not None
        # They should be different instances since singleton was cleared
        assert client1 is not client2


class TestOpenAIClient:
    """Tests for the OpenAI client implementation."""

    @override_settings(LLM_ENABLED=True, LLM_API_KEY="test-key", LLM_PROVIDER="openai")
    @patch("ai.providers.openai_client.openai")
    def _make_client(self, mock_openai):
        """Helper to construct an OpenAIClient with mocked openai module."""
        mock_openai.OpenAI.return_value = MagicMock()
        from ai.providers.openai_client import OpenAIClient

        client = OpenAIClient()
        return client, mock_openai

    @override_settings(LLM_ENABLED=True, LLM_API_KEY="test-key", LLM_PROVIDER="openai")
    @patch("ai.providers.openai_client.openai")
    def test_generate_returns_text(self, mock_openai):
        """generate() returns the text content from the LLM response."""
        mock_inner = MagicMock()
        mock_openai.OpenAI.return_value = mock_inner

        mock_choice = MagicMock()
        mock_choice.message.content = "Hello world response"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_inner.chat.completions.create.return_value = mock_response

        from ai.providers.openai_client import OpenAIClient

        client = OpenAIClient()
        result = client.generate("Tell me something")
        assert result == "Hello world response"

    @override_settings(LLM_ENABLED=True, LLM_API_KEY="test-key", LLM_PROVIDER="openai")
    @patch("ai.providers.openai_client.time.sleep")
    @patch("ai.providers.openai_client.openai")
    def test_generate_retries_on_failure(self, mock_openai, mock_sleep):
        """generate() retries on transient errors and succeeds on subsequent attempt."""
        mock_inner = MagicMock()
        mock_openai.OpenAI.return_value = mock_inner

        mock_choice = MagicMock()
        mock_choice.message.content = "Success after retry"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        # First call fails, second succeeds
        mock_inner.chat.completions.create.side_effect = [
            Exception("API timeout"),
            mock_response,
        ]

        from ai.providers.openai_client import OpenAIClient

        client = OpenAIClient()
        result = client.generate("Test prompt")
        assert result == "Success after retry"
        assert mock_inner.chat.completions.create.call_count == 2
        mock_sleep.assert_called_once()

    @override_settings(LLM_ENABLED=True, LLM_API_KEY="test-key", LLM_PROVIDER="openai")
    @patch("ai.providers.openai_client.openai")
    def test_embed_returns_vector(self, mock_openai):
        """embed() returns the embedding vector from the API response."""
        mock_inner = MagicMock()
        mock_openai.OpenAI.return_value = mock_inner

        mock_data_item = MagicMock()
        mock_data_item.embedding = [0.1, 0.2, 0.3]
        mock_response = MagicMock()
        mock_response.data = [mock_data_item]
        mock_inner.embeddings.create.return_value = mock_response

        from ai.providers.openai_client import OpenAIClient

        client = OpenAIClient()
        result = client.embed("test text")
        assert result == [0.1, 0.2, 0.3]

    @override_settings(LLM_ENABLED=True, LLM_API_KEY="test-key", LLM_PROVIDER="openai")
    @patch("ai.providers.openai_client.openai")
    def test_embed_batch_returns_vectors(self, mock_openai):
        """embed_batch() returns a list of embedding vectors."""
        mock_inner = MagicMock()
        mock_openai.OpenAI.return_value = mock_inner

        item1 = MagicMock()
        item1.embedding = [0.1, 0.2]
        item2 = MagicMock()
        item2.embedding = [0.3, 0.4]
        mock_response = MagicMock()
        mock_response.data = [item1, item2]
        mock_inner.embeddings.create.return_value = mock_response

        from ai.providers.openai_client import OpenAIClient

        client = OpenAIClient()
        result = client.embed_batch(["text one", "text two"])
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    @override_settings(LLM_ENABLED=True, LLM_API_KEY="test-key", LLM_PROVIDER="openai")
    @patch("ai.providers.openai_client.openai")
    def test_count_tokens_returns_integer(self, mock_openai):
        """count_tokens() returns an integer token count."""
        mock_openai.OpenAI.return_value = MagicMock()

        from ai.providers.openai_client import OpenAIClient

        client = OpenAIClient()
        # Uses fallback approximation (len // 4) when tiktoken is not available
        result = client.count_tokens("hello world this is a test")
        assert isinstance(result, int)
        assert result > 0


class TestOllamaClient:
    """Tests for the Ollama client implementation."""

    @override_settings(
        LLM_ENABLED=True,
        LLM_PROVIDER="ollama",
        LLM_API_ENDPOINT="http://localhost:11434",
    )
    @patch("ai.providers.ollama_client.ollama")
    def test_generate_returns_text(self, mock_ollama):
        """generate() returns the message content from the Ollama response."""
        mock_inner = MagicMock()
        mock_ollama.Client.return_value = mock_inner

        mock_response = MagicMock()
        mock_response.message.content = "Ollama response text"
        mock_inner.chat.return_value = mock_response

        from ai.providers.ollama_client import OllamaClient

        client = OllamaClient()
        result = client.generate("Tell me something")
        assert result == "Ollama response text"

    @override_settings(
        LLM_ENABLED=True,
        LLM_PROVIDER="ollama",
        LLM_API_ENDPOINT="http://localhost:11434",
    )
    @patch("ai.providers.ollama_client.ollama")
    def test_embed_returns_vector(self, mock_ollama):
        """embed() returns the embedding vector from the Ollama response."""
        mock_inner = MagicMock()
        mock_ollama.Client.return_value = mock_inner

        mock_response = MagicMock()
        mock_response.embeddings = [[0.5, 0.6, 0.7]]
        mock_inner.embed.return_value = mock_response

        from ai.providers.ollama_client import OllamaClient

        client = OllamaClient()
        result = client.embed("some text")
        assert result == [0.5, 0.6, 0.7]

    @override_settings(
        LLM_ENABLED=True,
        LLM_PROVIDER="ollama",
        LLM_API_ENDPOINT="http://localhost:11434",
    )
    @patch("ai.providers.ollama_client.ollama")
    def test_embed_batch_returns_vectors(self, mock_ollama):
        """embed_batch() returns a list of embedding vectors from Ollama."""
        mock_inner = MagicMock()
        mock_ollama.Client.return_value = mock_inner

        mock_response = MagicMock()
        mock_response.embeddings = [[0.1, 0.2], [0.3, 0.4]]
        mock_inner.embed.return_value = mock_response

        from ai.providers.ollama_client import OllamaClient

        client = OllamaClient()
        result = client.embed_batch(["text one", "text two"])
        assert result == [[0.1, 0.2], [0.3, 0.4]]
