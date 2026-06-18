import pytest
from django.core.exceptions import ImproperlyConfigured

from docvault.settings.validators import validate_secret_key_for_production


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
