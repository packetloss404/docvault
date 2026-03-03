"""Helper functions for named-entity extraction."""

import logging
import re

logger = logging.getLogger(__name__)

# Module-level cache for the spaCy model (singleton).
_spacy_model = None


def get_spacy_model():
    """Return the configured spaCy NLP model, loading it once and caching."""
    global _spacy_model
    if _spacy_model is not None:
        return _spacy_model

    from django.conf import settings

    model_name = getattr(settings, "NER_SPACY_MODEL", "en_core_web_sm")

    try:
        import spacy
        _spacy_model = spacy.load(model_name)
        logger.info("Loaded spaCy model: %s", model_name)
        return _spacy_model
    except ImportError:
        logger.warning("spaCy is not installed; NER will fall back to regex only.")
        return None
    except OSError:
        logger.warning(
            "spaCy model '%s' not found. Install it with: "
            "python -m spacy download %s",
            model_name,
            model_name,
        )
        return None


def extract_entities_spacy(content, max_length=100000):
    """Extract named entities from *content* using spaCy.

    Returns a list of dicts::

        [
            {
                "label": "PERSON",   # spaCy label
                "value": "John Doe",
                "start": 0,
                "end": 8,
            },
            ...
        ]
    """
    nlp = get_spacy_model()
    if nlp is None:
        return []

    # Truncate very long documents to stay within spaCy memory limits.
    text = content[:max_length] if len(content) > max_length else content

    try:
        doc = nlp(text)
        entities = []
        for ent in doc.ents:
            entities.append({
                "label": ent.label_,
                "value": ent.text.strip(),
                "start": ent.start_char,
                "end": ent.end_char,
            })
        return entities
    except Exception:
        logger.exception("spaCy extraction failed")
        return []


def extract_entities_regex(content, entity_types):
    """Extract entities using custom regex patterns defined on *entity_types*.

    Parameters
    ----------
    content : str
        The document text to scan.
    entity_types : iterable of EntityType
        Only types with a non-empty ``extraction_pattern`` are used.

    Returns a list of dicts with the same shape as ``extract_entities_spacy``.
    """
    results = []
    for et in entity_types:
        pattern = et.extraction_pattern
        if not pattern or not pattern.strip():
            continue
        try:
            compiled = re.compile(pattern)
            for match in compiled.finditer(content):
                results.append({
                    "label": et.name,
                    "value": match.group(0).strip(),
                    "start": match.start(),
                    "end": match.end(),
                })
        except re.error:
            logger.warning(
                "Invalid regex pattern for entity type '%s': %s",
                et.name,
                pattern,
            )
    return results


def normalize_entity_value(value, entity_type_name):
    """Return a normalised version of *value* suitable for grouping.

    - Strips leading/trailing whitespace.
    - Collapses internal whitespace.
    - Title-cases PERSON names.
    - Upper-cases ORGANIZATION names.
    - Leaves other types as-is after whitespace normalisation.
    """
    value = " ".join(value.split())

    if entity_type_name == "PERSON":
        return value.title()
    if entity_type_name == "ORGANIZATION":
        return value.upper()

    return value
