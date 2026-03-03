"""
Authentication backends for DocVault.

LDAP authentication is optional and configured via environment variables.
Requires python-ldap and django-auth-ldap to be installed separately.
"""

import logging

from django.conf import settings

logger = logging.getLogger("docvault.security")


def configure_ldap_backend():
    """
    Configure LDAP authentication if enabled.

    Required environment variables when LDAP_ENABLED=true:
    - LDAP_SERVER_URI: e.g., ldap://ldap.example.com
    - LDAP_BIND_DN: e.g., cn=admin,dc=example,dc=com
    - LDAP_BIND_PASSWORD: bind password
    - LDAP_USER_SEARCH_BASE: e.g., ou=users,dc=example,dc=com
    - LDAP_USER_SEARCH_FILTER: e.g., (uid=%(user)s)
    - LDAP_GROUP_SEARCH_BASE: e.g., ou=groups,dc=example,dc=com

    Optional:
    - LDAP_START_TLS: true/false (default: false)
    - LDAP_REQUIRE_GROUP: DN of required group membership
    """
    if not getattr(settings, "LDAP_ENABLED", False):
        return

    try:
        import ldap
        from django_auth_ldap.config import GroupOfNamesType, LDAPSearch

        from django.conf import settings as django_settings
        import environ

        env = environ.Env()

        django_settings.AUTH_LDAP_SERVER_URI = env.str("LDAP_SERVER_URI", default="")
        django_settings.AUTH_LDAP_BIND_DN = env.str("LDAP_BIND_DN", default="")
        django_settings.AUTH_LDAP_BIND_PASSWORD = env.str("LDAP_BIND_PASSWORD", default="")

        django_settings.AUTH_LDAP_USER_SEARCH = LDAPSearch(
            env.str("LDAP_USER_SEARCH_BASE", default=""),
            ldap.SCOPE_SUBTREE,
            env.str("LDAP_USER_SEARCH_FILTER", default="(uid=%(user)s)"),
        )

        django_settings.AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
            env.str("LDAP_GROUP_SEARCH_BASE", default=""),
            ldap.SCOPE_SUBTREE,
            "(objectClass=groupOfNames)",
        )
        django_settings.AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()

        django_settings.AUTH_LDAP_USER_ATTR_MAP = {
            "first_name": "givenName",
            "last_name": "sn",
            "email": "mail",
        }

        # Mirror LDAP groups to Django groups
        django_settings.AUTH_LDAP_MIRROR_GROUPS = True

        # Optionally require membership in a specific group
        required_group = env.str("LDAP_REQUIRE_GROUP", default="")
        if required_group:
            django_settings.AUTH_LDAP_REQUIRE_GROUP = required_group

        # Add LDAP backend to authentication backends
        backends = list(django_settings.AUTHENTICATION_BACKENDS)
        if "django_auth_ldap.backend.LDAPBackend" not in backends:
            backends.insert(0, "django_auth_ldap.backend.LDAPBackend")
            django_settings.AUTHENTICATION_BACKENDS = backends

        logger.info("LDAP authentication configured successfully.")

    except ImportError:
        logger.warning(
            "LDAP_ENABLED=true but django-auth-ldap/python-ldap not installed. "
            "Install with: pip install django-auth-ldap python-ldap"
        )
