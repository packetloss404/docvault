"""Document embedding generation and text chunking."""

import logging

from .client import get_llm_client
from .constants import CHUNK_OVERLAP, CHUNK_SIZE, MAX_CONTEXT_TOKENS

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by word count.

    Args:
        text: The text to split.
        chunk_size: Max words per chunk.
        overlap: Number of overlapping words between chunks.

    Returns:
        A list of text chunks.
    """
    words = text.split()
    if len(words) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def build_embedding_text(document) -> str:
    """Build the text representation of a document for embedding.

    Combines title, metadata, and content into a single string,
    truncated to fit within token limits.
    """
    parts = []

    if document.title:
        parts.append(f"Title: {document.title}")

    if document.correspondent:
        parts.append(f"Correspondent: {document.correspondent.name}")

    if document.document_type:
        parts.append(f"Type: {document.document_type.name}")

    tags = document.tags.all()
    if tags:
        tag_names = ", ".join(t.name for t in tags)
        parts.append(f"Tags: {tag_names}")

    header = "\n".join(parts)

    content = document.content or ""
    client = get_llm_client()
    if client:
        max_content_tokens = MAX_CONTEXT_TOKENS - client.count_tokens(header) - 100
        content_tokens = client.count_tokens(content)
        if content_tokens > max_content_tokens:
            # Truncate content to fit within limits
            ratio = max_content_tokens / content_tokens
            content = content[: int(len(content) * ratio)]

    if content:
        parts.append(f"\nContent:\n{content}")

    return "\n".join(parts)


def generate_document_embedding(document) -> list[float] | None:
    """Generate an embedding vector for a document.

    Returns:
        The embedding vector, or None if LLM is not available.
    """
    client = get_llm_client()
    if not client:
        return None

    text = build_embedding_text(document)
    if not text.strip():
        return None

    return client.embed(text)


def generate_query_embedding(query: str) -> list[float] | None:
    """Generate an embedding vector for a search query.

    Returns:
        The embedding vector, or None if LLM is not available.
    """
    client = get_llm_client()
    if not client:
        return None

    return client.embed(query)


def generate_chunk_embeddings(text: str) -> list[tuple[str, list[float]]]:
    """Generate embeddings for each chunk of a document.

    Returns:
        List of (chunk_text, embedding_vector) tuples.
    """
    client = get_llm_client()
    if not client:
        return []

    chunks = chunk_text(text)
    if not chunks:
        return []

    embeddings = client.embed_batch(chunks)
    return list(zip(chunks, embeddings))
