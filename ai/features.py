"""AI-powered document features: summarization, entity extraction, smart titles."""

import json
import logging

from .client import get_llm_client

logger = logging.getLogger(__name__)


def summarize_document(document_id: int) -> dict:
    """Generate a summary for a document.

    Returns:
        Dict with 'summary' key.
    """
    client = get_llm_client()
    if not client:
        return {"summary": None, "error": "AI features are not enabled."}

    from documents.models import Document

    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        return {"summary": None, "error": "Document not found."}

    content = document.content or ""
    if not content.strip():
        return {"summary": None, "error": "Document has no text content."}

    # Truncate if needed
    max_chars = 20000
    if len(content) > max_chars:
        content = content[:max_chars] + "..."

    prompt = (
        "Provide a concise summary of the following document in 2-4 sentences. "
        "Focus on the key points, purpose, and any important details like dates, "
        "amounts, or parties involved."
    )

    summary = client.generate(prompt, context=content)
    return {"summary": summary}


def extract_entities(document_id: int) -> dict:
    """Extract named entities from a document.

    Returns:
        Dict with 'entities' key containing categorized entities.
    """
    client = get_llm_client()
    if not client:
        return {"entities": None, "error": "AI features are not enabled."}

    from documents.models import Document

    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        return {"entities": None, "error": "Document not found."}

    content = document.content or ""
    if not content.strip():
        return {"entities": None, "error": "Document has no text content."}

    max_chars = 15000
    if len(content) > max_chars:
        content = content[:max_chars] + "..."

    prompt = (
        "Extract named entities from the following document. Return a JSON object with "
        "these categories: dates, amounts, names, organizations, addresses, emails, "
        "phone_numbers. Each category should be a list of strings. Only include entities "
        "that are clearly present. Return ONLY the JSON object, no other text."
    )

    response = client.generate(prompt, context=content, temperature=0.1)

    try:
        # Try to parse JSON from the response
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1].rsplit("```", 1)[0]
        entities = json.loads(response)
    except (json.JSONDecodeError, IndexError):
        logger.warning("Failed to parse entity extraction response as JSON")
        entities = {"raw": response}

    return {"entities": entities}


def suggest_title(document_id: int) -> dict:
    """Suggest a better title for a document based on its content.

    Returns:
        Dict with 'suggested_title' key.
    """
    client = get_llm_client()
    if not client:
        return {"suggested_title": None, "error": "AI features are not enabled."}

    from documents.models import Document

    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        return {"suggested_title": None, "error": "Document not found."}

    content = document.content or ""
    if not content.strip():
        return {"suggested_title": None, "error": "Document has no text content."}

    max_chars = 5000
    if len(content) > max_chars:
        content = content[:max_chars] + "..."

    prompt = (
        f"The current title of this document is: \"{document.title}\"\n\n"
        "Based on the document content, suggest a concise, descriptive title "
        "(maximum 100 characters). The title should clearly identify what the "
        "document is about. Return ONLY the suggested title, nothing else."
    )

    suggested = client.generate(prompt, context=content, temperature=0.3)
    # Clean up: remove quotes if LLM wraps in them
    suggested = suggested.strip().strip('"').strip("'")
    if len(suggested) > 128:
        suggested = suggested[:125] + "..."

    return {"suggested_title": suggested}
