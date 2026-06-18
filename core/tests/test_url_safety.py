import pytest

from core.url_safety import UnsafeOutboundUrlError, validate_outbound_http_url


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/webhook",
        "http://hooks.example.org/path",
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
    ],
)
def test_validate_outbound_http_url_rejects_local_or_private_destinations(url):
    with pytest.raises(UnsafeOutboundUrlError):
        validate_outbound_http_url(url)
