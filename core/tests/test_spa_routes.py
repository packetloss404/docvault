import pytest
from django.urls import resolve

from docvault.urls import spa_fallback


@pytest.mark.parametrize("screen", ["users", "groups", "roles", "storage", "permissions"])
@pytest.mark.parametrize("suffix", ["", "/"])
def test_angular_admin_deep_links_resolve_to_the_spa(screen, suffix):
    assert resolve(f"/admin/{screen}{suffix}").func is spa_fallback


@pytest.mark.parametrize("url", ["/admin/", "/admin/login/", "/admin/auth/user/"])
def test_django_admin_keeps_its_existing_routes(url):
    assert resolve(url).namespace == "admin"
