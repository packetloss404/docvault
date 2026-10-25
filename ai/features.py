"""AI-powered document features: summarization, entity extraction, smart titles."""

import json
import logging

from .client import get_llm_client

logger = logging.getLogger(__name__)

ENTITY_DESCRIPTIONS = {
    "names": "Person names exactly as written in the document, without expanding or resolving their identity.",
    "organizations": "Names of organizations explicitly named in the document, copied verbatim.",
    "dates": "Date expressions actually written in the document, without inferring historical dates.",
    "amounts": "Amounts actually written in the document, preserving their original currency or unit text.",
    "addresses": "Addresses or place names actually written in the document, copied verbatim.",
    "emails": "Email addresses actually written in the document, copied verbatim.",
    "phone_numbers": "Phone numbers actually written in the document, copied verbatim.",
}
ENTITY_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        category: {"type": "array", "items": {"type": "string"}, "description": description}
        for category, description in ENTITY_DESCRIPTIONS.items()
    },
    "required": list(ENTITY_DESCRIPTIONS),
    "additionalProperties": False,
}
ENTITY_EXAMPLES = [{
    "document": "Mira Soland paid 75 dollars in Paris.",
    "response": {
        "names": ["Mira Soland"], "organizations": [], "dates": [], "amounts": ["75 dollars"],
        "addresses": ["Paris"], "emails": [], "phone_numbers": [],
    },
}]


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
        "Summarize only the facts explicitly stated in the supplied document in 2-4 sentences. "
        "Preserve its important identifiers, amounts and named parties. "
        "Do not add facts from memory or claim that information is missing when it is present. "
        "Return the summary directly, without a preamble."
    )

    summary = client.generate(prompt, context=content, temperature=0, seed=0)
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
        "Extract person names, organization names, date mentions, monetary amounts, places and addresses, "
        "emails and phone numbers. Every value must be copied exactly from the user document. "
        "Do not expand names or invent dates. Empty arrays mean the category is absent. "
        "Return only a JSON object with string-list fields: names, organizations, dates, amounts, "
        "addresses, emails, phone_numbers."
    )

    try:
        response = client.generate(
            prompt, context=content, temperature=0, seed=0,
            json_schema=ENTITY_RESPONSE_SCHEMA, examples=ENTITY_EXAMPLES,
        )
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1].rsplit("```", 1)[0]
        entities = json.loads(response)
        if not isinstance(entities, dict) or set(entities) != set(ENTITY_DESCRIPTIONS):
            raise ValueError("Unexpected entity categories")
        normalized_content = " ".join(content.casefold().split())
        for values in entities.values():
            if not isinstance(values, list):
                raise ValueError("Entity categories must contain lists")
            for value in values:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError("Entities must be nonempty strings")
                if " ".join(value.casefold().split()) not in normalized_content:
                    raise ValueError("Entity value is absent from the document")
    except (ValueError, TypeError, IndexError):
        logger.warning("Entity extraction returned invalid or ungrounded output")
        return {
            "entities": None,
            "error": "Entity extraction did not return valid source-grounded data.",
            "error_code": "invalid_model_output",
        }

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
