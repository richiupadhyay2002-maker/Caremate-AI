"""Factory for selecting LLM and embedding providers.

Reads configuration from environment variables and instantiates the
appropriate provider, falling back to the Mock provider when no
API keys are configured.
"""

from __future__ import annotations

from typing import Any

from caremate.providers.base import LLMProvider, EmbeddingProvider
from caremate.providers.mock import MockLLMProvider, MockEmbeddingProvider
from caremate.utils.config import get_settings

# Optional imports for real providers (only needed when API keys are set)
try:
    from caremate.providers.openai import OpenAILLMProvider, OpenAIEmbeddingProvider
    _HAS_OPENAI = True
except Exception:  # ImportError, etc.
    OpenAILLMProvider = None  # type: ignore
    OpenAIEmbeddingProvider = None  # type: ignore
    _HAS_OPENAI = False

try:
    from caremate.providers.anthropic import AnthropicLLMProvider
    _HAS_ANTHROPIC = True
except Exception:
    AnthropicLLMProvider = None  # type: ignore
    _HAS_ANTHROPIC = False

try:
    from caremate.providers.groq import GroqLLMProvider
    _HAS_GROQ = True
except Exception:
    GroqLLMProvider = None  # type: ignore
    _HAS_GROQ = False


class LLMFactory:
    """Factory that creates LLM and embedding providers based on settings."""

    _llm_cache: dict[str, LLMProvider] = {}
    _embedding_cache: dict[str, EmbeddingProvider] = {}

    @classmethod
    def create_llm(cls, provider_name: str | None = None) -> LLMProvider:
        """Create (or return cached) LLM provider.

        Args:
            provider_name: Override provider name. If None, uses settings.

        Returns:
            An LLMProvider instance.
        """
        if provider_name is None:
            settings = get_settings()
            provider_name = settings.effective_llm_provider

        if provider_name in cls._llm_cache:
            return cls._llm_cache[provider_name]

        if provider_name == "mock":
            provider = MockLLMProvider()
        elif provider_name == "openai":
            if not _HAS_OPENAI or not OpenAILLMProvider:
                raise ImportError("OpenAI provider not available. Install 'openai' package.")
            provider = OpenAILLMProvider()
        elif provider_name == "anthropic":
            if not _HAS_ANTHROPIC or not AnthropicLLMProvider:
                raise ImportError("Anthropic provider not available. Install 'anthropic' package.")
            provider = AnthropicLLMProvider()
        elif provider_name == "groq":
            if not _HAS_GROQ or not GroqLLMProvider:
                raise ImportError("Groq provider not available. Install 'groq' package.")
            provider = GroqLLMProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")

        cls._llm_cache[provider_name] = provider
        return provider

    @classmethod
    def create_embedding_provider(cls, provider_name: str | None = None) -> EmbeddingProvider:
        """Create (or return cached) embedding provider.

        Args:
            provider_name: Override provider name. If None, uses settings.

        Returns:
            An EmbeddingProvider instance.
        """
        if provider_name is None:
            settings = get_settings()
            # If LLM is real, prefer sentence-transformers for embeddings
            # (OpenAI/Anthropic embeddings cost money), else mock is fine
            if settings.effective_llm_provider == "mock":
                provider_name = "sentence_transformers"
            else:
                provider_name = settings.embedding_provider

        if provider_name in cls._embedding_cache:
            return cls._embedding_cache[provider_name]

        if provider_name == "mock":
            provider = MockEmbeddingProvider(dim=get_settings().vector_dim)
        elif provider_name == "sentence_transformers":
            from caremate.providers.sentence_transformer import SentenceTransformerEmbeddingProvider
            provider = SentenceTransformerEmbeddingProvider()
        elif provider_name == "openai":
            if not _HAS_OPENAI or not OpenAIEmbeddingProvider:
                raise ImportError("OpenAI embedding provider not available.")
            provider = OpenAIEmbeddingProvider()
        else:
            raise ValueError(f"Unknown embedding provider: {provider_name}")

        cls._embedding_cache[provider_name] = provider
        return provider

    @classmethod
    def clear_cache(cls) -> None:
        """Close and clear cached providers."""
        for provider in cls._llm_cache.values():
            provider.close()
        for provider in cls._embedding_cache.values():
            provider.close()
        cls._llm_cache.clear()
        cls._embedding_cache.clear()
