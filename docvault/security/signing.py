"""GPG document signing utilities."""

import logging
import tempfile
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

_gpg = None


def get_gpg():
    """Return a GPG instance."""
    global _gpg
    if _gpg is not None:
        return _gpg

    import gnupg

    gpg_home = getattr(settings, "GPG_HOME", "") or None
    _gpg = gnupg.GPG(gnupghome=gpg_home)
    return _gpg


def reset_gpg():
    """Reset the GPG instance (for testing)."""
    global _gpg
    _gpg = None


def sign_data(data: bytes, key_id: str = "") -> dict:
    """Sign binary data with the server GPG key.

    Returns a dict with 'signature', 'key_id', 'algorithm', 'ok'.
    """
    gpg = get_gpg()
    signing_key = key_id or getattr(settings, "GPG_KEY_ID", "")
    if not signing_key:
        raise ValueError("No GPG key ID configured. Set GPG_KEY_ID.")

    result = gpg.sign(data, keyid=signing_key, detach=True)
    if not result.data:
        raise RuntimeError(f"GPG signing failed: {result.stderr}")

    return {
        "signature": str(result),
        "key_id": result.key_id or signing_key,
        "algorithm": "RSA",
        "ok": True,
    }


def verify_signature(data: bytes, signature: str) -> dict:
    """Verify a detached GPG signature against data.

    Returns a dict with 'valid', 'key_id', 'username', 'timestamp'.
    """
    gpg = get_gpg()

    # Write signature to a temp file for verification
    with tempfile.NamedTemporaryFile(suffix=".sig", delete=False, mode="w") as sig_file:
        sig_file.write(signature)
        sig_path = sig_file.name

    try:
        # Write data to a temp file
        with tempfile.NamedTemporaryFile(suffix=".data", delete=False) as data_file:
            data_file.write(data)
            data_path = data_file.name

        try:
            verified = gpg.verify_data(sig_path, data)
            return {
                "valid": verified.valid,
                "key_id": getattr(verified, "key_id", ""),
                "username": getattr(verified, "username", ""),
                "timestamp": getattr(verified, "timestamp", ""),
            }
        finally:
            Path(data_path).unlink(missing_ok=True)
    finally:
        Path(sig_path).unlink(missing_ok=True)


def list_keys():
    """List available GPG keys."""
    gpg = get_gpg()
    keys = gpg.list_keys()
    return [
        {
            "key_id": k.get("keyid", ""),
            "fingerprint": k.get("fingerprint", ""),
            "uids": k.get("uids", []),
            "expires": k.get("expires", ""),
            "length": k.get("length", ""),
        }
        for k in keys
    ]


def import_key(key_data: str) -> dict:
    """Import a GPG key."""
    gpg = get_gpg()
    result = gpg.import_keys(key_data)
    return {
        "count": result.count,
        "fingerprints": result.fingerprints,
    }


def delete_key(fingerprint: str) -> bool:
    """Delete a GPG key by fingerprint."""
    gpg = get_gpg()
    result = gpg.delete_keys(fingerprint)
    return str(result) == "ok"
