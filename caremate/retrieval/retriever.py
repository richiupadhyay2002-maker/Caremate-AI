"""Hybrid retriever with BM25 + embedding similarity and reranking."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Optional

from caremate.models.document import DocumentChunk
from caremate.providers.base import EmbeddingProvider


class HybridRetriever:
    """Combines keyword (BM25) and embedding similarity for retrieval.

    Retrieves top-k chunks from the vector store, then reranks
    using a combination of embedding similarity and keyword overlap.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store,
        alpha: float = 0.7,  # weight for embedding score (1-alpha for BM25)
        top_k: int = 5,
    ):
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._alpha = alpha
        self._top_k = top_k
        self._doc_freq: dict[str, int] = {}
        self._total_docs: int = 0
        self._built: bool = False

    def build_index(self, chunks: list[DocumentChunk]) -> None:
        """Pre-compute BM25 statistics from a set of chunks."""
        self._doc_freq.clear()
        self._total_docs = len(chunks)
        for chunk in chunks:
            tokens = self._tokenize(chunk.content)
            for token in set(tokens):
                self._doc_freq[token] = self._doc_freq.get(token, 0) + 1
        self._built = True

    def retrieve(
        self,
        query: str,
        patient_id: str,
        k: Optional[int] = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """Retrieve and rerank the top-k relevant chunks for a query.

        Args:
            query: The user's query/question.
            patient_id: Patient whose records to search (enforces isolation).
            k: Number of results (defaults to self._top_k).

        Returns:
            List of (chunk, combined_score) pairs, sorted by score descending.
        """
        if k is None:
            k = self._top_k

        # Step 1: Embedding-based retrieval from vector store
        embedding_results = self._vector_store.search_by_text(
            query, patient_id, self._embedding_provider, k=k * 5
        )
        if not embedding_results:
            return []

        # Step 2: Rerank using BM25
        reranked = self._rerank(query, embedding_results)

        return reranked[:k]

    def retrieve_with_context(
        self,
        query: str,
        patient_id: str,
        context_chunks: list[DocumentChunk],
        k: Optional[int] = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """Retrieve from a specific set of chunks (for testing/direct use).

        This bypasses the vector store and operates purely on the provided
        chunk list, using embedding + BM25 reranking.
        """
        if k is None:
            k = self._top_k

        # Embed query
        query_emb = self._embedding_provider.embed(query)

        # Score each chunk
        results: list[tuple[DocumentChunk, float]] = []
        for chunk in context_chunks:
            # Only include chunks for this patient
            if chunk.patient_id != patient_id:
                continue
            if chunk.embedding is None:
                chunk.embedding = self._embedding_provider.embed(chunk.content)

            emb_score = self._cosine_similarity(query_emb, chunk.embedding)
            bm25_score = self._bm25_score(query, chunk.content)

            # Normalize BM25 (rough): divide by average BM25
            bm25_norm = bm25_score / 10.0 if bm25_score > 0 else 0.0

            combined = self._alpha * emb_score + (1 - self._alpha) * bm25_norm
            results.append((chunk, combined))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    def _rerank(
        self,
        query: str,
        results: list[tuple[DocumentChunk, float]],
    ) -> list[tuple[DocumentChunk, float]]:
        """Rerank vector-search results using BM25 keyword scoring."""
        reranked: list[tuple[DocumentChunk, float]] = []
        for chunk, emb_score in results:
            bm25 = self._bm25_score(query, chunk.content)
            bm25_norm = bm25 / 10.0 if bm25 > 0 else 0.0
            combined = self._alpha * emb_score + (1 - self._alpha) * bm25_norm
            reranked.append((chunk, combined))

        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked

    def _tokenize(self, text: str) -> list[str]:
        """Simple lowercased tokenization."""
        return re.findall(r"\b[a-z]+\b", text.lower())

    def _bm25_score(self, query: str, doc: str) -> float:
        """Compute a simplified BM25 score for a query-document pair."""
        tokens = self._tokenize(doc)
        q_tokens = self._tokenize(query)

        if not q_tokens:
            return 0.0

        doc_len = len(tokens)
        if doc_len == 0:
            return 0.0

        tf = Counter(tokens)
        score = 0.0
        k1 = 1.2
        b = 0.75

        # Average document length (approximate)
        avg_dl = max(doc_len, 100)

        for token in q_tokens:
            idf = math.log(1 + (self._total_docs - self._doc_freq.get(token, 0) + 0.5)
                          / (self._doc_freq.get(token, 0) + 0.5))
            tf_val = tf.get(token, 0)
            score += idf * (tf_val * (k1 + 1)) / (tf_val + k1 * (1 - b + b * doc_len / avg_dl))

        return score

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
