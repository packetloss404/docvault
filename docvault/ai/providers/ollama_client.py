"""Ollama LLM provider implementation."""

import logging
import time

import ollama
from django.conf import settings

from ..client import LLMClient
from ..constants import (
    DEFAULT_EMBEDDING_MODEL_OLLAMA,
    DEFAULT_OLLAMA_MODEL,
    EMBEDDING_DIM_OLLAMA,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 1.0


class OllamaClient(LLMClient):
    """Ollama local LLM client implementation."""

    def __init__(self):
        api_endpoint = getattr(settings, "LLM_API_ENDPOINT", "http://localhost:11434")
        self._client = ollama.Client(host=api_endpoint)
        self._model = getattr(settings, "LLM_MODEL", DEFAULT_OLLAMA_MODEL)
        self._embedding_model = getattr(
            settings, "EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL_OLLAMA
        )
        self._embedding_dim = getattr(settings, "EMBEDDING_DIM", EMBEDDING_DIM_OLLAMA)

    def generate(self, prompt: str, context: str = "", **kwargs) -> str:
        full_prompt = prompt
        if context:
            full_prompt = (
                f"Use the following document content as context:\n\n{context}\n\n"
                f"Now answer this question:\n{prompt}"
            )

        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.chat(
                    model=self._model,
                    messages=[{"role": "user", "content": full_prompt}],
                    options={
                        "temperature": kwargs.get("temperature", 0.3),
                        "num_predict": kwargs.get("max_tokens", 2000),
                    },
                )
                return response.message.content or ""
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "Ollama generate failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e,
                    )
                    time.sleep(wait)
                else:
                    logger.error("Ollama generate failed after %d attempts: %s", MAX_RETRIES, e)
                    raise

    def embed(self, text: str) -> list[float]:
        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.embed(
                    model=self._embedding_model,
                    input=text,
                )
                return response.embeddings[0]
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "Ollama embed failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e,
                    )
                    time.sleep(wait)
                else:
                    logger.error("Ollama embed failed after %d attempts: %s", MAX_RETRIES, e)
                    raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.embed(
                    model=self._embedding_model,
                    input=texts,
                )
                return response.embeddings
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "Ollama embed_batch failed (attempt %d/%d): %s",
                        attempt + 1, MAX_RETRIES, e,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "Ollama embed_batch failed after %d attempts: %s", MAX_RETRIES, e,
                    )
                    raise

    def count_tokens(self, text: str) -> int:
        # Rough approximation for Ollama models: ~4 chars per token
        return len(text) // 4

    @property
    def embedding_dimension(self) -> int:
        return self._embedding_dim
