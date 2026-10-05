"""Embedding manager — caching facade around embedding providers."""

from __future__ import annotations

from typing import Optional

from caremate.providers.base import EmbeddingProvider


class EmbeddingManager:
    """Wraps an EmbeddingProvider with caching and batch support.

    Caches embeddings by text hash so the same text is never
    embedded twice, reducing latency and API costs.
    """

    def __init__(self, provider: EmbeddingProvider):
        self._provider = provider
        self._cache: dict[str, list[float]] = {}
        self._cache_keys: list[str] = []  # LRU tracking
        self._max_cache_size: int = 10_000

    @property
    def provider(self) -> EmbeddingProvider:
        return self._provider

    @property
    def name(self) -> str:
        return self._provider.name

    @property
    def dimension(self) -> int:
        return self._provider.dimension()

    def embed(self, text: str) -> list[float]:
        """Get embedding for text, with caching."""
        cache_key = self._cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]

        embedding = self._provider.embed(text)
        self._cache_and_trim(cache_key, embedding)
        return embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for a batch, using cache where possible."""
        results: list[list[float]] = []
        uncached: list[str] = []
        uncached_keys: list[str] = []

        for text in texts:
            key = self._cache_key(text)
            if key in self._cache:
                results.append(self._cache[key])
            else:
                results.append(None)  # type: ignore[list-item]
                uncached.append(text)
                uncached_keys.append(key)

        if uncached:
            embeddings = self._provider.embed_batch(uncached)
            for i, (key, emb) in enumerate(zip(uncached_keys, embeddings)):
                self._cache_and_trim(key, emb)
                # Fill in the placeholder
                placeholder_idx = results.index(None)  # type: ignore[arg-type]
                results[placeholder_idx] = emb

        return results

    def close(self) -> None:
        """Release provider resources."""
        self._provider.close()

    def _cache_key(self, text: str) -> str:
        """Create a cache key from text content."""
        return text.strip()[:500]

    def _cache_and_trim(self, key: str, embedding: list[float]) -> None:
        """Store embedding in cache, trimming if over capacity."""
        if len(self._cache) >= self._max_cache_size:
            oldest = self._cache_keys.pop(0)
            self._cache.pop(oldest, None)
        self._cache[key] = embedding
        self._cache_keys.append(key)
