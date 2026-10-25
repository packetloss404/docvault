import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
@pytest.mark.parametrize("enabled", ["", "1"])
def test_acceptance_seed_refuses_normal_settings_even_if_flag_is_present(monkeypatch, enabled):
    monkeypatch.setenv("DOCVAULT_E2E", enabled)
    with pytest.raises(CommandError, match="Refusing to seed accounts"):
        call_command("seed_e2e")
    assert not User.objects.filter(username__startswith="e2e-").exists()
