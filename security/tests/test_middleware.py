"""Tests for security middleware."""

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, override_settings

from security.middleware import IPAccessControlMiddleware, SecurityHeadersMiddleware


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rf():
    return RequestFactory()


def dummy_response_view(request):
    """Simple view that returns a 200 OK."""
    return HttpResponse("OK")


# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware
# ---------------------------------------------------------------------------


class TestSecurityHeadersMiddleware:
    """Tests for the SecurityHeadersMiddleware."""

    def test_adds_csp_header(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(dummy_response_view)
        response = middleware(request)
        assert "Content-Security-Policy" in response
        assert "default-src 'self'" in response["Content-Security-Policy"]

    def test_adds_x_content_type_options(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(dummy_response_view)
        response = middleware(request)
        assert response["X-Content-Type-Options"] == "nosniff"

    def test_adds_x_frame_options(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(dummy_response_view)
        response = middleware(request)
        assert response["X-Frame-Options"] == "DENY"

    def test_adds_referrer_policy(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(dummy_response_view)
        response = middleware(request)
        assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_adds_permissions_policy(self, rf):
        request = rf.get("/")
        middleware = SecurityHeadersMiddleware(dummy_response_view)
        response = middleware(request)
        assert "Permissions-Policy" in response
        assert "camera=()" in response["Permissions-Policy"]


# ---------------------------------------------------------------------------
# IPAccessControlMiddleware
# ---------------------------------------------------------------------------


class TestIPAccessControlMiddleware:
    """Tests for the IPAccessControlMiddleware."""

    @override_settings(IP_WHITELIST=["10.0.0.1", "10.0.0.2"], IP_BLACKLIST=[])
    def test_whitelist_allows_listed_ip(self, rf):
        request = rf.get("/")
        request.META["REMOTE_ADDR"] = "10.0.0.1"
        middleware = IPAccessControlMiddleware(dummy_response_view)
        response = middleware(request)
        assert response.status_code == 200

    @override_settings(IP_WHITELIST=["10.0.0.1"], IP_BLACKLIST=[])
    def test_whitelist_blocks_unlisted_ip(self, rf):
        request = rf.get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        middleware = IPAccessControlMiddleware(dummy_response_view)
        response = middleware(request)
        assert response.status_code == 403

    @override_settings(IP_WHITELIST=[], IP_BLACKLIST=["192.168.1.100"])
    def test_blacklist_blocks_listed_ip(self, rf):
        request = rf.get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.100"
        middleware = IPAccessControlMiddleware(dummy_response_view)
        response = middleware(request)
        assert response.status_code == 403

    @override_settings(IP_WHITELIST=[], IP_BLACKLIST=["192.168.1.100"])
    def test_blacklist_allows_unlisted_ip(self, rf):
        request = rf.get("/")
        request.META["REMOTE_ADDR"] = "10.0.0.5"
        middleware = IPAccessControlMiddleware(dummy_response_view)
        response = middleware(request)
        assert response.status_code == 200

    @override_settings(IP_WHITELIST=[], IP_BLACKLIST=[])
    def test_empty_lists_passes_all(self, rf):
        request = rf.get("/")
        request.META["REMOTE_ADDR"] = "1.2.3.4"
        middleware = IPAccessControlMiddleware(dummy_response_view)
        response = middleware(request)
        assert response.status_code == 200

    @override_settings(IP_WHITELIST=["10.0.0.1"], IP_BLACKLIST=[])
    def test_x_forwarded_for_parsing(self, rf):
        request = rf.get("/")
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        request.META["HTTP_X_FORWARDED_FOR"] = "10.0.0.1, 192.168.1.1"
        middleware = IPAccessControlMiddleware(dummy_response_view)
        response = middleware(request)
        # Should use first IP from X-Forwarded-For (10.0.0.1), which is whitelisted
        assert response.status_code == 200

    @override_settings(IP_WHITELIST=["10.0.0.1"], IP_BLACKLIST=[])
    def test_x_forwarded_for_blocked_ip(self, rf):
        request = rf.get("/")
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        request.META["HTTP_X_FORWARDED_FOR"] = "192.168.1.1, 10.0.0.1"
        middleware = IPAccessControlMiddleware(dummy_response_view)
        response = middleware(request)
        # First IP is 192.168.1.1, not whitelisted
        assert response.status_code == 403
