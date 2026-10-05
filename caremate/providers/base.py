"""Abstract base classes for LLM and embedding providers.

This module defines the provider-agnostic interface that all LLM and
embedding implementations (OpenAI, Anthropic, Groq, Mock) must conform to.
"""

from __future__ import annotations

import abc
from typing import Any, Optional, TypeVar, Union, get_args, get_origin

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(abc.ABC):
    """Abstract base class for LLM text-generation providers."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable provider name, e.g. 'openai', 'mock'."""
        ...

    @abc.abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> str:
        """Generate a raw text response from the LLM.

        Args:
            prompt: The user prompt.
            system_prompt: System-level instruction (prepended to conversation).
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.

        Returns:
            The generated text response.
        """
        ...

    def generate_structured(
        self,
        prompt: str,
        schema: TypeVar("T"),
        system_prompt: str = "",
        *,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> T:
        """Generate a structured (typed) response from the LLM.

        Subclasses can override this for native structured-output support,
        but the default implementation parses JSON from a text response.

        Args:
            prompt: The user prompt.
            schema: A Pydantic model class to parse the response into.
            system_prompt: System-level instruction.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.

        Returns:
            An instance of ``schema``.
        """
        # Build a system prompt that instructs the model to output valid JSON
        cls_name = getattr(schema, "__name__", "result")
        fields = _extract_schema_fields(schema)
        json_instruction = (
            f"\n\nRespond with valid JSON matching this schema: {cls_name}. "
            f"Fields: {', '.join(fields)}. Do not include any prose before or after the JSON."
        )

        response_text = self.generate(
            prompt + json_instruction,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return _parse_json_to_schema(response_text, schema)

    @abc.abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Args:
            text: Input text to embed.

        Returns:
            A list of floats representing the embedding.
        """
        ...

    @abc.abstractmethod
    def close(self) -> None:
        """Release any resources held by the provider."""
        ...


class EmbeddingProvider(abc.ABC):
    """Abstract base class for standalone embedding providers."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @abc.abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""
        ...

    @abc.abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        ...

    @abc.abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of the embedding vectors."""
        ...

    @abc.abstractmethod
    def close(self) -> None:
        """Release any resources held by the provider."""
        ...


def _extract_schema_fields(schema: type) -> list[str]:
    """Extract field names from a Pydantic model class or dataclass."""
    if hasattr(schema, "model_fields"):
        return list(schema.model_fields.keys())  # type: ignore[attr-defined]
    if hasattr(schema, "__dataclass_fields__"):
        return list(schema.__dataclass_fields__.keys())  # type: ignore[attr-defined]
    return []


def _parse_json_to_schema(text: str, schema: type[T]) -> T:
    """Parse a JSON string (or fenced JSON block) into a Pydantic model."""
    import json
    import re

    # Strip fenced code blocks
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        # Try to find the first { ... } block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

    data = json.loads(text)
    return schema.model_validate(data)
