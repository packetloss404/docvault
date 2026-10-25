import io
import socket
import urllib.error
import urllib.request
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.url_safety import (
    UnsafeOutboundUrlError,
    open_outbound_http_request,
    validate_outbound_http_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/webhook",
        "http://hooks.example.org/path",
        "https://[2606:4700:4700::1111]/hook",
    ],
)
def test_validate_outbound_http_url_accepts_public_http_urls(url):
    assert validate_outbound_http_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/file",
        "http://localhost:8000/hook",
        "http://api.localhost/hook",
        "http://redis:6379/hook",
        "http://127.0.0.1/hook",
        "http://10.0.0.5/hook",
        "http://172.16.0.5/hook",
        "http://192.168.1.5/hook",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/hook",
        "http://100.64.0.1/hook",
        "http://224.0.0.1/hook",
        "http://username:password@example.com/hook",
        "http://example.com:0/hook",
        "http://example.com:99999/hook",
        "http://[invalid/hook",
    ],
)
def test_validate_outbound_http_url_rejects_local_or_private_destinations(url):
    with pytest.raises(UnsafeOutboundUrlError):
        validate_outbound_http_url(url)


def _dns_address(address, port=80):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, port))


@pytest.mark.parametrize(
    "addresses",
    [
        ["127.0.0.1"],
        ["10.0.0.1"],
        ["169.254.169.254"],
        ["::1"],
        ["::ffff:127.0.0.1"],
        ["not-an-ip"],
        ["93.184.216.34", "192.168.1.1"],
        [],
    ],
)
def test_outbound_request_rejects_nonpublic_dns_answers_before_connect(addresses):
    answers = [_dns_address(address) for address in addresses]
    with patch("core.url_safety.socket.getaddrinfo", return_value=answers), patch(
        "core.url_safety.socket.socket"
    ) as mock_socket:
        with pytest.raises(UnsafeOutboundUrlError):
            open_outbound_http_request(urllib.request.Request("http://hooks.example.org/"))
    mock_socket.assert_not_called()


def test_outbound_http_connects_to_the_checked_address_without_resolving_again(monkeypatch):
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:8000")
    sock = MagicMock()
    sock.makefile.return_value = io.BytesIO(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    with patch("core.url_safety.socket.getaddrinfo", return_value=[_dns_address("93.184.216.34")]) as dns, patch(
        "core.url_safety.socket.socket", return_value=sock
    ):
        with open_outbound_http_request(urllib.request.Request("http://hooks.example.org/")) as response:
            assert response.status == 200
    dns.assert_called_once_with("hooks.example.org", 80, type=socket.SOCK_STREAM)
    sock.connect.assert_called_once_with(("93.184.216.34", 80))
    assert b"Host: hooks.example.org\r\n" in sock.sendall.call_args[0][0]


def test_outbound_https_keeps_hostname_for_certificate_verification():
    sock = MagicMock()
    sock.makefile.return_value = io.BytesIO(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    context = MagicMock()
    context.wrap_socket.return_value = sock
    with patch("core.url_safety.socket.getaddrinfo", return_value=[_dns_address("93.184.216.34", 443)]), patch(
        "core.url_safety.socket.socket", return_value=sock
    ), patch("http.client._create_https_context", return_value=context):
        with open_outbound_http_request(urllib.request.Request("https://hooks.example.org/")) as response:
            assert response.status == 200
    context.wrap_socket.assert_called_once_with(sock, server_hostname="hooks.example.org")


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_outbound_request_never_follows_redirects(status):
    sock = MagicMock()
    sock.makefile.return_value = io.BytesIO(
        f"HTTP/1.1 {status} Redirect\r\nLocation: http://127.0.0.1/admin\r\nContent-Length: 0\r\n\r\n".encode()
    )
    with patch("core.url_safety.socket.getaddrinfo", return_value=[_dns_address("93.184.216.34")]) as dns, patch(
        "core.url_safety.socket.socket", return_value=sock
    ) as mock_socket:
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            open_outbound_http_request(urllib.request.Request("http://hooks.example.org/", data=b"{}"))
        assert exc_info.value.code == status
        exc_info.value.close()
    dns.assert_called_once()
    mock_socket.assert_called_once()


def test_outbound_request_closes_a_failed_connection_before_trying_the_next_address():
    failed_socket = MagicMock()
    failed_socket.connect.side_effect = OSError("Connection refused")
    sock = MagicMock()
    sock.makefile.return_value = io.BytesIO(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    with patch(
        "core.url_safety.socket.getaddrinfo",
        return_value=[_dns_address("93.184.216.34"), _dns_address("1.1.1.1")],
    ), patch("core.url_safety.socket.socket", side_effect=[failed_socket, sock]):
        with open_outbound_http_request(urllib.request.Request("http://hooks.example.org/")) as response:
            assert response.status == 200
    failed_socket.close.assert_called_once()
    sock.connect.assert_called_once_with(("1.1.1.1", 80))


@pytest.mark.parametrize("sender", ["workflow_action", "workflow_rule", "notification"])
def test_webhook_senders_block_a_hostname_resolving_to_a_private_address(sender):
    from notifications.dispatch import _send_webhook
    from workflows.actions.webhook import WebhookAction
    from workflows.rules import _send_webhook_action

    document = SimpleNamespace(id=1, title="Test document")
    config = {"url": "http://hooks.example.org/"}
    with patch("core.url_safety.socket.getaddrinfo", return_value=[_dns_address("127.0.0.1")]) as dns, patch(
        "core.url_safety.socket.socket"
    ) as mock_socket:
        if sender == "workflow_action":
            instance = SimpleNamespace(
                document_id=document.id, document=document,
                workflow=SimpleNamespace(label="Test"), current_state=None, context={},
            )
            WebhookAction().execute(instance, config)
        elif sender == "workflow_rule":
            _send_webhook_action(config, document)
        else:
            _send_webhook(config["url"], "test", "Title", "Body", document)
    dns.assert_called_once()
    mock_socket.assert_not_called()
