"""Validation helpers for settings modules."""

from django.core.exceptions import ImproperlyConfigured

PLACEHOLDER_SECRET_KEYS = frozenset(
    {
        "",
        "change-me-in-production",
        "dev-secret-key-change-in-production",
        "insecure-dev-key-change-in-production",
    }
)


def validate_secret_key_for_production(secret_key: str) -> None:
    """Reject missing or known development placeholder Django secret keys."""
    normalized = (secret_key or "").strip().lower()
    if normalized in PLACEHOLDER_SECRET_KEYS or "change-me" in normalized or "insecure" in normalized:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set to a unique, non-placeholder value for production."
        )
