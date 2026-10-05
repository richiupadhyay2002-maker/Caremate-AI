"""Anthropic (Claude) provider implementation."""

from __future__ import annotations

from typing import Any

from caremate.providers.base import LLMProvider
from caremate.utils.config import get_settings


class AnthropicLLMProvider(LLMProvider):
    """LLM provider using Anthropic's Claude API."""

    def __init__(self, model: str | None = None):
        self._api_key = get_settings().anthropic_api_key
        if not self._api_key:
            raise ValueError("Anthropic API key not configured")
        self._model = model or get_settings().anthropic_model
        self._client = self._create_client()

    def _create_client(self):
        import anthropic
        return anthropic.Anthropic(api_key=self._api_key)

    @property
    def name(self) -> str:
        return "anthropic"

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> str:
        # Anthropic uses max_output_tokens
        kwargs.setdefault("max_output_tokens", max_tokens)

        if system_prompt:
            response = self._client.messages.create(
                model=self._model,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                **kwargs,
            )
        else:
            response = self._client.messages.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                **kwargs,
            )

        # Concatenate all text content blocks
        text_parts = []
        for content_block in response.content:
            if content_block.type == "text":
                text_parts.append(content_block.text)
        return "".join(text_parts).strip()

    def embed(self, text: str) -> list[float]:
        # Anthropic doesn't offer embeddings; fall back to a simple
        # hash-based embedding. In production, use a dedicated provider.
        from caremate.providers.mock import _deterministic_embedding
        return _deterministic_embedding(text, dim=384)

    def close(self) -> None:
        pass
