"""Base agent class for the six-agent deterministic pipeline.

Each agent processes a PipelineData object and returns an updated
PipelineData, forming a chain: Document → Retrieval → Summarization →
Citation → Safety → Response.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Optional

from caremate.models.response import StructuredAIResponse, SafetyCheckResult, SafetyFlag
from caremate.models.patient import PatientContext
from caremate.models.document import DocumentChunk


class BaseAgent(abc.ABC):
    """Abstract base class for pipeline agents.

    Each agent processes a PipelineData object in sequence and returns
    an updated PipelineData.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Agent identifier for tracing."""
        ...

    @abc.abstractmethod
    def process(self, data: "PipelineData") -> "PipelineData":
        """Process the pipeline data and return updated data."""
        ...


@dataclass
class PipelineData:
    """Shared data object passed between agents in the pipeline."""

    # Input
    query: str = ""
    patient: Optional[PatientContext] = None

    # Document processing
    raw_documents: list[str] = field(default_factory=list)
    chunks: list[DocumentChunk] = field(default_factory=list)
    document_metadata: dict[str, Any] = field(default_factory=dict)

    # Retrieval
    retrieved_chunks: list[tuple[DocumentChunk, float]] = field(default_factory=list)

    # Summarization
    summary: str = ""
    reasoning: str = ""
    confidence: float = 0.5

    # Citations
    verified_citations: list[Any] = field(default_factory=list)

    # Safety
    safety_result: Optional[SafetyCheckResult] = None

    # Final output
    response: Optional[StructuredAIResponse] = None

    # Pipeline tracing
    pipeline_trace: list[str] = field(default_factory=list)

    def trace(self, agent_name: str, message: str) -> None:
        """Record a trace entry for debugging/auditability."""
        self.pipeline_trace.append(f"[{agent_name}] {message}")
