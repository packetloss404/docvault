"""Tests for the FAISS vector store."""

import pickle
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from ai.vector_store import VectorStore, get_vector_store, reset_vector_store


@pytest.fixture(autouse=True)
def _reset_store():
    """Reset the vector store singleton between tests."""
    reset_vector_store()
    yield
    reset_vector_store()


def _random_embedding(dim=128):
    """Generate a random normalized embedding vector."""
    vec = np.random.randn(dim).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return vec.tolist()


class TestVectorStoreCreation:
    """Tests for VectorStore initialization."""

    def test_empty_store_creation(self):
        """A new VectorStore should be empty."""
        store = VectorStore(dimension=128)
        assert store.count == 0
        assert store.doc_ids == []
        assert store.dimension == 128

    def test_count_property(self):
        """The count property reflects the number of indexed vectors."""
        store = VectorStore(dimension=128)
        assert store.count == 0

        store.add(1, _random_embedding())
        assert store.count == 1

        store.add(2, _random_embedding())
        assert store.count == 2


class TestVectorStoreAdd:
    """Tests for adding vectors to the store."""

    def test_add_single_vector(self):
        """Adding a single vector increases count and tracks doc_id."""
        store = VectorStore(dimension=128)
        store.add(42, _random_embedding())
        assert store.count == 1
        assert 42 in store.doc_ids

    def test_add_batch_multiple_vectors(self):
        """add_batch adds multiple vectors at once."""
        store = VectorStore(dimension=128)
        embeddings = [_random_embedding() for _ in range(5)]
        doc_ids = [10, 20, 30, 40, 50]
        store.add_batch(doc_ids, embeddings)
        assert store.count == 5
        for doc_id in doc_ids:
            assert doc_id in store.doc_ids

    def test_add_replaces_existing(self):
        """Adding a vector for an existing doc_id replaces it (remove + add)."""
        store = VectorStore(dimension=128)
        emb1 = _random_embedding()
        emb2 = _random_embedding()
        store.add(1, emb1)
        store.add(1, emb2)
        # Should only have one non-tombstoned entry
        active_ids = [d for d in store.doc_ids if d != -1]
        assert len(active_ids) == 1
        assert active_ids[0] == 1


class TestVectorStoreSearch:
    """Tests for searching the vector store."""

    def test_search_returns_correct_document(self):
        """Searching with a known vector should return the matching document."""
        store = VectorStore(dimension=128)
        emb = _random_embedding()
        store.add(99, emb)

        results = store.search(emb, k=5)
        assert len(results) > 0
        doc_ids = [doc_id for doc_id, _ in results]
        assert 99 in doc_ids

    def test_search_sorted_by_score_descending(self):
        """Results should be sorted by similarity score in descending order."""
        dim = 128
        store = VectorStore(dimension=dim)

        # Add multiple documents
        for i in range(10):
            store.add(i, _random_embedding(dim))

        query = _random_embedding(dim)
        results = store.search(query, k=10)
        scores = [score for _, score in results]
        # Verify descending order
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_search_empty_store_returns_empty(self):
        """Searching an empty store should return an empty list."""
        store = VectorStore(dimension=128)
        results = store.search(_random_embedding(), k=10)
        assert results == []


class TestVectorStoreRemove:
    """Tests for removing vectors from the store."""

    def test_remove_tombstones_document(self):
        """Removing a document should tombstone it (set doc_id to -1)."""
        store = VectorStore(dimension=128)
        store.add(1, _random_embedding())
        store.add(2, _random_embedding())
        store.add(3, _random_embedding())

        result = store.remove(2)
        assert result is True
        # Doc ID 2 should be tombstoned
        assert -1 in store.doc_ids
        # Searching should not return doc 2
        query = _random_embedding()
        search_results = store.search(query, k=10)
        returned_ids = [doc_id for doc_id, _ in search_results]
        assert 2 not in returned_ids

    def test_remove_nonexistent_returns_false(self):
        """Removing a non-existent document should return False."""
        store = VectorStore(dimension=128)
        store.add(1, _random_embedding())
        result = store.remove(999)
        assert result is False


class TestVectorStoreRebuild:
    """Tests for rebuilding the vector store index."""

    def test_rebuild_replaces_entire_index(self):
        """rebuild() should replace all existing data."""
        store = VectorStore(dimension=128)
        store.add(1, _random_embedding())
        store.add(2, _random_embedding())
        assert store.count == 2

        # Rebuild with different data
        new_embeddings = [_random_embedding() for _ in range(3)]
        store.rebuild([10, 20, 30], new_embeddings)
        assert store.count == 3
        assert 1 not in store.doc_ids
        assert 2 not in store.doc_ids
        assert 10 in store.doc_ids
        assert 20 in store.doc_ids
        assert 30 in store.doc_ids


class TestVectorStorePersistence:
    """Tests for save/load functionality."""

    def test_save_and_load_roundtrip(self, tmp_path):
        """Saving and loading should preserve the index and metadata."""
        store = VectorStore(dimension=64)
        emb1 = _random_embedding(64)
        emb2 = _random_embedding(64)
        store.add(100, emb1)
        store.add(200, emb2)

        save_path = tmp_path / "vector_index"
        store.save(save_path)

        loaded = VectorStore.load(save_path)
        assert loaded.count == 2
        assert loaded.dimension == 64
        assert 100 in loaded.doc_ids
        assert 200 in loaded.doc_ids

        # Search should work on loaded store
        results = loaded.search(emb1, k=5)
        assert len(results) > 0
        doc_ids = [doc_id for doc_id, _ in results]
        assert 100 in doc_ids

    def test_load_nonexistent_path_returns_empty_store(self, tmp_path):
        """Loading from a non-existent path should return an empty store."""
        nonexistent = tmp_path / "does_not_exist"
        store = VectorStore.load(nonexistent)
        assert store.count == 0


class TestGetVectorStoreSingleton:
    """Tests for the get_vector_store() singleton."""

    @patch("ai.vector_store.VectorStore.load")
    def test_singleton_behavior(self, mock_load):
        """get_vector_store() should return the same instance on repeated calls."""
        mock_store = VectorStore(dimension=128)
        mock_load.return_value = mock_store

        store1 = get_vector_store()
        store2 = get_vector_store()
        assert store1 is store2
        # load() should only be called once
        mock_load.assert_called_once()
