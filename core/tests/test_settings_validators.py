import pytest
from django.core.exceptions import ImproperlyConfigured

from docvault.settings.validators import redis_database_url, validate_secret_key_for_production


@pytest.mark.parametrize(
    "secret_key",
    [
        "",
        "change-me-in-production",
        "dev-secret-key-change-in-production",
        "insecure-dev-key-change-in-production",
        "my-change-me-secret",
        "insecure-value",
    ],
)
def test_production_secret_validator_rejects_placeholders(secret_key):
    with pytest.raises(ImproperlyConfigured):
        validate_secret_key_for_production(secret_key)


def test_production_secret_validator_accepts_non_placeholder():
    validate_secret_key_for_production("ci-secret-key-not-for-production")


@pytest.mark.parametrize("url", ["redis://localhost:6379", "redis://localhost:6379/", "redis://localhost:6379/7"])
def test_redis_database_url_replaces_existing_database_path(url):
    assert redis_database_url(url, 1) == "redis://localhost:6379/1"


def test_redis_database_url_preserves_tls_credentials_and_options():
    assert redis_database_url("rediss://user:password@cache.example:6380/5?socket_timeout=3", 0) == (
        "rediss://user:password@cache.example:6380/0?socket_timeout=3"
    )
