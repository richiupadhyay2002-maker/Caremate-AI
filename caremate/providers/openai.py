"""OpenAI provider implementation for ChatGPT and embeddings."""

from __future__ import annotations

import os
from typing import Any, Optional

from pydantic import BaseModel

from caremate.providers.base import LLMProvider, EmbeddingProvider
from caremate.utils.config import get_settings


class OpenAILLMProvider(LLMProvider):
    """LLM provider using OpenAI's chat completions API."""

    def __init__(self, model: str | None = None):
        self._api_key = get_settings().openai_api_key
        if not self._api_key:
            raise ValueError("OpenAI API key not configured")
        self._model = model or get_settings().openai_model
        self._client = self._create_client()

    def _create_client(self):
        from openai import OpenAI
        return OpenAI(api_key=self._api_key)

    @property
    def name(self) -> str:
        return "openai"

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
        response = self._client.embeddings.create(
            model=get_settings().openai_embedding_model,
            input=text,
        )
        return response.data[0].embedding

    def close(self) -> None:
        self._client.close()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using OpenAI's embeddings API."""

    def __init__(self, model: str | None = None):
        self._api_key = get_settings().openai_api_key
        if not self._api_key:
            raise ValueError("OpenAI API key not configured")
        self._model = model or get_settings().openai_embedding_model
        self._client = self._create_client()

    def _create_client(self):
        from openai import OpenAI
        return OpenAI(api_key=self._api_key)

    @property
    def name(self) -> str:
        return "openai"

    def embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(model=self._model, input=text)
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]

    def dimension(self) -> int:
        return 1536  # text-embedding-3-small default

    def close(self) -> None:
        self._client.close()
