"""Matching algorithm implementations for auto-assigning organization objects to documents."""

import logging
import re

from documents.constants import (
    MATCH_ALL,
    MATCH_ANY,
    MATCH_AUTO,
    MATCH_FUZZY,
    MATCH_LITERAL,
    MATCH_NONE,
    MATCH_REGEX,
)

logger = logging.getLogger(__name__)


def matches(matching_obj, document_content: str) -> bool:
    """
    Check if a matching object (Tag, Correspondent, etc.) matches the document content.

    Args:
        matching_obj: An object with matching_algorithm, match, and is_insensitive fields.
        document_content: The text content of the document.

    Returns:
        True if the object matches the document content.
    """
    algorithm = matching_obj.matching_algorithm
    pattern = matching_obj.match
    insensitive = matching_obj.is_insensitive

    if algorithm == MATCH_NONE:
        return False

    if not pattern or not document_content:
        return False

    if algorithm == MATCH_ANY:
        return _match_any(pattern, document_content, insensitive)
    elif algorithm == MATCH_ALL:
        return _match_all(pattern, document_content, insensitive)
    elif algorithm == MATCH_LITERAL:
        return _match_literal(pattern, document_content, insensitive)
    elif algorithm == MATCH_REGEX:
        return _match_regex(pattern, document_content, insensitive)
    elif algorithm == MATCH_FUZZY:
        return _match_fuzzy(pattern, document_content, insensitive)
    elif algorithm == MATCH_AUTO:
        return _match_auto(matching_obj, document_content)

    return False


def _match_any(pattern: str, content: str, insensitive: bool) -> bool:
    """Match if any word from the pattern is present in content."""
    words = pattern.split()
    if insensitive:
        content_lower = content.lower()
        return any(word.lower() in content_lower for word in words)
    return any(word in content for word in words)


def _match_all(pattern: str, content: str, insensitive: bool) -> bool:
    """Match if all words from the pattern are present in content."""
    words = pattern.split()
    if not words:
        return False
    if insensitive:
        content_lower = content.lower()
        return all(word.lower() in content_lower for word in words)
    return all(word in content for word in words)


def _match_literal(pattern: str, content: str, insensitive: bool) -> bool:
    """Match if the exact string pattern is found in content."""
    if insensitive:
        return pattern.lower() in content.lower()
    return pattern in content


def _match_regex(pattern: str, content: str, insensitive: bool) -> bool:
    """Match using a regex pattern."""
    flags = re.IGNORECASE if insensitive else 0
    try:
        return bool(re.search(pattern, content, flags))
    except re.error:
        logger.warning("Invalid regex pattern: %s", pattern)
        return False


def _match_fuzzy(pattern: str, content: str, insensitive: bool) -> bool:
    """Fuzzy match - checks if any word from pattern approximately matches content words."""
    from difflib import SequenceMatcher

    threshold = 0.85
    pattern_words = pattern.split()
    content_words = content.split()

    if insensitive:
        pattern_words = [w.lower() for w in pattern_words]
        content_words = [w.lower() for w in content_words]

    # Limit content words for performance
    content_words = content_words[:5000]

    for pw in pattern_words:
        found = False
        for cw in content_words:
            ratio = SequenceMatcher(None, pw, cw).ratio()
            if ratio >= threshold:
                found = True
                break
        if found:
            return True
    return False


def _match_auto(matching_obj, content: str) -> bool:
    """ML-based matching using the trained classifier.

    Checks if the classifier predicts this object as a match for the
    given content with sufficient confidence (>= 0.5).
    """
    try:
        from ml.classifier import get_classifier
    except ImportError:
        return False

    classifier = get_classifier()
    if classifier is None:
        return False

    # Determine which prediction method to use based on the model type
    from organization.models import Correspondent, StoragePath, Tag

    obj_id = matching_obj.pk

    if isinstance(matching_obj, Tag):
        predictions = classifier.predict_tags(content)
        return any(tid == obj_id for tid, _ in predictions)

    elif isinstance(matching_obj, Correspondent):
        predictions = classifier.predict_correspondent(content)
        return any(cid == obj_id and conf >= 0.5 for cid, conf in predictions)

    elif isinstance(matching_obj, StoragePath):
        predictions = classifier.predict_storage_path(content)
        return any(spid == obj_id and conf >= 0.5 for spid, conf in predictions)

    else:
        # DocumentType or other model
        from documents.models.document_type import DocumentType

        if isinstance(matching_obj, DocumentType):
            predictions = classifier.predict_document_type(content)
            return any(dtid == obj_id and conf >= 0.5 for dtid, conf in predictions)

    return False


def get_matching_objects(queryset, document_content: str):
    """
    Find all objects from the queryset that match the document content.

    Args:
        queryset: A queryset of matching objects (Tags, Correspondents, etc.)
        document_content: The text content of the document.

    Returns:
        List of matching objects.
    """
    results = []
    for obj in queryset.exclude(matching_algorithm=MATCH_NONE):
        if matches(obj, document_content):
            results.append(obj)
    return results
