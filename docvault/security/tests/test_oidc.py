"""Tests for OIDC authentication backend and utilities."""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import Group, User
from django.test import override_settings

from security.oidc import (
    DocVaultOIDCBackend,
    create_oidc_user,
    map_groups,
    update_oidc_user,
)


@pytest.mark.django_db
class TestCreateOidcUser:
    """Tests for create_oidc_user."""

    def test_creates_user_from_claims(self):
        claims = {
            "preferred_username": "oidcuser",
            "email": "oidc@example.com",
            "given_name": "OIDC",
            "family_name": "User",
        }
        user = create_oidc_user(claims)
        assert user.username == "oidcuser"
        assert user.email == "oidc@example.com"
        assert user.first_name == "OIDC"
        assert user.last_name == "User"

    def test_falls_back_to_sub_for_username(self):
        claims = {
            "sub": "sub-12345",
            "email": "sub@example.com",
        }
        user = create_oidc_user(claims)
        assert user.username == "sub-12345"


@pytest.mark.django_db
class TestUpdateOidcUser:
    """Tests for update_oidc_user."""

    def test_updates_fields(self):
        user = User.objects.create_user("existing", email="old@example.com")
        claims = {
            "email": "new@example.com",
            "given_name": "New",
            "family_name": "Name",
        }
        updated = update_oidc_user(user, claims)
        updated.refresh_from_db()
        assert updated.email == "new@example.com"
        assert updated.first_name == "New"
        assert updated.last_name == "Name"

    def test_no_save_when_unchanged(self):
        user = User.objects.create_user(
            "nochange", email="same@example.com", first_name="Same", last_name="Name"
        )
        claims = {
            "email": "same@example.com",
            "given_name": "Same",
            "family_name": "Name",
        }
        # Should not raise or change anything
        updated = update_oidc_user(user, claims)
        assert updated.email == "same@example.com"


@pytest.mark.django_db
class TestMapGroups:
    """Tests for map_groups."""

    def test_creates_and_assigns_groups(self):
        user = User.objects.create_user("groupuser")
        claims = {"groups": ["editors", "viewers"]}
        map_groups(user, claims)
        assert user.groups.filter(name="editors").exists()
        assert user.groups.filter(name="viewers").exists()
        assert Group.objects.filter(name="editors").exists()

    def test_empty_groups_does_nothing(self):
        user = User.objects.create_user("nogroupuser")
        claims = {"groups": []}
        map_groups(user, claims)
        assert user.groups.count() == 0


@pytest.mark.django_db
class TestDocVaultOIDCBackend:
    """Tests for the DocVaultOIDCBackend class."""

    @override_settings(OIDC_ENABLED=False)
    def test_returns_none_when_oidc_disabled(self):
        backend = DocVaultOIDCBackend()
        result = backend.authenticate(request=MagicMock())
        assert result is None

    def test_get_user_returns_user(self):
        user = User.objects.create_user("oidclookup", password="testpass123!")
        backend = DocVaultOIDCBackend()
        found = backend.get_user(user.pk)
        assert found == user

    def test_get_user_returns_none_for_missing(self):
        backend = DocVaultOIDCBackend()
        assert backend.get_user(99999) is None
