"""Outbound HTTP requests restricted to public network destinations."""

import http.client
import socket
import urllib.request
from functools import partial
from ipaddress import ip_address
from urllib.parse import urlparse


class UnsafeOutboundUrlError(ValueError):
    """Raised when an outbound URL targets a disallowed destination."""


def validate_outbound_http_url(url: str) -> str:
    """Validate an outbound webhook URL before the server connects to it."""
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as exc:
        raise UnsafeOutboundUrlError("URL has an invalid host or port.") from exc
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeOutboundUrlError("Only http and https URLs are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeOutboundUrlError("URL must include a hostname.")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeOutboundUrlError("URL credentials are not allowed.")
    if port == 0:
        raise UnsafeOutboundUrlError("URL has an invalid port.")

    host = hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith(".localhost"):
        raise UnsafeOutboundUrlError("Localhost webhook destinations are not allowed.")
    try:
        address = ip_address(host)
    except ValueError:
        if "." not in host:
            raise UnsafeOutboundUrlError("Single-label internal hostnames are not allowed.")
        return url

    if not address.is_global or address.is_multicast:
        raise UnsafeOutboundUrlError(
            "Private or local network destinations are not allowed."
        )

    return url


def _create_public_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    host, port = address
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise UnsafeOutboundUrlError("URL hostname did not resolve to a public address.")
    for _, _, _, _, sockaddr in addresses:
        try:
            resolved = ip_address(sockaddr[0])
        except ValueError as exc:
            raise UnsafeOutboundUrlError("URL hostname resolved to an invalid address.") from exc
        if not resolved.is_global or resolved.is_multicast:
            raise UnsafeOutboundUrlError("URL hostname resolves to a non-public address.")

    last_error = None
    for family, socktype, proto, _, sockaddr in addresses:
        sock = socket.socket(family, socktype, proto)
        try:
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as exc:
            sock.close()
            last_error = exc
    raise last_error


def _public_connection(connection_type, host, **kwargs):
    connection = connection_type(host, **kwargs)
    # Pin the checked sockaddr at connect time, keeping the original Host and TLS SNI.
    connection._create_connection = _create_public_connection
    return connection


class _PublicHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, request):
        return self.do_open(partial(_public_connection, http.client.HTTPConnection), request)


class _PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, request):
        return self.do_open(
            partial(_public_connection, http.client.HTTPSConnection),
            request,
            context=self._context,
        )


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def open_outbound_http_request(request, timeout=10):
    """Open HTTP(S) without redirects, proxies, or a second DNS lookup on connect."""
    validate_outbound_http_url(request.full_url)
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _PublicHTTPHandler(),
        _PublicHTTPSHandler(),
        _NoRedirectHandler(),
    )
    return opener.open(request, timeout=timeout)
