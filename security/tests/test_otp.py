"""Tests for OTP utilities and OTPDevice model."""

import hashlib
import sys
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.test import override_settings

from security.models import OTPDevice


# ---------------------------------------------------------------------------
# Fixtures for mocking lazy imports
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_pyotp():
    """Inject a mock pyotp module into sys.modules for lazy import."""
    mock_mod = MagicMock()
    with patch.dict(sys.modules, {"pyotp": mock_mod}):
        yield mock_mod


@pytest.fixture
def mock_qrcode():
    """Inject a mock qrcode module into sys.modules for lazy import."""
    mock_mod = MagicMock()
    with patch.dict(sys.modules, {"qrcode": mock_mod}):
        yield mock_mod


# ---------------------------------------------------------------------------
# generate_totp_secret
# ---------------------------------------------------------------------------


class TestGenerateTotpSecret:
    """Tests for generate_totp_secret."""

    def test_returns_string(self, mock_pyotp):
        from security.otp import generate_totp_secret

        mock_pyotp.random_base32.return_value = "JBSWY3DPEHPK3PXP"
        result = generate_totp_secret()
        assert result == "JBSWY3DPEHPK3PXP"
        mock_pyotp.random_base32.assert_called_once()


# ---------------------------------------------------------------------------
# verify_totp
# ---------------------------------------------------------------------------


class TestVerifyTotp:
    """Tests for verify_totp."""

    def test_valid_code(self, mock_pyotp):
        from security.otp import verify_totp

        mock_totp = MagicMock()
        mock_totp.verify.return_value = True
        mock_pyotp.TOTP.return_value = mock_totp

        assert verify_totp("secret", "123456") is True
        mock_totp.verify.assert_called_once_with("123456", valid_window=1)

    def test_invalid_code(self, mock_pyotp):
        from security.otp import verify_totp

        mock_totp = MagicMock()
        mock_totp.verify.return_value = False
        mock_pyotp.TOTP.return_value = mock_totp

        assert verify_totp("secret", "000000") is False


# ---------------------------------------------------------------------------
# get_provisioning_uri
# ---------------------------------------------------------------------------


class TestGetProvisioningUri:
    """Tests for get_provisioning_uri."""

    @override_settings(OTP_ISSUER_NAME="TestApp")
    def test_returns_uri_string(self, mock_pyotp):
        from security.otp import get_provisioning_uri

        mock_totp = MagicMock()
        mock_totp.provisioning_uri.return_value = "otpauth://totp/TestApp:testuser?secret=SECRET&issuer=TestApp"
        mock_pyotp.TOTP.return_value = mock_totp

        result = get_provisioning_uri("SECRET", "testuser")
        assert "otpauth://" in result
        mock_totp.provisioning_uri.assert_called_once_with(name="testuser", issuer_name="TestApp")


# ---------------------------------------------------------------------------
# generate_qr_code
# ---------------------------------------------------------------------------


class TestGenerateQrCode:
    """Tests for generate_qr_code."""

    def test_returns_bytes(self, mock_qrcode):
        from security.otp import generate_qr_code

        mock_qr = MagicMock()
        mock_qrcode.QRCode.return_value = mock_qr
        mock_img = MagicMock()
        mock_qr.make_image.return_value = mock_img

        # Simulate img.save writing PNG data to the buffer
        def fake_save(buf, format="PNG"):
            buf.write(b"\x89PNG\r\n\x1a\n")

        mock_img.save.side_effect = fake_save

        result = generate_qr_code("otpauth://totp/test")
        assert isinstance(result, bytes)
        assert len(result) > 0
        mock_qr.add_data.assert_called_once_with("otpauth://totp/test")
        mock_qr.make.assert_called_once_with(fit=True)


# ---------------------------------------------------------------------------
# hash_backup_code / verify_backup_code
# ---------------------------------------------------------------------------


class TestBackupCodes:
    """Tests for backup code hashing and verification."""

    def test_hash_backup_code_deterministic(self):
        from security.otp import hash_backup_code

        h1 = hash_backup_code("abc12345")
        h2 = hash_backup_code("abc12345")
        assert h1 == h2
        assert h1 == hashlib.sha256(b"abc12345").hexdigest()

    def test_verify_backup_code_found(self):
        from security.otp import hash_backup_code, verify_backup_code

        codes = ["code1", "code2", "code3"]
        hashed = [hash_backup_code(c) for c in codes]
        assert verify_backup_code("code2", hashed) == 1

    def test_verify_backup_code_not_found(self):
        from security.otp import hash_backup_code, verify_backup_code

        hashed = [hash_backup_code("code1")]
        assert verify_backup_code("wrong", hashed) == -1


# ---------------------------------------------------------------------------
# OTPDevice model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOTPDeviceModel:
    """Tests for the OTPDevice Django model."""

    def test_create_otp_device(self):
        user = User.objects.create_user("otpuser", password="testpass123!")
        device = OTPDevice.objects.create(
            user=user, secret="TESTSECRET", confirmed=False
        )
        assert device.pk is not None
        assert device.confirmed is False
        assert str(device) == "OTP(otpuser, pending)"

    def test_confirmed_str(self):
        user = User.objects.create_user("otpuser2", password="testpass123!")
        device = OTPDevice.objects.create(
            user=user, secret="TESTSECRET", confirmed=True
        )
        assert str(device) == "OTP(otpuser2, confirmed)"

    def test_generate_backup_codes(self):
        codes = OTPDevice.generate_backup_codes(count=8)
        assert len(codes) == 8
        # Each code should be a hex string (8 chars for token_hex(4))
        for code in codes:
            assert len(code) == 8
            int(code, 16)  # Should not raise

    def test_generate_backup_codes_custom_count(self):
        codes = OTPDevice.generate_backup_codes(count=4)
        assert len(codes) == 4
