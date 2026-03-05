"""Security middleware for DocVault."""

import logging

from django.conf import settings
from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Add security headers to all responses.

    Uses process_response pattern via __call__ to set headers after the
    response has been fully prepared, avoiding conflicts with DRF responses
    that haven't been rendered yet.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return self.process_response(request, response)

    @staticmethod
    def process_response(request, response):
        # Content Security Policy
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'"
        )

        # Additional security headers
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        return response


class IPAccessControlMiddleware:
    """IP-based access control via whitelist/blacklist."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        client_ip = self._get_client_ip(request)
        whitelist = getattr(settings, "IP_WHITELIST", [])
        blacklist = getattr(settings, "IP_BLACKLIST", [])

        # If whitelist is configured, only allow listed IPs
        if whitelist and client_ip not in whitelist:
            logger.warning("IP %s blocked by whitelist.", client_ip)
            return HttpResponseForbidden("Access denied.")

        # If blacklist is configured, deny listed IPs
        if blacklist and client_ip in blacklist:
            logger.warning("IP %s blocked by blacklist.", client_ip)
            return HttpResponseForbidden("Access denied.")

        return self.get_response(request)

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request, respecting X-Forwarded-For."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
