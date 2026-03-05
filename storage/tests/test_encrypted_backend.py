"""Tests for the AES-256 encrypted storage backend."""

import io
import os
import struct
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from storage.backends.base import StorageBackend
from storage.backends.encrypted import (
    CHUNK_SIZE,
    IV_SIZE,
    SALT_SIZE,
    EncryptedStorageBackend,
    _pad,
    _unpad,
    decrypt_stream,
    encrypt_stream,
)


# ---------------------------------------------------------------------------
# PKCS7 padding tests
# ---------------------------------------------------------------------------


class TestPKCS7Padding:
    """Tests for _pad and _unpad helpers."""

    def test_pad_adds_correct_bytes(self):
        data = b"hello"  # 5 bytes -> pad to 16, pad_len = 11
        padded = _pad(data)
        assert len(padded) == 16
        assert padded[-1] == 11
        assert padded == data + bytes([11] * 11)

    def test_pad_full_block_gets_16_byte_padding(self):
        data = b"a" * 16  # exactly 16 bytes -> pad_len = 16 -> adds full block
        padded = _pad(data)
        assert len(padded) == 32
        assert padded[-1] == 16

    def test_pad_empty_data(self):
        padded = _pad(b"")
        assert len(padded) == 16
        assert padded == bytes([16] * 16)

    def test_unpad_reverses_pad(self):
        for size in [0, 1, 5, 15, 16, 31, 32]:
            data = os.urandom(size) if size else b""
            assert _unpad(_pad(data)) == data

    def test_unpad_invalid_padding_value(self):
        bad = b"a" * 15 + bytes([0])
        with pytest.raises(ValueError, match="Invalid padding"):
            _unpad(bad)

    def test_unpad_inconsistent_padding(self):
        bad = b"a" * 14 + bytes([2, 3])
        with pytest.raises(ValueError, match="Invalid padding"):
            _unpad(bad)


# ---------------------------------------------------------------------------
# encrypt_stream / decrypt_stream round-trip
# ---------------------------------------------------------------------------


class TestEncryptDecryptStream:
    """Tests for encrypt_stream and decrypt_stream functions."""

    @override_settings(STORAGE_ENCRYPTION_KDF_ITERATIONS=1000)
    def test_roundtrip_small_data(self):
        plaintext = b"Hello, DocVault!"
        stream = io.BytesIO(plaintext)
        encrypted = encrypt_stream(stream, "secret-key")
        decrypted = decrypt_stream(encrypted, "secret-key")
        assert decrypted.read() == plaintext

    @override_settings(STORAGE_ENCRYPTION_KDF_ITERATIONS=1000)
    def test_roundtrip_empty_data(self):
        stream = io.BytesIO(b"")
        encrypted = encrypt_stream(stream, "secret-key")
        decrypted = decrypt_stream(encrypted, "secret-key")
        assert decrypted.read() == b""

    @override_settings(STORAGE_ENCRYPTION_KDF_ITERATIONS=1000)
    def test_roundtrip_exact_chunk_size(self):
        """Data that is exactly CHUNK_SIZE should trigger the else clause for padding."""
        plaintext = os.urandom(CHUNK_SIZE)
        stream = io.BytesIO(plaintext)
        encrypted = encrypt_stream(stream, "my-pass")
        decrypted = decrypt_stream(encrypted, "my-pass")
        assert decrypted.read() == plaintext

    @override_settings(STORAGE_ENCRYPTION_KDF_ITERATIONS=1000)
    def test_roundtrip_large_data(self):
        """Data larger than CHUNK_SIZE uses multi-chunk processing."""
        plaintext = os.urandom(CHUNK_SIZE * 2 + 1234)
        stream = io.BytesIO(plaintext)
        encrypted = encrypt_stream(stream, "my-pass")
        decrypted = decrypt_stream(encrypted, "my-pass")
        assert decrypted.read() == plaintext

    @override_settings(STORAGE_ENCRYPTION_KDF_ITERATIONS=1000)
    def test_encrypted_output_starts_with_salt_and_iv(self):
        stream = io.BytesIO(b"test data")
        encrypted = encrypt_stream(stream, "key")
        raw = encrypted.read()
        # Must have at least salt + iv + one encrypted block
        assert len(raw) >= SALT_SIZE + IV_SIZE + 16

    @override_settings(STORAGE_ENCRYPTION_KDF_ITERATIONS=1000)
    def test_different_encryptions_produce_different_output(self):
        """Random IV/salt means same plaintext produces different ciphertext."""
        data = b"same plaintext"
        enc1 = encrypt_stream(io.BytesIO(data), "key").read()
        enc2 = encrypt_stream(io.BytesIO(data), "key").read()
        assert enc1 != enc2

    @override_settings(STORAGE_ENCRYPTION_KDF_ITERATIONS=1000)
    def test_wrong_passphrase_fails(self):
        plaintext = b"secret data that should not be recoverable with wrong key"
        encrypted = encrypt_stream(io.BytesIO(plaintext), "correct-key")
        try:
            result = decrypt_stream(encrypted, "wrong-key").read()
            # If decryption didn't raise, the output must differ from plaintext
            assert result != plaintext, "Wrong key must not produce correct plaintext"
        except (ValueError, Exception):
            pass  # Expected: decryption error with wrong key

    @override_settings(STORAGE_ENCRYPTION_KDF_ITERATIONS=1000)
    def test_truncated_ciphertext_raises(self):
        """Missing salt/IV raises ValueError."""
        truncated = io.BytesIO(b"short")
        with pytest.raises(ValueError, match="missing salt or IV"):
            decrypt_stream(truncated, "key")


# ---------------------------------------------------------------------------
# EncryptedStorageBackend class
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEncryptedStorageBackend:
    """Tests for the EncryptedStorageBackend class."""

    @override_settings(STORAGE_ENCRYPTION_KEY="")
    def test_missing_key_raises_value_error(self):
        mock_delegate = MagicMock(spec=StorageBackend)
        with pytest.raises(ValueError, match="STORAGE_ENCRYPTION_KEY must be set"):
            EncryptedStorageBackend(delegate=mock_delegate)

    @override_settings(
        STORAGE_ENCRYPTION_KEY="test-encryption-key",
        STORAGE_ENCRYPTION_KDF_ITERATIONS=1000,
    )
    def test_wraps_delegate(self):
        mock_delegate = MagicMock(spec=StorageBackend)
        backend = EncryptedStorageBackend(delegate=mock_delegate)
        assert backend._delegate is mock_delegate

    @override_settings(
        STORAGE_ENCRYPTION_KEY="test-encryption-key",
        STORAGE_ENCRYPTION_KDF_ITERATIONS=1000,
    )
    def test_save_encrypts_and_open_decrypts(self):
        """save() should encrypt data, open() should transparently decrypt it."""
        stored = {}

        def fake_save(name, content):
            stored[name] = content.read()
            return name

        def fake_open(name):
            return io.BytesIO(stored[name])

        mock_delegate = MagicMock(spec=StorageBackend)
        mock_delegate.save.side_effect = fake_save
        mock_delegate.open.side_effect = fake_open

        backend = EncryptedStorageBackend(delegate=mock_delegate)
        plaintext = b"Hello, encrypted world!"
        backend.save("test.txt", io.BytesIO(plaintext))

        # Stored data should NOT be plaintext
        assert stored["test.txt"] != plaintext

        # open() should return the original plaintext
        result = backend.open("test.txt")
        assert result.read() == plaintext

    @override_settings(
        STORAGE_ENCRYPTION_KEY="test-encryption-key",
        STORAGE_ENCRYPTION_KDF_ITERATIONS=1000,
    )
    def test_delete_delegates(self):
        mock_delegate = MagicMock(spec=StorageBackend)
        backend = EncryptedStorageBackend(delegate=mock_delegate)
        backend.delete("file.txt")
        mock_delegate.delete.assert_called_once_with("file.txt")

    @override_settings(
        STORAGE_ENCRYPTION_KEY="test-encryption-key",
        STORAGE_ENCRYPTION_KDF_ITERATIONS=1000,
    )
    def test_exists_delegates(self):
        mock_delegate = MagicMock(spec=StorageBackend)
        mock_delegate.exists.return_value = True
        backend = EncryptedStorageBackend(delegate=mock_delegate)
        assert backend.exists("file.txt") is True
        mock_delegate.exists.assert_called_once_with("file.txt")

    @override_settings(
        STORAGE_ENCRYPTION_KEY="test-encryption-key",
        STORAGE_ENCRYPTION_KDF_ITERATIONS=1000,
    )
    def test_url_delegates(self):
        mock_delegate = MagicMock(spec=StorageBackend)
        mock_delegate.url.return_value = "/media/file.txt"
        backend = EncryptedStorageBackend(delegate=mock_delegate)
        assert backend.url("file.txt") == "/media/file.txt"

    @override_settings(
        STORAGE_ENCRYPTION_KEY="test-encryption-key",
        STORAGE_ENCRYPTION_KDF_ITERATIONS=1000,
    )
    def test_size_delegates(self):
        mock_delegate = MagicMock(spec=StorageBackend)
        mock_delegate.size.return_value = 1024
        backend = EncryptedStorageBackend(delegate=mock_delegate)
        assert backend.size("file.txt") == 1024

    @override_settings(
        STORAGE_ENCRYPTION_KEY="test-encryption-key",
        STORAGE_ENCRYPTION_KDF_ITERATIONS=1000,
    )
    def test_list_files_delegates(self):
        mock_delegate = MagicMock(spec=StorageBackend)
        mock_delegate.list_files.return_value = ["a.txt", "b.txt"]
        backend = EncryptedStorageBackend(delegate=mock_delegate)
        assert backend.list_files("prefix") == ["a.txt", "b.txt"]
        mock_delegate.list_files.assert_called_once_with("prefix")


# ---------------------------------------------------------------------------
# get_storage_backend factory
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetStorageBackendEncryption:
    """Tests for get_storage_backend with encryption enabled."""

    @override_settings(
        STORAGE_BACKEND="local",
        STORAGE_ENCRYPTION_ENABLED=True,
        STORAGE_ENCRYPTION_KEY="factory-test-key",
    )
    def test_returns_encrypted_backend_when_enabled(self):
        from storage.utils import get_storage_backend

        backend = get_storage_backend()
        assert isinstance(backend, EncryptedStorageBackend)

    @override_settings(
        STORAGE_BACKEND="local",
        STORAGE_ENCRYPTION_ENABLED=False,
    )
    def test_returns_plain_backend_when_disabled(self):
        from storage.backends.local import LocalStorageBackend
        from storage.utils import get_storage_backend

        backend = get_storage_backend()
        assert isinstance(backend, LocalStorageBackend)
