"""Groq provider implementation (Llama models)."""

from __future__ import annotations

from typing import Any

from caremate.providers.base import LLMProvider
from caremate.utils.config import get_settings


class GroqLLMProvider(LLMProvider):
    """LLM provider using Groq's API for fast Llama inference."""

    def __init__(self, model: str | None = None):
        self._api_key = get_settings().groq_api_key
        if not self._api_key:
            raise ValueError("Groq API key not configured")
        self._model = model or get_settings().groq_model
        self._client = self._create_client()

    def _create_client(self):
        from groq import Groq
        return Groq(api_key=self._api_key)

    @property
    def name(self) -> str:
        return "groq"

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content.strip()

    def embed(self, text: str) -> list[float]:
        # Groq doesn't offer embeddings; fall back to hash-based embedding
        from caremate.providers.mock import _deterministic_embedding
        return _deterministic_embedding(text, dim=384)

    def close(self) -> None:
        pass
