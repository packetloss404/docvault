"""Azure OpenAI LLM provider implementation."""

import logging
import os
import time

import openai
from django.conf import settings

from ..client import LLMClient
from ..constants import (
    DEFAULT_EMBEDDING_MODEL_OPENAI,
    EMBEDDING_DIM_OPENAI,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 1.0

DEFAULT_AZURE_DEPLOYMENT = "gpt-4o-mini"
DEFAULT_AZURE_EMBEDDING_DEPLOYMENT = "text-embedding-3-small"


class AzureOpenAIClient(LLMClient):
    """Azure OpenAI API client implementation.

    Reads configuration from Django settings (preferred) with fallback to
    environment variables:
        AZURE_OPENAI_ENDPOINT   — e.g. https://<resource>.openai.azure.com/
        AZURE_OPENAI_API_KEY    — Azure API key
        AZURE_OPENAI_DEPLOYMENT — deployment / model name (e.g. gpt-4o-mini)
    """

    def __init__(self):
        endpoint = (
            getattr(settings, "AZURE_OPENAI_ENDPOINT", None)
            or os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        )
        api_key = (
            getattr(settings, "AZURE_OPENAI_API_KEY", None)
            or os.environ.get("AZURE_OPENAI_API_KEY", "")
        )
        deployment = (
            getattr(settings, "AZURE_OPENAI_DEPLOYMENT", None)
            or os.environ.get("AZURE_OPENAI_DEPLOYMENT", DEFAULT_AZURE_DEPLOYMENT)
        )
        embedding_deployment = getattr(
            settings, "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", None
        ) or os.environ.get(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", DEFAULT_AZURE_EMBEDDING_DEPLOYMENT
        )

        if not endpoint:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT must be set in settings or environment "
                "to use the Azure OpenAI provider."
            )
        if not api_key:
            raise ValueError(
                "AZURE_OPENAI_API_KEY must be set in settings or environment "
                "to use the Azure OpenAI provider."
            )

        self._client = openai.AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=getattr(settings, "AZURE_OPENAI_API_VERSION", "2024-02-01"),
            timeout=60.0,
        )
        self._deployment = deployment
        self._embedding_deployment = embedding_deployment

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
                    model=self._deployment,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "Azure OpenAI generate failed (attempt %d/%d): %s. Retrying in %.1fs",
                        attempt + 1, MAX_RETRIES, e, wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "Azure OpenAI generate failed after %d attempts: %s", MAX_RETRIES, e
                    )
                    raise

    def embed(self, text: str) -> list[float]:
        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.embeddings.create(
                    model=self._embedding_deployment,
                    input=text,
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "Azure OpenAI embed failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e,
                    )
                    time.sleep(wait)
                else:
                    logger.error("Azure OpenAI embed failed after %d attempts: %s", MAX_RETRIES, e)
                    raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.embeddings.create(
                    model=self._embedding_deployment,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "Azure OpenAI embed_batch failed (attempt %d/%d): %s",
                        attempt + 1, MAX_RETRIES, e,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "Azure OpenAI embed_batch failed after %d attempts: %s", MAX_RETRIES, e,
                    )
                    raise

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken

            encoding = tiktoken.encoding_for_model(self._deployment)
            return len(encoding.encode(text))
        except Exception:
            # Rough approximation: ~4 chars per token
            return len(text) // 4

    @property
    def embedding_dimension(self) -> int:
        return EMBEDDING_DIM_OPENAI
