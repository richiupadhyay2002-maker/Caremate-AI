"""Structured output schemas for Caremate AI.

Every AI output is typed via these Pydantic models — never raw text.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SafetyFlag(str, Enum):
    """Categories of safety concern that can be raised by the guardrails."""

    PROMPT_INJECTION = "prompt_injection"
    RED_FLAG_SYMPTOM = "red_flag_symptom"
    DRUG_FOOD_INTERACTION = "drug_food_interaction"
    LOW_CONFIDENCE = "low_confidence"


class Citation(BaseModel):
    """A verifiable citation linking an AI statement to its source."""

    source_document: str = Field(..., description="ID or title of the source document")
    section: str = Field(default="unknown", description="Section label within the document")
    chunk_id: str = Field(..., description="Unique identifier of the source chunk")
    page_number: Optional[int] = Field(default=None, description="Page number of the cited source")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score of this citation")
    text_snippet: str = Field(..., description="Excerpt from the source that supports the claim")

    model_config = {"extra": "ignore"}


class SafetyCheckResult(BaseModel):
    """Result of running guardrails on a pipeline output."""

    is_safe: bool = Field(..., description="Overall safety verdict")
    flags: list[SafetyFlag] = Field(default_factory=list, description="Safety concerns detected")
    reasons: list[str] = Field(default_factory=list, description="Human-readable explanations")
    short_circuit: bool = Field(default=False, description="If True, pipeline should abort immediately")

    model_config = {"extra": "ignore"}


class StructuredAIResponse(BaseModel):
    """The canonical, fully-typed response from Caremate AI."""

    response: str = Field(..., description="The natural-language response shown to the user")
    citations: list[Citation] = Field(default_factory=list, description="Citations supporting the response")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0.0–1.0")
    safety_flags: list[SafetyFlag] = Field(default_factory=list, description="Any safety flags raised during generation")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (patient_id, pipeline_trace, timestamps, etc.)",
    )

    model_config = {"extra": "ignore"}
