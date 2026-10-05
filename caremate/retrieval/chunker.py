"""Section-aware medical document chunking."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Optional

from caremate.models.document import DocumentChunk

# Recognised medical section headers (regex, case-insensitive)
SECTION_PATTERNS: list[tuple[str, str]] = [
    (r"history\s+of\s+present\s+illness", "history_of_present_illness"),
    (r"chief\s+complaint", "chief_complaint"),
    (r"patient\s+history", "patient_history"),
    (r"past\s+medical\s+history", "past_medical_history"),
    (r"current\s+medications?", "medications"),
    (r"medications?", "medications"),
    (r"allergies?", "allergies"),
    (r"diagnos(es|is|is)", "diagnosis"),
    (r"assessment", "assessment"),
    (r"impression", "impression"),
    (r"treatment\s+plan", "treatment_plan"),
    (r"discharge\s+instructions?", "discharge_instructions"),
    (r"plan", "plan"),
    (r"dietary\s+instructions?", "dietary_instructions"),
    (r"nutrition", "nutrition"),
    (r"nutritional\s+assessment", "nutritional_assessment"),
    (r"\bdiet\b", "diet"),
    (r"lab(?:oratory)?\s+results?", "lab_results"),
    (r"vital\s+signs?", "vital_signs"),
    (r"social\s+history", "social_history"),
    (r"family\s+history", "family_history"),
    (r"review\s+of\s+systems?", "review_of_systems"),
]


@dataclass
class ChunkConfig:
    """Configuration for the chunker."""
    max_tokens: int = 500
    min_tokens: int = 50
    overlap_tokens: int = 50


class SectionAwareChunker:
    """Splits medical documents into section-aware chunks.

    Detects standard medical section headers and splits around them.
    Falls back to fixed-size chunking for unstructured text.
    Every chunk is tagged with a patient_id for isolation.
    """

    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()
        self._compiled = [
            (re.compile(pat, re.IGNORECASE | re.MULTILINE), label)
            for pat, label in SECTION_PATTERNS
        ]

    def chunk_document(
        self, text: str, document_id: str, patient_id: str,
        title: str = "unnamed_document", document_type: str = "clinical_note",
        page_number: Optional[int] = None,
        confidence: Optional[float] = None,
    ) -> list[DocumentChunk]:
        """Split a document into section-aware chunks.

        Args:
            text: The document text (may span multiple pages; pass page-specific
                  text when page-level provenance is desired).
            document_id: Stable identifier for the source document.
            patient_id: Patient ID for isolation (enforced on every chunk).
            title: Human-readable document title.
            document_type: One of the ``DocumentType`` constants.
            page_number: Optional 1-based page number from the source document,
                         propagated to every chunk for provenance tracking.
            confidence: Optional OCR/extraction confidence (0.0–1.0).
        """
        sections = self._extract_sections(text)
        chunks: list[DocumentChunk] = []
        if sections:
            for label, content in sections:
                chunks.extend(self._chunk_text(
                    content, document_id, patient_id, label, title, document_type,
                    page_number, confidence,
                ))
        else:
            chunks = self._chunk_text(
                text, document_id, patient_id, "unstructured", title, document_type,
                page_number, confidence,
            )
        return chunks

    def _extract_sections(self, text: str) -> list[tuple[str, str]]:
        """Detect section headers; return [(label, content), ...] or []."""
        headers: list[tuple[int, str, str]] = []
        for pattern, label in self._compiled:
            for m in pattern.finditer(text):
                headers.append((m.start(), m.group(), label))
        if not headers:
            return []
        headers.sort(key=lambda x: x[0])
        sections: list[tuple[str, str]] = []
        for i, (start, _hdr, label) in enumerate(headers):
            nl = text.find("\n", start)
            cstart = nl + 1 if nl != -1 else start + len(_hdr)
            cend = headers[i + 1][0] if i + 1 < len(headers) else len(text)
            content = text[cstart:cend].strip()
            if content:
                sections.append((label, content))
        return sections

    def _chunk_text(self, text: str, document_id: str, patient_id: str,
                    section_label: str, title: str, document_type: str,
                    page_number: Optional[int] = None,
                    confidence: Optional[float] = None) -> list[DocumentChunk]:
        """Split text into fixed-size chunks with overlap."""
        max_w = int(self.config.max_tokens * 0.75)
        overlap_w = int(self.config.overlap_tokens * 0.75)
        words = text.split()

        if len(words) <= max_w:
            return [self._make_chunk(text, document_id, patient_id, section_label, title, document_type,
                                      page_number, confidence)]

        chunks: list[DocumentChunk] = []
        start = 0
        while start < len(words):
            end = min(start + max_w, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append(self._make_chunk(chunk_text, document_id, patient_id, section_label, title, document_type,
                                           page_number, confidence))
            if end >= len(words):
                break
            start = end - overlap_w
        return chunks

    def _make_chunk(self, text: str, document_id: str, patient_id: str,
                    section_label: str, title: str, document_type: str,
                    page_number: Optional[int] = None,
                    confidence: Optional[float] = None) -> DocumentChunk:
        """Create a single DocumentChunk with a unique ID."""
        chunk_id = f"{document_id}_{uuid.uuid4().hex[:8]}"
        meta = {"title": title, "document_type": document_type}
        if page_number is not None:
            meta["page_number"] = page_number
        return DocumentChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            patient_id=patient_id,
            section_label=section_label,
            page_number=page_number,
            confidence=confidence,
            content=text,
            token_count=len(text.split()),
            metadata=meta,
        )

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token approximation: words / 0.75."""
        return max(1, int(len(text.split()) / 0.75))
