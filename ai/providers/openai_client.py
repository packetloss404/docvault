"""OpenAI LLM provider implementation."""

import logging
import time

import openai
from django.conf import settings

from ..client import LLMClient
from ..constants import (
    DEFAULT_EMBEDDING_MODEL_OPENAI,
    DEFAULT_OPENAI_MODEL,
    EMBEDDING_DIM_OPENAI,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 1.0


class OpenAIClient(LLMClient):
    """OpenAI API client implementation."""

    def __init__(self):
        api_key = getattr(settings, "LLM_API_KEY", "")
        api_endpoint = getattr(settings, "LLM_API_ENDPOINT", None)

        kwargs = {"api_key": api_key, "timeout": 60.0}
        if api_endpoint:
            kwargs["base_url"] = api_endpoint

        self._client = openai.OpenAI(**kwargs)
        self._model = getattr(settings, "LLM_MODEL", DEFAULT_OPENAI_MODEL)
        self._embedding_model = getattr(
            settings, "EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL_OPENAI
        )

    def generate(self, prompt: str, context: str = "", **kwargs) -> str:
        messages = []
        if context:
            messages.append({
                "role": "system",
                "content": f"Use the following document content as context:\n\n{context}",
            })
        messages.append({"role": "user", "content": prompt})

        temperature = kwargs.get("temperature", 0.3)
        max_tokens = kwargs.get("max_tokens", 2000)

        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "OpenAI generate failed (attempt %d/%d): %s. Retrying in %.1fs",
                        attempt + 1, MAX_RETRIES, e, wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error("OpenAI generate failed after %d attempts: %s", MAX_RETRIES, e)
                    raise

    def embed(self, text: str) -> list[float]:
        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.embeddings.create(
                    model=self._embedding_model,
                    input=text,
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "OpenAI embed failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e,
                    )
                    time.sleep(wait)
                else:
                    logger.error("OpenAI embed failed after %d attempts: %s", MAX_RETRIES, e)
                    raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.embeddings.create(
                    model=self._embedding_model,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "OpenAI embed_batch failed (attempt %d/%d): %s",
                        attempt + 1, MAX_RETRIES, e,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "OpenAI embed_batch failed after %d attempts: %s", MAX_RETRIES, e,
                    )
                    raise

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken

            encoding = tiktoken.encoding_for_model(self._model)
            return len(encoding.encode(text))
        except Exception:
            # Rough approximation: ~4 chars per token
            return len(text) // 4

    @property
    def embedding_dimension(self) -> int:
        return EMBEDDING_DIM_OPENAI
