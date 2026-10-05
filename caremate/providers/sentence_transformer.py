"""Sentence Transformers embedding provider (local, offline embeddings).

Uses a lightweight transformer model to produce high-quality embeddings
without requiring an external API. Falls back to mock embeddings if
the model cannot be loaded.
"""

from __future__ import annotations

import threading

from caremate.providers.base import EmbeddingProvider
from caremate.providers.mock import _deterministic_embedding


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using locally-run sentence-transformer models."""

    # Cache the model instance across provider instances
    _model_lock = threading.Lock()
    _model = None
    _model_name = None

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        if SentenceTransformerEmbeddingProvider._model is None or \
           SentenceTransformerEmbeddingProvider._model_name != model_name:
            with SentenceTransformerEmbeddingProvider._model_lock:
                # Double-check inside lock
                if SentenceTransformerEmbeddingProvider._model is None or \
                   SentenceTransformerEmbeddingProvider._model_name != model_name:
                    SentenceTransformerEmbeddingProvider._model = self._load_model(model_name)
                    SentenceTransformerEmbeddingProvider._model_name = model_name

    def _load_model(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
            return SentenceTransformer(model_name)
        except Exception:
            return None

    @property
    def name(self) -> str:
        return "sentence_transformers"

    def embed(self, text: str) -> list[float]:
        model = SentenceTransformerEmbeddingProvider._model
        if model is not None:
            emb = model.encode([text], convert_to_numpy=True)
            return emb[0].tolist()
        # Fallback to mock deterministic embedding
        return _deterministic_embedding(text, dim=384)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = SentenceTransformerEmbeddingProvider._model
        if model is not None:
            embs = model.encode(texts, convert_to_numpy=True)
            return embs.tolist()
        return [_deterministic_embedding(text, dim=384) for text in texts]

    def dimension(self) -> int:
        model = SentenceTransformerEmbeddingProvider._model
        if model is not None:
            try:
                return int(model.get_sentence_embedding_dimension())
            except Exception:
                pass
        return 384  # all-MiniLM-L6-v2 default dimension

    def close(self) -> None:
        # Keep model cached for reuse
        pass
