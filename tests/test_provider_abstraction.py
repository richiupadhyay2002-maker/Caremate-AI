"""Tests for provider abstraction — mock and structured output.

Verifies that the provider abstraction layer works correctly with the
Mock provider, producing typed responses and consistent embeddings.
"""

import pytest

from caremate.providers.mock import MockLLMProvider, MockEmbeddingProvider
from caremate.providers.factory import LLMFactory
from caremate.utils.config import get_settings
from caremate.models.response import StructuredAIResponse, Citation


def test_mock_llm_generates_structured_response():
    """The mock LLM can generate structured (JSON) responses."""
    provider = MockLLMProvider()
    response = provider.generate(prompt="Generate structured output for testing")
    # The mock returns a JSON string when "structured" is detected
    import json
    data = json.loads(response)
    assert "response" in data
    assert "citations" in data
    assert "confidence" in data
    assert "safety_flags" in data
    assert isinstance(data["citations"], list)


def test_mock_embedding_consistency():
    """The mock embedding provider produces consistent, reproducible embeddings."""
    provider = MockEmbeddingProvider(dim=384)
    emb1 = provider.embed("Patient has diabetes and needs insulin management.")
    emb2 = provider.embed("Patient has diabetes and needs insulin management.")
    emb3 = provider.embed("Completely different text about weather today.")

    assert len(emb1) == 384
    assert emb1 == emb2  # deterministic
    assert emb1 != emb3  # different text → different embedding


def test_mock_embedding_batch():
    """Batch embedding returns same count and valid vectors."""
    provider = MockEmbeddingProvider(dim=128)
    texts = ["First patient note", "Second patient note", "Third patient note"]
    embeddings = provider.embed_batch(texts)
    assert len(embeddings) == 3
    assert all(len(e) == 128 for e in embeddings)


def test_factory_creates_mock_in_zero_key_mode(monkeypatch):
    """LLMFactory creates a mock provider when no API keys are set."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    get_settings.cache_clear()  # force re-read with no keys

    factory = LLMFactory()
    llm = factory.create_llm()
    assert llm.name == "mock"

    factory.clear_cache()
    get_settings.cache_clear()

