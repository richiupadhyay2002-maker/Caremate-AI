"""Summarization agent — generates a summary from retrieved chunks.

Third agent in the pipeline: Document → Retrieval → Summarization → …

Uses the LLM provider to produce a context-grounded summary and
reasoning chain from the retrieved document chunks.
"""

from __future__ import annotations

from typing import Optional

from caremate.agents.base import BaseAgent, PipelineData
from caremate.providers.base import LLMProvider
from caremate.utils.config import get_logger

logger = get_logger(__name__)


class SummarizationAgent(BaseAgent):
    """Summarizes retrieved chunks and generates reasoning.

    Constructs a prompt from the query and retrieved chunks, then
    calls the LLM to produce a summary and confidence score.
    """

    SYSTEM_PROMPT = (
        "You are Caremate, a safety-checked healthcare AI assistant. "
        "Summarize the provided medical information relevant to the patient's query. "
        "Base your response ONLY on the provided context. "
        "Provide a confidence score (0.0-1.0) for your summary. "
        "Do not provide medical advice beyond what is in the context."
    )

    def __init__(self, llm: LLMProvider):
        self._llm = llm

    @property
    def name(self) -> str:
        return "SummarizationAgent"

    def process(self, data: PipelineData) -> PipelineData:
        """Summarize retrieved chunks and generate reasoning."""
        if not data.retrieved_chunks:
            data.trace(self.name, "No chunks retrieved — generating minimal response")
            data.summary = "No relevant medical information was found in the patient's records."
            data.reasoning = "No retrieval results available."
            data.confidence = 0.1
            return data

        # Build context from retrieved chunks
        context_parts = []
        sources = set()
        for chunk, score in data.retrieved_chunks:
            context_parts.append(f"[Source: {chunk.section_label}] {chunk.content}")
            sources.add(chunk.document_id)

        context = "\n\n".join(context_parts)

        prompt = (
            f"Patient Query: {data.query}\n\n"
            f"Relevant Medical Context:\n{context}\n\n"
            f"Provide a concise summary and your confidence in this summary. "
            f"Format as: SUMMARY: <text> | REASONING: <text> | CONFIDENCE: <float>"
        )

        try:
            raw_response = self._llm.generate(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=512,
            )
            summary, reasoning, confidence = self._parse_response(raw_response)
        except Exception as exc:
            data.trace(self.name, f"LLM error: {exc}")
            summary = "Unable to generate summary due to an error."
            reasoning = f"Error: {exc}"
            confidence = 0.0

        data.summary = summary
        data.reasoning = reasoning
        data.confidence = confidence
        data.trace(self.name, f"Summary generated (confidence: {confidence:.2f})")
        logger.info("SummarizationAgent: confidence=%.2f", confidence)
        return data

    @staticmethod
    def _parse_response(raw: str) -> tuple[str, str, float]:
        """Parse the LLM's structured summary response."""
        summary = raw
        reasoning = ""
        confidence = 0.5

        # Try to parse the structured format
        if "SUMMARY:" in raw:
            parts = raw.split("SUMMARY:")[1]
            if "REASONING:" in parts:
                summary = parts.split("REASONING:")[0].strip()
                parts = parts.split("REASONING:")[1]
                if "CONFIDENCE:" in parts:
                    reasoning = parts.split("CONFIDENCE:")[0].strip()
                    try:
                        confidence = float(parts.split("CONFIDENCE:")[1].strip())
                    except (ValueError, IndexError):
                        confidence = 0.5
                else:
                    reasoning = parts.strip()
            else:
                summary = parts.split("REASONING:")[0].strip() if "REASONING:" in parts else parts.strip()
        else:
            # Plain text response
            summary = raw.strip()

        return summary, reasoning, max(0.0, min(1.0, confidence))
