"""Response agent — assembles the final typed response.

Sixth and final agent: Document → Retrieval → Summarization →
Citation → Safety → Response.

Produces a StructuredAIResponse with response text, citations,
confidence, and safety flags.
"""

from __future__ import annotations

from caremate.agents.base import BaseAgent, PipelineData
from caremate.models.response import (
    StructuredAIResponse,
    SafetyFlag,
    Citation,
)
from caremate.utils.config import get_logger

logger = get_logger(__name__)


class ResponseAgent(BaseAgent):
    """Assembles the final StructuredAIResponse from pipeline data."""

    @property
    def name(self) -> str:
        return "ResponseAgent"

    def process(self, data: PipelineData) -> PipelineData:
        """Build the final structured response."""
        data.trace(self.name, "Assembling final response")

        # Convert verified citations to Citation objects if needed
        citations = self._to_citations(data.verified_citations)

        # Determine safety flags
        safety_flags: list[SafetyFlag] = []
        if data.safety_result:
            safety_flags = data.safety_result.flags

        # Build response text
        response_text = self._build_response_text(data)

        # Build metadata
        patient_id = data.patient.patient_id if data.patient else "unknown"
        metadata = {
            "patient_id": patient_id,
            "pipeline_trace": data.pipeline_trace,
            "sources": list(set(c.source_document for c in citations)),
            "agent": data.patient.name if data.patient else "unknown_patient",
        }

        # If safety short-circuited, override with a safe response
        if data.safety_result and data.safety_result.short_circuit:
            response_text = self._safe_response(
                data.safety_result.reasons, data.query
            )
            confidence = 0.9  # We're confident the safety block is correct
        else:
            confidence = data.confidence

        structured = StructuredAIResponse(
            response=response_text,
            citations=citations,
            confidence=round(confidence, 2),
            safety_flags=safety_flags,
            metadata=metadata,
        )

        data.response = structured
        data.trace(self.name, "Final response assembled")
        logger.info("ResponseAgent: response ready (confidence: %.2f)", confidence)
        return data

    def _to_citations(self, verified: list) -> list[Citation]:
        """Convert verified citation data to Citation objects."""
        citations: list[Citation] = []
        for item in verified:
            if isinstance(item, Citation):
                citations.append(item)
            elif isinstance(item, dict):
                citations.append(Citation(**item))
            elif hasattr(item, "__dict__"):
                citations.append(Citation(**item.__dict__))
        return citations

    def _build_response_text(self, data: PipelineData) -> str:
        """Build the natural-language response from summary and reasoning."""
        summary = data.summary or "No information available."
        if data.reasoning:
            return summary
        return summary

    def _safe_response(self, reasons: list[str], query: str) -> str:
        """Generate a safe response when guardrails triggered."""
        base = (
            "I'm sorry, but I cannot provide an answer to that query. "
        )
        if reasons:
            base += f"Reason: {'; '.join(reasons)}. "
        base += "For your safety, please consult with a qualified healthcare professional."
        return base
