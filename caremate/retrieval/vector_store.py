"""Patient-isolated FAISS vector store.

Every chunk is tagged with a patient_id. Search results are filtered
to only return chunks belonging to the specified patient, making it
architecturally impossible for one patient's data to leak into another's
query results.
"""

from __future__ import annotations

import logging
from typing import Optional

import faiss
import numpy as np

from caremate.models.document import DocumentChunk
from caremate.utils.config import get_logger

logger = get_logger(__name__)


class PatientIsolatedVectorStore:
    """A FAISS-based vector store that enforces strict patient isolation.

    Each chunk added to the store must include a patient_id. When searching,
    a patient_id is required and only chunks matching that patient are returned.

    This isolation is the core safety guarantee of the RAG pipeline.
    """

    def __init__(self, dim: int = 384):
        self._dim = dim
        self._index: faiss.IndexFlatIP = faiss.IndexFlatIP(dim)
        self._id_to_chunk: dict[int, DocumentChunk] = {}
        self._patient_chunks: dict[str, list[int]] = {}
        self._next_id: int = 0

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def total_chunks(self) -> int:
        return len(self._id_to_chunk)

    @property
    def patients(self) -> list[str]:
        """Return all patient IDs in the store."""
        return list(self._patient_chunks.keys())

    # ------------------------------------------------------------------
    # Insertion
    # ------------------------------------------------------------------
    def add_chunk(self, chunk: DocumentChunk) -> int:
        """Add a single chunk to the store.

        Requires a non-empty patient_id and a pre-computed embedding.
        Returns the internal FAISS index ID.
        """
        if not chunk.patient_id:
            raise ValueError("Chunk must have a patient_id — patient isolation enforced")
        if chunk.embedding is None:
            raise ValueError("Chunk must have an embedding vector")

        vec = np.array([chunk.embedding], dtype=np.float32)
        faiss.normalize_L2(vec)  # normalize for cosine similarity
        self._index.add(vec)

        internal_id = self._next_id
        self._next_id += 1

        self._id_to_chunk[internal_id] = chunk
        self._patient_chunks.setdefault(chunk.patient_id, []).append(internal_id)
        return internal_id

    def add_chunks(self, chunks: list[DocumentChunk]) -> list[int]:
        """Add multiple chunks at once."""
        return [self.add_chunk(c) for c in chunks]

    # ------------------------------------------------------------------
    # Search (patient-isolated)
    # ------------------------------------------------------------------
    def search(
        self,
        query_embedding: list[float],
        patient_id: str,
        k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        """Search for similar chunks, filtered to a single patient.

        Only chunks whose patient_id matches the provided patient_id
        are returned. If the patient has no chunks, returns empty list.
        """
        if patient_id not in self._patient_chunks:
            return []
        if self._index.ntotal == 0:
            return []

        # Over-search to account for patient filtering
        search_k = max(k * 3, 50)
        query_vec = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_vec)

        scores, indices = self._index.search(query_vec, min(search_k, self._index.ntotal))

        results: list[tuple[DocumentChunk, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk = self._id_to_chunk.get(idx)
            if chunk is None:
                continue
            # Enforce patient isolation
            if chunk.patient_id != patient_id:
                continue
            results.append((chunk, float(score)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    def search_by_text(
        self,
        query: str,
        patient_id: str,
        embedding_provider,
        k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        """Convenience: embed the query text, then search."""
        emb = embedding_provider.embed(query)
        return self.search(emb, patient_id=patient_id, k=k)

    # ------------------------------------------------------------------
    # Patient management
    # ------------------------------------------------------------------
    def get_patient_chunks(self, patient_id: str) -> list[DocumentChunk]:
        """Return all chunks for a specific patient."""
        if patient_id not in self._patient_chunks:
            return []
        return [self._id_to_chunk[i] for i in self._patient_chunks[patient_id]
                if i in self._id_to_chunk]

    def has_patient(self, patient_id: str) -> bool:
        """Check if any chunks exist for a given patient."""
        return patient_id in self._patient_chunks and len(self._patient_chunks[patient_id]) > 0

    def remove_patient(self, patient_id: str) -> int:
        """Remove all metadata for a patient. Returns number removed."""
        if patient_id not in self._patient_chunks:
            return 0
        count = len(self._patient_chunks[patient_id])
        for internal_id in self._patient_chunks[patient_id]:
            self._id_to_chunk.pop(internal_id, None)
        del self._patient_chunks[patient_id]
        logger.info("Removed %d chunks for patient %s", count, patient_id)
        return count

    def clear(self) -> None:
        """Remove all chunks and reset the index."""
        self._index.reset()
        self._id_to_chunk.clear()
        self._patient_chunks.clear()
        self._next_id = 0
