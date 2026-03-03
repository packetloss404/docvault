"""AES-256-CBC encrypted storage backend.

Wraps another StorageBackend to transparently encrypt on save and decrypt on read.
Uses PyCryptodome with PBKDF2 key derivation and random IV per file.
"""

import hashlib
import io
import struct
from typing import BinaryIO

from django.conf import settings

from .base import StorageBackend

CHUNK_SIZE = 64 * 1024  # 64KB chunks for memory-efficient processing
SALT_SIZE = 16
IV_SIZE = 16  # AES block size
KEY_SIZE = 32  # AES-256
KDF_ITERATIONS = 100_000


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive an AES-256 key from a passphrase using PBKDF2."""
    from Crypto.Protocol.KDF import PBKDF2
    from Crypto.Hash import SHA256

    iterations = getattr(settings, "STORAGE_ENCRYPTION_KDF_ITERATIONS", KDF_ITERATIONS)
    return PBKDF2(
        passphrase.encode("utf-8"),
        salt,
        dkLen=KEY_SIZE,
        count=iterations,
        prf=lambda p, s: hashlib.new("sha256", p + s).digest(),
    )


def _pad(data: bytes) -> bytes:
    """PKCS7 pad to AES block size."""
    pad_len = IV_SIZE - (len(data) % IV_SIZE)
    return data + bytes([pad_len] * pad_len)


def _unpad(data: bytes) -> bytes:
    """Remove PKCS7 padding."""
    pad_len = data[-1]
    if pad_len < 1 or pad_len > IV_SIZE:
        raise ValueError("Invalid padding")
    if data[-pad_len:] != bytes([pad_len] * pad_len):
        raise ValueError("Invalid padding")
    return data[:-pad_len]


def encrypt_stream(plaintext: BinaryIO, passphrase: str) -> BinaryIO:
    """Encrypt a file stream, returning a new stream.

    File format: [salt:16][iv:16][encrypted_data...]
    The last block includes PKCS7 padding.
    """
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes

    salt = get_random_bytes(SALT_SIZE)
    iv = get_random_bytes(IV_SIZE)
    key = _derive_key(passphrase, salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)

    output = io.BytesIO()
    output.write(salt)
    output.write(iv)

    needs_padding_block = True
    while True:
        chunk = plaintext.read(CHUNK_SIZE)
        if not chunk:
            break
        if len(chunk) < CHUNK_SIZE:
            # Last chunk — pad it
            chunk = _pad(chunk)
            output.write(cipher.encrypt(chunk))
            needs_padding_block = False
            break
        output.write(cipher.encrypt(chunk))

    if needs_padding_block:
        # Input was empty or exact multiple of CHUNK_SIZE — add full padding block
        output.write(cipher.encrypt(_pad(b"")))

    output.seek(0)
    return output


def decrypt_stream(ciphertext: BinaryIO, passphrase: str) -> BinaryIO:
    """Decrypt a file stream, returning the plaintext stream.

    Expects format: [salt:16][iv:16][encrypted_data...]
    """
    from Crypto.Cipher import AES

    salt = ciphertext.read(SALT_SIZE)
    iv = ciphertext.read(IV_SIZE)
    if len(salt) != SALT_SIZE or len(iv) != IV_SIZE:
        raise ValueError("Invalid encrypted file: missing salt or IV")

    key = _derive_key(passphrase, salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)

    output = io.BytesIO()
    prev_chunk = None

    while True:
        chunk = ciphertext.read(CHUNK_SIZE)
        if not chunk:
            break
        decrypted = cipher.decrypt(chunk)
        if prev_chunk is not None:
            output.write(prev_chunk)
        prev_chunk = decrypted

    # Unpad the last decrypted chunk
    if prev_chunk is not None:
        output.write(_unpad(prev_chunk))

    output.seek(0)
    return output


class EncryptedStorageBackend(StorageBackend):
    """Storage backend that encrypts files using AES-256-CBC.

    Wraps a delegate backend (local or S3) to transparently encrypt on save
    and decrypt on read. All other operations are delegated directly.
    """

    def __init__(self, delegate: StorageBackend | None = None):
        if delegate is None:
            from .local import LocalStorageBackend
            delegate = LocalStorageBackend()
        self._delegate = delegate
        self._passphrase = getattr(settings, "STORAGE_ENCRYPTION_KEY", "")
        if not self._passphrase:
            raise ValueError(
                "STORAGE_ENCRYPTION_KEY must be set when using encrypted storage."
            )

    def save(self, name: str, content: BinaryIO) -> str:
        encrypted = encrypt_stream(content, self._passphrase)
        return self._delegate.save(name, encrypted)

    def open(self, name: str) -> BinaryIO:
        encrypted = self._delegate.open(name)
        return decrypt_stream(encrypted, self._passphrase)

    def delete(self, name: str) -> None:
        self._delegate.delete(name)

    def exists(self, name: str) -> bool:
        return self._delegate.exists(name)

    def url(self, name: str) -> str:
        return self._delegate.url(name)

    def size(self, name: str) -> int:
        # Return the encrypted size (actual file size on disk)
        return self._delegate.size(name)

    def list_files(self, prefix: str = "") -> list[str]:
        return self._delegate.list_files(prefix)
