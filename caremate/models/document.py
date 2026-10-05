"""Document and chunk models for the RAG pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """A single chunk of a medical document, tagged with patient isolation."""

    chunk_id: str = Field(..., description="Globally unique chunk identifier")
    document_id: str = Field(..., description="Source document identifier")
    patient_id: str = Field(..., description="Patient to whom this chunk belongs (enforces isolation)")
    section_label: str = Field(default="unknown", description="Detected medical section header")
    page_number: Optional[int] = Field(default=None, description="1-based page number in the source PDF")
    confidence: Optional[float] = Field(default=None, description="OCR / extraction confidence 0.0-1.0")
    content: str = Field(..., description="Text content of the chunk")
    token_count: int = Field(default=0, description="Approximate token count")
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {"extra": "ignore"}


class DocumentMetadata(BaseModel):
    """Metadata extracted from a source document."""

    document_id: str
    patient_id: str
    title: str
    document_type: str = Field(default="clinical_note")
    source: str = Field(default="manual")
    created_at: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)
    raw_text: Optional[str] = None

    model_config = {"extra": "ignore"}
