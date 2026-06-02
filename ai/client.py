"""LLM client abstraction layer."""

import logging
from abc import ABC, abstractmethod

from django.conf import settings

from .constants import PROVIDER_AZURE, PROVIDER_OLLAMA, PROVIDER_OPENAI

logger = logging.getLogger(__name__)

_client = None


class LLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, context: str = "", **kwargs) -> str:
        """Generate a text response from the LLM.

        Args:
            prompt: The user prompt / instruction.
            context: Optional context (e.g. document content) to include.
            **kwargs: Provider-specific options (temperature, max_tokens, etc.).

        Returns:
            The generated text response.
        """

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of texts.

        Args:
            texts: List of texts to embed.

        Returns:
            A list of embedding vectors.
        """

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in the given text.

        Args:
            text: The text to count tokens for.

        Returns:
            The number of tokens.
        """

    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Return the dimension of embedding vectors produced by this provider."""


def get_llm_client() -> LLMClient | None:
    """Return a configured LLM client, or None if LLM is disabled."""
    global _client
    if _client is not None:
        return _client

    if not getattr(settings, "LLM_ENABLED", False):
        return None

    provider = getattr(settings, "LLM_PROVIDER", "").lower()

    if provider == PROVIDER_OPENAI:
        from .providers.openai_client import OpenAIClient

        _client = OpenAIClient()
    elif provider == PROVIDER_OLLAMA:
        from .providers.ollama_client import OllamaClient

        _client = OllamaClient()
    elif provider == PROVIDER_AZURE:
        from .providers.azure_client import AzureOpenAIClient

        _client = AzureOpenAIClient()
    else:
        logger.warning("Unknown LLM provider: %s", provider)
        return None

    return _client


def reset_client():
    """Reset the client singleton (for testing)."""
    global _client
    _client = None
