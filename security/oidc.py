"""OpenID Connect authentication backend for DocVault."""

import logging

from django.conf import settings
from django.contrib.auth.models import Group

logger = logging.getLogger(__name__)


class DocVaultOIDCBackend:
    """Custom OIDC authentication backend.

    Wraps mozilla-django-oidc to:
    - Auto-create users on first OIDC login
    - Map OIDC claims to user attributes
    - Map OIDC groups to Django groups
    """

    def authenticate(self, request, **kwargs):
        """Authenticate via OIDC. Delegates to mozilla-django-oidc if available."""
        if not getattr(settings, "OIDC_ENABLED", False):
            return None

        try:
            from mozilla_django_oidc.auth import OIDCAuthenticationBackend

            backend = OIDCAuthenticationBackend()
            return backend.authenticate(request, **kwargs)
        except ImportError:
            logger.warning("mozilla-django-oidc not installed but OIDC_ENABLED=True")
            return None
        except Exception:
            logger.exception("OIDC authentication failed")
            return None

    def get_user(self, user_id):
        from django.contrib.auth.models import User

        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


def create_oidc_user(claims):
    """Create a new user from OIDC claims."""
    from django.contrib.auth.models import User

    email = claims.get("email", "")
    username = claims.get("preferred_username") or claims.get("sub", "")

    user = User.objects.create_user(
        username=username,
        email=email,
        first_name=claims.get("given_name", ""),
        last_name=claims.get("family_name", ""),
    )

    # Map OIDC groups to Django groups
    map_groups(user, claims)

    logger.info("Created OIDC user: %s", username)
    return user


def update_oidc_user(user, claims):
    """Update user attributes from OIDC claims."""
    changed = False

    for claim, field in [
        ("email", "email"),
        ("given_name", "first_name"),
        ("family_name", "last_name"),
    ]:
        value = claims.get(claim, "")
        if value and getattr(user, field) != value:
            setattr(user, field, value)
            changed = True

    if changed:
        user.save()

    map_groups(user, claims)
    return user


def map_groups(user, claims):
    """Map OIDC group claims to Django groups."""
    oidc_groups = claims.get("groups", [])
    if not oidc_groups:
        return

    for group_name in oidc_groups:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
