"""Mock LLM and embedding providers for offline testing and demos."""

from __future__ import annotations
import hashlib
import json
import random
import re
from typing import Any, Optional
from caremate.providers.base import LLMProvider, EmbeddingProvider


class MockLLMProvider(LLMProvider):
    """A deterministic mock LLM provider for zero-key offline operation."""

    def __init__(self, temperature: float = 0.0, seed: int = 42):
        self._rng = random.Random(seed)
        self._temperature = temperature

    @property
    def name(self) -> str:
        return "mock"

    def generate(self, prompt: str, system_prompt: str = "", *,
                 temperature: float = 0.7, max_tokens: int = 1024,
                 **kwargs: Any) -> str:
        pl = prompt.lower()
        inj = self._check_red_flags(pl)
        if inj:
            return inj
        nut = self._handle_nutrition(pl)
        if nut:
            return nut
        if "citation" in pl or "source" in pl or "reference" in pl:
            return json.dumps({"response": "Based on clinical guidelines.",
                               "has_citations": True,
                               "sources": ["Patient record", "Nutrition guidelines"]})
        if "structured" in pl:
            return json.dumps({"response": "Mock structured response.",
                               "citations": [], "confidence": 0.95,
                               "safety_flags": [], "metadata": {}})
        wc = len(prompt.split())
        return (f"I understand your question. Based on the medical information "
                f"provided, consult your healthcare team for personalized advice. "
                f"This simulation used {wc} prompt tokens.")

    def embed(self, text: str) -> list[float]:
        return _deterministic_embedding(text, dim=128)

    def close(self) -> None:
        pass

    def _check_red_flags(self, pl: str) -> Optional[str]:
        for phrase in ["ignore previous", "disregard", "system prompt",
                        "override", "forget your instructions", "pretend you are",
                        "ignore the above", "administer medication", "dosage change",
                        "stop taking", "immediate treatment"]:
            if phrase in pl:
                return ("I cannot comply with that request. For your safety, "
                        "please consult a qualified healthcare professional.")
        return None

    def _handle_nutrition(self, pl: str) -> Optional[str]:
        triggers = ["nutrition", "diet", "food", "eat", "malnutrition",
                     "protein", "calcium", "sodium", "salt"]
        if not any(w in pl for w in triggers):
            return None
        if "protein" in pl:
            return ("Protein is essential for healing. Aim for 1.2-1.5g per kg. "
                    "Sources: lean meats, fish, eggs, dairy, legumes, nuts, seeds. "
                    "Protein shakes if swallowing is difficult.")
        if "calcium" in pl:
            return ("Calcium for bones. Dairy, leafy greens, fortified milks. "
                    "Avoid supplements within 2 hours of antibiotics. Aim 1000-1200mg.")
        if "malnutrition" in pl:
            return ("Malnutrition delays healing and weakens immunity. "
                    "Signs: weight loss, poor appetite, fatigue. "
                    "See a healthcare provider immediately.")
        if "sodium" in pl or "salt" in pl:
            return ("Limit sodium to under 2,300 mg per day. "
                    "Choose fresh foods, read labels, use herbs not salt.")
        return ("Nutrition aids recovery. Balanced diet with protein, calcium, "
                "fruits, and vegetables. Stay hydrated. Consult a dietitian.")


class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dim: int = 384, seed: int = 42):
        self._dim = dim
        self._rng = random.Random(seed)

    @property
    def name(self) -> str:
        return "mock"

    def embed(self, text: str) -> list[float]:
        return _deterministic_embedding(text, dim=self._dim)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [_deterministic_embedding(t, dim=self._dim) for t in texts]

    def dimension(self) -> int:
        return self._dim

    def close(self) -> None:
        pass


def _deterministic_embedding(text: str, dim: int = 128) -> list[float]:
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    seed = int(text_hash[:8], 16)
    rng = random.Random(seed)
    values = [rng.gauss(0, 1) for _ in range(dim)]
    words = re.findall(r"\\b[a-z]+\\b", text.lower())
    for w in words:
        wh = int(hashlib.sha256(w.encode("utf-8")).hexdigest()[:4], 16)
        values[wh % dim] += 1.0
    lf = min(len(text) / 1000.0, 1.0)
    values = [v + lf * 0.1 for v in values]
    norm = sum(v * v for v in values) ** 0.5
    if norm > 0:
        values = [v / norm for v in values]
    return [round(v, 6) for v in values]
