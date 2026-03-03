"""Tests for Sprint 17 security-related API views."""

import base64
import io
import sys
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from documents.models import Document, DocumentType
from security.models import AuditLogEntry, OTPDevice, Signature, log_audit_event


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123!",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass123!",
    )


@pytest.fixture
def authed_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def doc_type(db):
    return DocumentType.objects.create(name="Invoice", slug="invoice")


@pytest.fixture
def document(db, user, doc_type):
    return Document.objects.create(
        title="Test Document",
        content="Sample content",
        original_filename="test.pdf",
        mime_type="application/pdf",
        checksum="abc123",
        filename="originals/test.pdf",
        document_type=doc_type,
        owner=user,
    )


@pytest.fixture
def mock_pyotp():
    """Mock the pyotp module for OTP tests."""
    mock_mod = MagicMock()
    # Patch at sys.modules level but also save/restore any cached refs
    _orig = sys.modules.get("pyotp")
    sys.modules["pyotp"] = mock_mod
    yield mock_mod
    if _orig is not None:
        sys.modules["pyotp"] = _orig
    else:
        sys.modules.pop("pyotp", None)


@pytest.fixture
def mock_qrcode():
    """Mock the qrcode module for QR code generation tests."""
    mock_mod = MagicMock()
    _orig = sys.modules.get("qrcode")
    sys.modules["qrcode"] = mock_mod
    yield mock_mod
    if _orig is not None:
        sys.modules["qrcode"] = _orig
    else:
        sys.modules.pop("qrcode", None)


@pytest.fixture
def mock_gnupg():
    """Mock the gnupg module for GPG signing tests."""
    from security.signing import reset_gpg

    reset_gpg()
    mock_mod = MagicMock()
    _orig = sys.modules.get("gnupg")
    sys.modules["gnupg"] = mock_mod
    yield mock_mod
    if _orig is not None:
        sys.modules["gnupg"] = _orig
    else:
        sys.modules.pop("gnupg", None)
    reset_gpg()


@pytest.fixture
def mock_sane():
    """Mock the sane module for scanner tests."""
    from sources.scanner import reset_sane

    reset_sane()
    mock_mod = MagicMock()
    _orig = sys.modules.get("sane")
    sys.modules["sane"] = mock_mod
    yield mock_mod
    if _orig is not None:
        sys.modules["sane"] = _orig
    else:
        sys.modules.pop("sane", None)
    reset_sane()


# ---------------------------------------------------------------------------
# OTP Setup
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOTPSetupView:
    """Tests for POST /api/v1/auth/otp/setup/."""

    def test_otp_setup_returns_qr_code(self, authed_client, user, mock_pyotp, mock_qrcode):
        mock_pyotp.random_base32.return_value = "TESTSECRET"
        mock_totp = MagicMock()
        mock_totp.provisioning_uri.return_value = "otpauth://totp/DocVault:testuser?secret=TESTSECRET"
        mock_pyotp.TOTP.return_value = mock_totp

        mock_qr = MagicMock()
        mock_qrcode.QRCode.return_value = mock_qr
        mock_img = MagicMock()
        mock_qr.make_image.return_value = mock_img
        mock_img.save.side_effect = lambda buf, format: buf.write(b"\x89PNG-data")

        resp = authed_client.post("/api/v1/auth/otp/setup/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["secret"] == "TESTSECRET"
        assert "otpauth://" in resp.data["provisioning_uri"]
        assert resp.data["qr_code_base64"]  # non-empty base64

        # OTPDevice should be created
        assert OTPDevice.objects.filter(user=user, confirmed=False).exists()

    def test_otp_setup_fails_when_already_confirmed(self, authed_client, user, mock_pyotp, mock_qrcode):
        OTPDevice.objects.create(user=user, secret="EXISTING", confirmed=True)
        resp = authed_client.post("/api/v1/auth/otp/setup/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "already enabled" in resp.data["error"].lower()


# ---------------------------------------------------------------------------
# OTP Confirm
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOTPConfirmView:
    """Tests for POST /api/v1/auth/otp/confirm/."""

    def test_confirm_success(self, authed_client, user, mock_pyotp):
        OTPDevice.objects.create(user=user, secret="TESTSECRET", confirmed=False)

        mock_totp = MagicMock()
        mock_totp.verify.return_value = True
        mock_pyotp.TOTP.return_value = mock_totp

        resp = authed_client.post("/api/v1/auth/otp/confirm/", {"code": "123456"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["confirmed"] is True
        assert len(resp.data["backup_codes"]) == 8

        device = OTPDevice.objects.get(user=user)
        assert device.confirmed is True

    def test_confirm_invalid_code(self, authed_client, user, mock_pyotp):
        OTPDevice.objects.create(user=user, secret="TESTSECRET", confirmed=False)

        mock_totp = MagicMock()
        mock_totp.verify.return_value = False
        mock_pyotp.TOTP.return_value = mock_totp

        resp = authed_client.post("/api/v1/auth/otp/confirm/", {"code": "000000"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid" in resp.data["error"].lower()

    def test_confirm_no_pending_device(self, authed_client, user):
        resp = authed_client.post("/api/v1/auth/otp/confirm/", {"code": "123456"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# OTP Verify
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOTPVerifyView:
    """Tests for POST /api/v1/auth/otp/verify/."""

    def test_verify_totp_success(self, authed_client, user, mock_pyotp):
        OTPDevice.objects.create(user=user, secret="TESTSECRET", confirmed=True, backup_codes=[])

        mock_totp = MagicMock()
        mock_totp.verify.return_value = True
        mock_pyotp.TOTP.return_value = mock_totp

        resp = authed_client.post("/api/v1/auth/otp/verify/", {"code": "123456"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["verified"] is True

    def test_verify_backup_code(self, authed_client, user, mock_pyotp):
        from security.otp import hash_backup_code

        backup_hash = hash_backup_code("abcd1234")
        OTPDevice.objects.create(
            user=user, secret="TESTSECRET", confirmed=True,
            backup_codes=[backup_hash],
        )

        mock_totp = MagicMock()
        mock_totp.verify.return_value = False  # TOTP fails
        mock_pyotp.TOTP.return_value = mock_totp

        resp = authed_client.post("/api/v1/auth/otp/verify/", {"code": "abcd1234"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["verified"] is True
        assert resp.data["backup_code_used"] is True

        # Backup code should be consumed
        device = OTPDevice.objects.get(user=user)
        assert len(device.backup_codes) == 0

    def test_verify_invalid_code(self, authed_client, user, mock_pyotp):
        OTPDevice.objects.create(user=user, secret="TESTSECRET", confirmed=True, backup_codes=[])

        mock_totp = MagicMock()
        mock_totp.verify.return_value = False
        mock_pyotp.TOTP.return_value = mock_totp

        resp = authed_client.post("/api/v1/auth/otp/verify/", {"code": "000000"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_no_otp_device(self, authed_client, user):
        resp = authed_client.post("/api/v1/auth/otp/verify/", {"code": "123456"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# OTP Disable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOTPDisableView:
    """Tests for POST /api/v1/auth/otp/disable/."""

    def test_disable_success(self, authed_client, user):
        OTPDevice.objects.create(user=user, secret="TESTSECRET", confirmed=True)
        resp = authed_client.post("/api/v1/auth/otp/disable/", {"password": "testpass123!"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["disabled"] is True
        assert not OTPDevice.objects.filter(user=user).exists()

    def test_disable_wrong_password(self, authed_client, user):
        OTPDevice.objects.create(user=user, secret="TESTSECRET", confirmed=True)
        resp = authed_client.post("/api/v1/auth/otp/disable/", {"password": "wrongpass"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "wrong password" in resp.data["error"].lower()


# ---------------------------------------------------------------------------
# OTP Status
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOTPStatusView:
    """Tests for GET /api/v1/auth/otp/status/."""

    def test_otp_enabled(self, authed_client, user):
        OTPDevice.objects.create(user=user, secret="TESTSECRET", confirmed=True)
        resp = authed_client.get("/api/v1/auth/otp/status/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["enabled"] is True
        assert resp.data["confirmed"] is True

    def test_otp_disabled(self, authed_client, user):
        resp = authed_client.get("/api/v1/auth/otp/status/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["enabled"] is False
        assert resp.data["confirmed"] is False


# ---------------------------------------------------------------------------
# Document Sign
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocumentSignView:
    """Tests for POST /api/v1/documents/{id}/sign/."""

    @patch("security.signing.sign_data")
    @patch("storage.utils.get_storage_backend")
    def test_sign_success(self, mock_get_backend, mock_sign, authed_client, document):
        mock_backend = MagicMock()
        mock_backend.open.return_value = io.BytesIO(b"file-content")
        mock_get_backend.return_value = mock_backend

        mock_sign.return_value = {
            "signature": "-----BEGIN PGP SIGNATURE-----\ndata\n-----END PGP SIGNATURE-----",
            "key_id": "ABCD1234",
            "algorithm": "RSA",
            "ok": True,
        }

        resp = authed_client.post(f"/api/v1/documents/{document.pk}/sign/")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["key_id"] == "ABCD1234"
        assert Signature.objects.filter(document=document).exists()

    @patch("security.signing.sign_data")
    @patch("storage.utils.get_storage_backend")
    def test_sign_with_key_id(self, mock_get_backend, mock_sign, authed_client, document):
        mock_backend = MagicMock()
        mock_backend.open.return_value = io.BytesIO(b"file-content")
        mock_get_backend.return_value = mock_backend

        mock_sign.return_value = {
            "signature": "sig-data",
            "key_id": "CUSTOM123",
            "algorithm": "RSA",
            "ok": True,
        }

        resp = authed_client.post(
            f"/api/v1/documents/{document.pk}/sign/",
            {"key_id": "CUSTOM123"},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        mock_sign.assert_called_once_with(b"file-content", key_id="CUSTOM123")

    def test_sign_document_not_found(self, authed_client):
        resp = authed_client.post("/api/v1/documents/99999/sign/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Document Signatures List
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocumentSignatureListView:
    """Tests for GET /api/v1/documents/{id}/signatures/."""

    def test_list_signatures(self, authed_client, document, user):
        Signature.objects.create(
            document=document,
            signer=user,
            signature_data="sig-data",
            key_id="ABCD1234",
            algorithm="RSA",
        )
        resp = authed_client.get(f"/api/v1/documents/{document.pk}/signatures/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["key_id"] == "ABCD1234"

    def test_list_signatures_empty(self, authed_client, document):
        resp = authed_client.get(f"/api/v1/documents/{document.pk}/signatures/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 0


# ---------------------------------------------------------------------------
# Document Verify
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDocumentVerifyView:
    """Tests for POST /api/v1/documents/{id}/verify/."""

    @patch("security.signing.verify_signature")
    @patch("storage.utils.get_storage_backend")
    def test_verify_success(self, mock_get_backend, mock_verify, authed_client, document, user):
        sig = Signature.objects.create(
            document=document,
            signer=user,
            signature_data="sig-data",
            key_id="ABCD1234",
        )
        mock_backend = MagicMock()
        mock_backend.open.return_value = io.BytesIO(b"file-content")
        mock_get_backend.return_value = mock_backend

        mock_verify.return_value = {"valid": True, "key_id": "ABCD1234"}

        resp = authed_client.post(f"/api/v1/documents/{document.pk}/verify/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["results"][0]["valid"] is True

    def test_verify_document_not_found(self, authed_client):
        resp = authed_client.post("/api/v1/documents/99999/verify/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# GPG Key List
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGPGKeyListView:
    """Tests for GET /api/v1/gpg-keys/."""

    def test_non_admin_forbidden(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.get("/api/v1/gpg-keys/", format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_list_keys(self, admin_client, mock_gnupg):
        mock_gpg_instance = mock_gnupg.GPG.return_value
        mock_gpg_instance.list_keys.return_value = [
            {
                "keyid": "KEY1",
                "fingerprint": "FP1",
                "uids": ["User 1"],
                "expires": "2030-01-01",
                "length": "4096",
            }
        ]

        resp = admin_client.get("/api/v1/gpg-keys/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["key_id"] == "KEY1"


# ---------------------------------------------------------------------------
# GPG Key Import
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGPGKeyImportView:
    """Tests for POST /api/v1/gpg-keys/import/."""

    def test_import_key(self, admin_client, mock_gnupg):
        mock_gpg_instance = mock_gnupg.GPG.return_value
        mock_result = MagicMock()
        mock_result.count = 1
        mock_result.fingerprints = ["FP123"]
        mock_gpg_instance.import_keys.return_value = mock_result

        resp = admin_client.post(
            "/api/v1/gpg-keys/import/",
            {"key_data": "-----BEGIN PGP PUBLIC KEY BLOCK-----"},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["count"] == 1


# ---------------------------------------------------------------------------
# Audit Log List
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAuditLogListView:
    """Tests for GET /api/v1/audit-log/."""

    def test_non_admin_forbidden(self, authed_client):
        resp = authed_client.get("/api/v1/audit-log/", format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_list(self, admin_client, admin_user):
        log_audit_event(user=admin_user, action="login", detail="Test login")
        resp = admin_client.get("/api/v1/audit-log/")
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get("results", resp.data)
        assert len(results) >= 1

    def test_filter_by_action(self, admin_client, admin_user):
        log_audit_event(user=admin_user, action="login", detail="Login event")
        log_audit_event(user=admin_user, action="create", detail="Create event")
        resp = admin_client.get("/api/v1/audit-log/?action=login")
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get("results", resp.data)
        for entry in results:
            assert entry["action"] == "login"

    def test_filter_by_user(self, admin_client, admin_user, user):
        log_audit_event(user=admin_user, action="login")
        log_audit_event(user=user, action="login")
        resp = admin_client.get(f"/api/v1/audit-log/?user={user.pk}")
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get("results", resp.data)
        for entry in results:
            assert entry["user"] == user.pk


# ---------------------------------------------------------------------------
# Audit Log Export
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAuditLogExportView:
    """Tests for GET /api/v1/audit-log/export/."""

    def test_export_csv(self, admin_client, admin_user):
        log_audit_event(user=admin_user, action="login", detail="CSV test")
        resp = admin_client.get("/api/v1/audit-log/export/?export_format=csv")
        assert resp.status_code == status.HTTP_200_OK
        assert resp["Content-Type"] == "text/csv"
        content = resp.content.decode()
        assert "timestamp" in content
        assert "login" in content

    def test_export_json(self, admin_client, admin_user):
        log_audit_event(user=admin_user, action="login", detail="JSON test")
        resp = admin_client.get("/api/v1/audit-log/export/?export_format=json")
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        assert len(resp.data) >= 1

    def test_export_default_is_json(self, admin_client, admin_user):
        log_audit_event(user=admin_user, action="login", detail="Default test")
        resp = admin_client.get("/api/v1/audit-log/export/")
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)


# ---------------------------------------------------------------------------
# Scanner List
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestScannerListView:
    """Tests for GET /api/v1/sources/scanners/."""

    def test_list_scanners(self, authed_client, mock_sane):
        mock_sane.init.return_value = None
        mock_sane.get_devices.return_value = [
            ("scanner:usb1", "Epson", "V600", "flatbed"),
        ]
        resp = authed_client.get("/api/v1/sources/scanners/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["vendor"] == "Epson"

    @patch("sources.scanner.is_sane_available", return_value=False)
    def test_no_sane_returns_empty(self, mock_avail, authed_client):
        resp = authed_client.get("/api/v1/sources/scanners/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == []


# ---------------------------------------------------------------------------
# Scanner Scan
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestScannerScanView:
    """Tests for POST /api/v1/sources/scanners/{id}/scan/."""

    @patch("sources.scanner.scan_document")
    def test_scan_success(self, mock_scan, authed_client):
        mock_scan.return_value = b"\x89PNG-fake-image-data"
        resp = authed_client.post(
            "/api/v1/sources/scanners/scanner:usb1/scan/",
            {"dpi": 300, "color_mode": "color", "paper_size": "a4"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["format"] == "png"
        assert resp.data["size"] == len(b"\x89PNG-fake-image-data")
        # Verify base64 is decodable
        decoded = base64.b64decode(resp.data["image_base64"])
        assert decoded == b"\x89PNG-fake-image-data"

    @patch("sources.scanner.scan_document", side_effect=RuntimeError("Scanner error"))
    def test_scan_failure(self, mock_scan, authed_client):
        resp = authed_client.post(
            "/api/v1/sources/scanners/scanner:usb1/scan/",
            {"dpi": 300, "color_mode": "color", "paper_size": "a4"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "Scanner error" in resp.data["error"]
