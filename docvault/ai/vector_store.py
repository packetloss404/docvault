"""FAISS vector store for document semantic search."""

import logging
import pickle
import threading
from pathlib import Path

import numpy as np
from django.conf import settings

from .constants import DEFAULT_EMBEDDING_DIM

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_store = None


class VectorStore:
    """FAISS-based vector store for document embeddings."""

    def __init__(self, dimension: int = DEFAULT_EMBEDDING_DIM):
        import faiss

        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine after normalize)
        self.doc_ids: list[int] = []  # Maps FAISS row index → document ID
        self._id_to_idx: dict[int, int] = {}  # document ID → FAISS row index

    @property
    def count(self) -> int:
        """Number of vectors in the store."""
        return self.index.ntotal

    def add(self, doc_id: int, embedding: list[float]) -> None:
        """Add or update a document embedding."""
        vector = self._normalize(np.array([embedding], dtype=np.float32))

        if doc_id in self._id_to_idx:
            self.remove(doc_id)

        self.index.add(vector)
        self.doc_ids.append(doc_id)
        self._id_to_idx[doc_id] = len(self.doc_ids) - 1

    def add_batch(self, doc_ids: list[int], embeddings: list[list[float]]) -> None:
        """Add multiple document embeddings at once."""
        if not doc_ids:
            return

        # Remove existing entries first
        for doc_id in doc_ids:
            if doc_id in self._id_to_idx:
                self.remove(doc_id)

        vectors = self._normalize(np.array(embeddings, dtype=np.float32))
        base_idx = len(self.doc_ids)

        self.index.add(vectors)
        self.doc_ids.extend(doc_ids)
        for i, doc_id in enumerate(doc_ids):
            self._id_to_idx[doc_id] = base_idx + i

    def remove(self, doc_id: int) -> bool:
        """Remove a document embedding. Requires a full rebuild."""
        if doc_id not in self._id_to_idx:
            return False

        # FAISS IndexFlatIP doesn't support removal.
        # Mark for removal and rebuild at next opportunity.
        idx = self._id_to_idx.pop(doc_id)
        self.doc_ids[idx] = -1  # Tombstone
        return True

    def search(self, query_embedding: list[float], k: int = 10) -> list[tuple[int, float]]:
        """Search for the k nearest documents.

        Returns:
            List of (document_id, similarity_score) tuples, sorted by descending score.
        """
        if self.index.ntotal == 0:
            return []

        query = self._normalize(np.array([query_embedding], dtype=np.float32))
        k = min(k, self.index.ntotal)
        scores, indices = self.index.search(query, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.doc_ids):
                continue
            doc_id = self.doc_ids[idx]
            if doc_id == -1:  # Tombstoned
                continue
            results.append((doc_id, float(score)))

        return results

    def rebuild(self, doc_ids: list[int], embeddings: list[list[float]]) -> None:
        """Rebuild the entire index from scratch."""
        import faiss

        self.index = faiss.IndexFlatIP(self.dimension)
        self.doc_ids = []
        self._id_to_idx = {}

        if doc_ids:
            self.add_batch(doc_ids, embeddings)

    def save(self, path: Path | None = None) -> None:
        """Persist the index to disk."""
        if path is None:
            path = self._default_path()

        path.mkdir(parents=True, exist_ok=True)
        import faiss

        faiss.write_index(self.index, str(path / "index.faiss"))

        with open(path / "metadata.pkl", "wb") as f:
            pickle.dump({
                "doc_ids": self.doc_ids,
                "id_to_idx": self._id_to_idx,
                "dimension": self.dimension,
            }, f)

        logger.info("Saved vector store (%d vectors) to %s", self.count, path)

    @classmethod
    def load(cls, path: Path | None = None) -> "VectorStore":
        """Load the index from disk."""
        if path is None:
            path = cls._default_path()

        import faiss

        index_path = path / "index.faiss"
        meta_path = path / "metadata.pkl"

        if not index_path.exists() or not meta_path.exists():
            logger.info("No existing vector store found at %s", path)
            return cls()

        store = cls.__new__(cls)
        store.index = faiss.read_index(str(index_path))

        with open(meta_path, "rb") as f:
            meta = pickle.load(f)

        store.doc_ids = meta["doc_ids"]
        store._id_to_idx = meta["id_to_idx"]
        store.dimension = meta["dimension"]

        logger.info("Loaded vector store (%d vectors) from %s", store.count, path)
        return store

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        """L2-normalize vectors for cosine similarity via inner product."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return vectors / norms

    @staticmethod
    def _default_path() -> Path:
        media_root = Path(settings.MEDIA_ROOT)
        return media_root / "vector_index"


def get_vector_store() -> VectorStore:
    """Return the global vector store singleton, loading from disk if needed."""
    global _store
    if _store is not None:
        return _store

    with _lock:
        if _store is not None:
            return _store
        _store = VectorStore.load()
    return _store


def reset_vector_store():
    """Reset the vector store singleton (for testing)."""
    global _store
    _store = None
