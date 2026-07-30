"""Helpers for validating outbound URLs."""

from ipaddress import ip_address
from urllib.parse import urlparse


class UnsafeOutboundUrlError(ValueError):
    """Raised when an outbound URL targets a disallowed destination."""


def validate_outbound_http_url(url: str) -> str:
    """Validate an outbound webhook URL before the server connects to it."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeOutboundUrlError("Only http and https URLs are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeOutboundUrlError("URL must include a hostname.")

    host = hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith(".localhost"):
        raise UnsafeOutboundUrlError("Localhost webhook destinations are not allowed.")
    if "." not in host:
        raise UnsafeOutboundUrlError("Single-label internal hostnames are not allowed.")

    try:
        address = ip_address(host)
    except ValueError:
        return url

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise UnsafeOutboundUrlError(
            "Private or local network destinations are not allowed."
        )

    return url
