"""Tests for GPG signing utilities."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings


@pytest.fixture(autouse=True)
def _reset_gpg():
    """Reset GPG singleton before and after each test."""
    from security.signing import reset_gpg

    reset_gpg()
    yield
    reset_gpg()


@pytest.fixture
def mock_gnupg():
    """Inject a mock gnupg module into sys.modules for lazy import."""
    mock_mod = MagicMock()
    with patch.dict(sys.modules, {"gnupg": mock_mod}):
        yield mock_mod


# ---------------------------------------------------------------------------
# sign_data
# ---------------------------------------------------------------------------


class TestSignData:
    """Tests for the sign_data function."""

    @override_settings(GPG_KEY_ID="ABCD1234")
    def test_sign_data_success(self, mock_gnupg):
        from security.signing import sign_data

        mock_gpg_instance = mock_gnupg.GPG.return_value
        mock_result = MagicMock()
        mock_result.data = b"signature-bytes"
        mock_result.__str__ = lambda self: "-----BEGIN PGP SIGNATURE-----\ndata\n-----END PGP SIGNATURE-----"
        mock_result.key_id = "ABCD1234"
        mock_gpg_instance.sign.return_value = mock_result

        result = sign_data(b"test data")

        assert result["ok"] is True
        assert result["key_id"] == "ABCD1234"
        assert result["algorithm"] == "RSA"
        assert "PGP SIGNATURE" in result["signature"]
        mock_gpg_instance.sign.assert_called_once()

    @override_settings(GPG_KEY_ID="")
    def test_sign_data_no_key_raises_value_error(self, mock_gnupg):
        from security.signing import sign_data

        with pytest.raises(ValueError, match="No GPG key ID configured"):
            sign_data(b"data")

    @override_settings(GPG_KEY_ID="ABCD1234")
    def test_sign_data_failure_raises_runtime_error(self, mock_gnupg):
        from security.signing import sign_data

        mock_gpg_instance = mock_gnupg.GPG.return_value
        mock_result = MagicMock()
        mock_result.data = b""  # Empty means failure
        mock_result.stderr = "signing failed"
        mock_gpg_instance.sign.return_value = mock_result

        with pytest.raises(RuntimeError, match="GPG signing failed"):
            sign_data(b"data")


# ---------------------------------------------------------------------------
# verify_signature
# ---------------------------------------------------------------------------


class TestVerifySignature:
    """Tests for verify_signature function."""

    def test_verify_signature_valid(self, mock_gnupg):
        from security.signing import verify_signature

        mock_gpg_instance = mock_gnupg.GPG.return_value
        mock_verified = MagicMock()
        mock_verified.valid = True
        mock_verified.key_id = "ABCD1234"
        mock_verified.username = "testuser"
        mock_verified.timestamp = "2025-01-01"
        mock_gpg_instance.verify_data.return_value = mock_verified

        result = verify_signature(b"data", "-----BEGIN PGP SIGNATURE-----")
        assert result["valid"] is True
        assert result["key_id"] == "ABCD1234"
        assert result["username"] == "testuser"

    def test_verify_signature_invalid(self, mock_gnupg):
        from security.signing import verify_signature

        mock_gpg_instance = mock_gnupg.GPG.return_value
        mock_verified = MagicMock()
        mock_verified.valid = False
        mock_verified.key_id = ""
        mock_verified.username = ""
        mock_verified.timestamp = ""
        mock_gpg_instance.verify_data.return_value = mock_verified

        result = verify_signature(b"data", "bad-sig")
        assert result["valid"] is False


# ---------------------------------------------------------------------------
# list_keys, import_key, delete_key
# ---------------------------------------------------------------------------


class TestKeyManagement:
    """Tests for key management utilities."""

    def test_list_keys(self, mock_gnupg):
        from security.signing import list_keys

        mock_gpg_instance = mock_gnupg.GPG.return_value
        mock_gpg_instance.list_keys.return_value = [
            {
                "keyid": "ABCD1234",
                "fingerprint": "AABB1122",
                "uids": ["Test User <test@example.com>"],
                "expires": "2030-01-01",
                "length": "4096",
            }
        ]

        keys = list_keys()
        assert len(keys) == 1
        assert keys[0]["key_id"] == "ABCD1234"
        assert keys[0]["fingerprint"] == "AABB1122"
        assert "Test User" in keys[0]["uids"][0]

    def test_import_key(self, mock_gnupg):
        from security.signing import import_key

        mock_gpg_instance = mock_gnupg.GPG.return_value
        mock_result = MagicMock()
        mock_result.count = 1
        mock_result.fingerprints = ["AABB1122"]
        mock_gpg_instance.import_keys.return_value = mock_result

        result = import_key("-----BEGIN PGP PUBLIC KEY BLOCK-----")
        assert result["count"] == 1
        assert result["fingerprints"] == ["AABB1122"]

    def test_delete_key_success(self, mock_gnupg):
        from security.signing import delete_key

        mock_gpg_instance = mock_gnupg.GPG.return_value
        mock_result = MagicMock()
        mock_result.__str__ = lambda self: "ok"
        mock_gpg_instance.delete_keys.return_value = mock_result

        assert delete_key("AABB1122") is True


# ---------------------------------------------------------------------------
# reset_gpg
# ---------------------------------------------------------------------------


class TestResetGpg:
    """Tests for the reset_gpg function."""

    def test_reset_gpg_clears_singleton(self, mock_gnupg):
        from security.signing import get_gpg, reset_gpg

        mock_gpg_instance = MagicMock()
        mock_gnupg.GPG.return_value = mock_gpg_instance

        # First call creates instance
        gpg1 = get_gpg()
        assert gpg1 is mock_gpg_instance

        # Reset clears it
        reset_gpg()

        # Next call creates a new instance
        mock_gpg_instance2 = MagicMock()
        mock_gnupg.GPG.return_value = mock_gpg_instance2
        gpg2 = get_gpg()
        assert gpg2 is mock_gpg_instance2
