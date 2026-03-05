"""Tests for content-addressable storage backend and ContentBlob model."""

import hashlib
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model

from storage.backends.content_addressed import ContentAddressedStorageBackend
from storage.models import ContentBlob

User = get_user_model()


def _make_content(data: bytes = b"hello world") -> BytesIO:
    return BytesIO(data)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def mock_backend():
    """A mock underlying StorageBackend."""
    backend = MagicMock()
    backend.save.side_effect = lambda name, content: name
    backend.open.side_effect = lambda name: BytesIO(b"hello world")
    backend.delete.return_value = None
    backend.exists.return_value = True
    backend.url.side_effect = lambda name: f"http://storage/{name}"
    backend.size.return_value = 11
    return backend


@pytest.fixture
def cas(mock_backend):
    return ContentAddressedStorageBackend(mock_backend)


# ===========================================================================
# ContentBlob Model
# ===========================================================================


@pytest.mark.django_db
def test_content_blob_creation():
    blob = ContentBlob.objects.create(
        sha256_hash="a" * 64,
        size=1024,
        reference_count=1,
        storage_backend="local",
        storage_path="aa/aa/aaaa",
    )
    assert blob.sha256_hash == "a" * 64
    assert blob.size == 1024
    assert blob.reference_count == 1
    assert blob.storage_backend == "local"
    assert blob.created_at is not None
    assert blob.last_accessed is None


@pytest.mark.django_db
def test_content_blob_str():
    blob = ContentBlob.objects.create(
        sha256_hash="abcdef1234" + "0" * 54,
        size=2048,
        reference_count=3,
        storage_backend="local",
        storage_path="ab/cd/abcdef1234" + "0" * 54,
    )
    s = str(blob)
    assert "Blob" in s
    assert "abcdef1234" in s
    assert "2048" in s
    assert "3 refs" in s


@pytest.mark.django_db
def test_content_blob_primary_key_is_hash():
    h = "b" * 64
    blob = ContentBlob.objects.create(
        sha256_hash=h, size=100, storage_path="bb/bb/" + h
    )
    assert ContentBlob.objects.get(pk=h) == blob


# ===========================================================================
# _compute_hash and _hash_to_path
# ===========================================================================


def test_compute_hash():
    data = b"test data for hashing"
    content = BytesIO(data)
    hex_digest, size = ContentAddressedStorageBackend._compute_hash(content)
    assert hex_digest == hashlib.sha256(data).hexdigest()
    assert size == len(data)
    # Stream should be reset to beginning
    assert content.read() == data


def test_hash_to_path():
    h = "abcdef1234567890" + "0" * 48
    path = ContentAddressedStorageBackend._hash_to_path(h)
    assert path == f"ab/cd/{h}"


# ===========================================================================
# save
# ===========================================================================


@pytest.mark.django_db
def test_save_new_file(cas, mock_backend):
    data = b"new file content"
    content = _make_content(data)
    expected_hash = _sha256(data)

    result = cas.save("test.pdf", content)

    assert result == expected_hash
    blob = ContentBlob.objects.get(pk=expected_hash)
    assert blob.reference_count == 1
    assert blob.size == len(data)
    mock_backend.save.assert_called_once()


@pytest.mark.django_db
def test_save_duplicate_increments_ref_count(cas, mock_backend):
    data = b"duplicate content"
    expected_hash = _sha256(data)

    # First save
    cas.save("file1.pdf", _make_content(data))
    blob = ContentBlob.objects.get(pk=expected_hash)
    assert blob.reference_count == 1

    # Second save with same content
    result = cas.save("file2.pdf", _make_content(data))
    assert result == expected_hash

    blob.refresh_from_db()
    assert blob.reference_count == 2

    # Underlying backend save should only be called once (for the first save)
    assert mock_backend.save.call_count == 1


@pytest.mark.django_db
def test_save_different_content_creates_separate_blobs(cas, mock_backend):
    data1 = b"content one"
    data2 = b"content two"

    hash1 = cas.save("file1.pdf", _make_content(data1))
    hash2 = cas.save("file2.pdf", _make_content(data2))

    assert hash1 != hash2
    assert ContentBlob.objects.count() == 2


# ===========================================================================
# delete
# ===========================================================================


@pytest.mark.django_db
def test_delete_decrements_ref_count(cas, mock_backend):
    data = b"ref count data"
    sha = _sha256(data)

    cas.save("file1.pdf", _make_content(data))
    cas.save("file2.pdf", _make_content(data))

    blob = ContentBlob.objects.get(pk=sha)
    assert blob.reference_count == 2

    cas.delete(sha)
    blob.refresh_from_db()
    assert blob.reference_count == 1
    # File should NOT be deleted from underlying backend
    mock_backend.delete.assert_not_called()


@pytest.mark.django_db
def test_delete_removes_blob_at_zero_refs(cas, mock_backend):
    data = b"single ref data"
    sha = _sha256(data)

    cas.save("file.pdf", _make_content(data))
    blob = ContentBlob.objects.get(pk=sha)
    assert blob.reference_count == 1

    cas.delete(sha)
    assert not ContentBlob.objects.filter(pk=sha).exists()
    mock_backend.delete.assert_called_once()


@pytest.mark.django_db
def test_delete_nonexistent_blob(cas, mock_backend):
    """Deleting a non-existent blob should not raise."""
    cas.delete("nonexistent" + "0" * 54)
    mock_backend.delete.assert_not_called()


# ===========================================================================
# open
# ===========================================================================


@pytest.mark.django_db
def test_open_file(cas, mock_backend):
    data = b"readable data"
    sha = _sha256(data)
    cas.save("file.pdf", _make_content(data))

    # Override the mock to return the correct data for this test
    mock_backend.open.side_effect = None
    mock_backend.open.return_value = BytesIO(data)
    fh = cas.open(sha)
    assert fh.read() == data

    # last_accessed should be updated
    blob = ContentBlob.objects.get(pk=sha)
    assert blob.last_accessed is not None


@pytest.mark.django_db
def test_open_nonexistent_raises(cas):
    with pytest.raises(FileNotFoundError):
        cas.open("nonexistent" + "0" * 54)


# ===========================================================================
# exists
# ===========================================================================


@pytest.mark.django_db
def test_exists_true(cas):
    data = b"exists data"
    sha = _sha256(data)
    cas.save("file.pdf", _make_content(data))
    assert cas.exists(sha) is True


@pytest.mark.django_db
def test_exists_false(cas):
    assert cas.exists("nonexistent" + "0" * 54) is False


# ===========================================================================
# get_dedup_stats
# ===========================================================================


@pytest.mark.django_db
def test_get_dedup_stats_empty(cas):
    stats = cas.get_dedup_stats()
    assert stats["total_blobs"] == 0
    assert stats["total_references"] == 0
    assert stats["total_stored_bytes"] == 0
    assert stats["bytes_saved"] == 0
    assert stats["dedup_ratio"] == 1.0


@pytest.mark.django_db
def test_get_dedup_stats_with_data(cas):
    data = b"dedup test data!!"
    cas.save("file1.pdf", _make_content(data))
    cas.save("file2.pdf", _make_content(data))

    stats = cas.get_dedup_stats()
    assert stats["total_blobs"] == 1
    assert stats["total_references"] == 2
    assert stats["total_stored_bytes"] == len(data)
    # logical_bytes = size * ref_count = len(data) * 2
    assert stats["logical_bytes"] == len(data) * 2
    assert stats["bytes_saved"] == len(data)
    assert stats["dedup_ratio"] == 2.0
    assert stats["avg_refs_per_blob"] == 2.0


# ===========================================================================
# hash-based path generation
# ===========================================================================


def test_hash_based_path_sharding():
    """Path should use first 2 and next 2 characters as directory shards."""
    h = "1234567890abcdef" + "f" * 48
    path = ContentAddressedStorageBackend._hash_to_path(h)
    parts = path.split("/")
    assert len(parts) == 3
    assert parts[0] == "12"
    assert parts[1] == "34"
    assert parts[2] == h
