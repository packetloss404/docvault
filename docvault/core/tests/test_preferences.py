"""Tests for UserPreferences model and API endpoint."""

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
from rest_framework.test import APIClient

from core.preferences import UserPreferences


@pytest.fixture
def user(db):
    return User.objects.create_user("testuser", "test@example.com", "pass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class TestUserPreferencesModel:
    """Tests for the UserPreferences Django model."""

    @pytest.mark.django_db
    def test_create_preferences(self, user):
        prefs = UserPreferences.objects.create(user=user)
        assert prefs.theme == "system"
        assert prefs.language == "en"
        assert prefs.dashboard_layout == []

    @pytest.mark.django_db
    def test_str_representation(self, user):
        prefs = UserPreferences.objects.create(user=user)
        assert str(prefs) == "Preferences(testuser)"

    @pytest.mark.django_db
    def test_one_to_one_constraint(self, user):
        UserPreferences.objects.create(user=user)
        with pytest.raises(IntegrityError):
            UserPreferences.objects.create(user=user)

    @pytest.mark.django_db
    def test_theme_default(self, user):
        prefs = UserPreferences.objects.create(user=user)
        assert prefs.theme == UserPreferences.THEME_SYSTEM

    @pytest.mark.django_db
    def test_theme_choices(self, user):
        prefs = UserPreferences.objects.create(user=user, theme="dark")
        assert prefs.theme == "dark"
        prefs.theme = "light"
        prefs.save()
        prefs.refresh_from_db()
        assert prefs.theme == "light"

    @pytest.mark.django_db
    def test_dashboard_layout_stores_json(self, user):
        layout = ["statistics", "recent_documents", "upload"]
        prefs = UserPreferences.objects.create(user=user, dashboard_layout=layout)
        prefs.refresh_from_db()
        assert prefs.dashboard_layout == layout

    @pytest.mark.django_db
    def test_user_deletion_cascades(self, user):
        UserPreferences.objects.create(user=user)
        assert UserPreferences.objects.count() == 1
        user.delete()
        assert UserPreferences.objects.count() == 0


class TestUserPreferencesAPI:
    """Tests for the GET/PATCH /api/v1/preferences/ endpoint."""

    @pytest.mark.django_db
    def test_get_preferences_creates_if_missing(self, auth_client):
        response = auth_client.get("/api/v1/preferences/")
        assert response.status_code == 200
        assert response.data["theme"] == "system"
        assert response.data["language"] == "en"
        assert response.data["dashboard_layout"] == []

    @pytest.mark.django_db
    def test_get_preferences_returns_existing(self, auth_client, user):
        UserPreferences.objects.create(user=user, theme="dark", language="de")
        response = auth_client.get("/api/v1/preferences/")
        assert response.status_code == 200
        assert response.data["theme"] == "dark"
        assert response.data["language"] == "de"

    @pytest.mark.django_db
    def test_patch_theme_to_dark(self, auth_client):
        response = auth_client.patch(
            "/api/v1/preferences/", {"theme": "dark"}, format="json"
        )
        assert response.status_code == 200
        assert response.data["theme"] == "dark"

    @pytest.mark.django_db
    def test_patch_theme_to_light(self, auth_client):
        response = auth_client.patch(
            "/api/v1/preferences/", {"theme": "light"}, format="json"
        )
        assert response.status_code == 200
        assert response.data["theme"] == "light"

    @pytest.mark.django_db
    def test_patch_theme_to_system(self, auth_client):
        # First set to dark, then back to system
        auth_client.patch(
            "/api/v1/preferences/", {"theme": "dark"}, format="json"
        )
        response = auth_client.patch(
            "/api/v1/preferences/", {"theme": "system"}, format="json"
        )
        assert response.status_code == 200
        assert response.data["theme"] == "system"

    @pytest.mark.django_db
    def test_patch_invalid_theme_is_ignored(self, auth_client):
        # Create preferences first
        auth_client.get("/api/v1/preferences/")
        response = auth_client.patch(
            "/api/v1/preferences/", {"theme": "neon"}, format="json"
        )
        assert response.status_code == 200
        # Should remain the default since "neon" is not a valid choice
        assert response.data["theme"] == "system"

    @pytest.mark.django_db
    def test_patch_language(self, auth_client):
        response = auth_client.patch(
            "/api/v1/preferences/", {"language": "de"}, format="json"
        )
        assert response.status_code == 200
        assert response.data["language"] == "de"

    @pytest.mark.django_db
    def test_patch_dashboard_layout(self, auth_client):
        layout = ["statistics", "recent_documents", "upload"]
        response = auth_client.patch(
            "/api/v1/preferences/", {"dashboard_layout": layout}, format="json"
        )
        assert response.status_code == 200
        assert response.data["dashboard_layout"] == layout

    @pytest.mark.django_db
    def test_patch_multiple_fields(self, auth_client):
        response = auth_client.patch(
            "/api/v1/preferences/",
            {"theme": "dark", "language": "fr", "dashboard_layout": ["upload"]},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["theme"] == "dark"
        assert response.data["language"] == "fr"
        assert response.data["dashboard_layout"] == ["upload"]

    @pytest.mark.django_db
    def test_patch_persists_changes(self, auth_client):
        auth_client.patch(
            "/api/v1/preferences/", {"theme": "dark"}, format="json"
        )
        # Fetch again to verify persistence
        response = auth_client.get("/api/v1/preferences/")
        assert response.data["theme"] == "dark"

    @pytest.mark.django_db
    def test_unauthenticated_get_returns_401_or_403(self):
        client = APIClient()
        response = client.get("/api/v1/preferences/")
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_unauthenticated_patch_returns_401_or_403(self):
        client = APIClient()
        response = client.patch(
            "/api/v1/preferences/", {"theme": "dark"}, format="json"
        )
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_preferences_isolated_per_user(self, auth_client, user):
        # Set preferences for first user
        auth_client.patch(
            "/api/v1/preferences/", {"theme": "dark"}, format="json"
        )
        # Create second user with their own client
        user2 = User.objects.create_user("user2", "user2@example.com", "pass123")
        client2 = APIClient()
        client2.force_authenticate(user=user2)
        response = client2.get("/api/v1/preferences/")
        # Second user should have default preferences, not user 1's
        assert response.data["theme"] == "system"
