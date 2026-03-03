"""Two-factor OTP authentication utilities."""

import hashlib
import io
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def generate_totp_secret():
    """Generate a new TOTP secret."""
    import pyotp
    return pyotp.random_base32()


def get_totp(secret):
    """Get a TOTP instance for a given secret."""
    import pyotp
    return pyotp.TOTP(secret)


def verify_totp(secret, code):
    """Verify a TOTP code against a secret."""
    totp = get_totp(secret)
    return totp.verify(code, valid_window=1)


def get_provisioning_uri(secret, username):
    """Get the OTP provisioning URI for QR code generation."""
    totp = get_totp(secret)
    issuer = getattr(settings, "OTP_ISSUER_NAME", "DocVault")
    return totp.provisioning_uri(name=username, issuer_name=issuer)


def generate_qr_code(provisioning_uri):
    """Generate a QR code as PNG bytes for the provisioning URI."""
    import qrcode

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def hash_backup_code(code):
    """Hash a backup code for storage."""
    return hashlib.sha256(code.encode()).hexdigest()


def verify_backup_code(code, hashed_codes):
    """Verify a backup code against stored hashes.

    Returns the index of the matching code, or -1 if not found.
    """
    hashed = hash_backup_code(code)
    try:
        return hashed_codes.index(hashed)
    except ValueError:
        return -1
