"""Tests for section-aware medical document chunking.

Verifies that the SectionAwareChunker correctly identifies medical
section headers and produces properly tagged chunks.
"""

import pytest

from caremate.retrieval.chunker import SectionAwareChunker, ChunkConfig
from caremate.models.document import DocumentChunk


SAMPLE_DOC = """PATIENT HISTORY
The patient is a 65-year-old male with a history of heart failure
and hypertension.

MEDICATIONS
- Lisinopril 10mg daily
- Warfarin 5mg daily

DIETARY INSTRUCTIONS
- Limit sodium to less than 2000 mg per day
- Avoid cranberry juice
- Increase protein intake

LABORATORY RESULTS
- Sodium: 135 mmol/L
- Albumin: 3.4 g/dL
"""


def test_section_aware_chunking_detects_sections(chunker):
    """The chunker correctly identifies medical section headers."""
    chunks = chunker.chunk_document(SAMPLE_DOC, document_id="doc1", patient_id="pat1")
    assert len(chunks) > 1
    sections = {c.section_label for c in chunks}
    assert "patient_history" in sections
    assert "medications" in sections
    assert "dietary_instructions" in sections
    assert "lab_results" in sections


def test_unstructured_document_chunking(chunker):
    """Documents without section headers are still chunked."""
    text = "This is a long unstructured medical note. " * 50
    chunks = chunker.chunk_document(text, document_id="doc2", patient_id="pat2",
                                     title="unstructured_note")
    assert len(chunks) >= 1
    # All chunks should be tagged with section_label "unstructured"
    assert all(c.section_label == "unstructured" for c in chunks)


def test_chunks_tagged_with_patient_id(chunker):
    """Every chunk must carry the patient_id for isolation."""
    chunks = chunker.chunk_document(SAMPLE_DOC, document_id="doc3", patient_id="patient_XYZ")
    assert len(chunks) > 0
    assert all(c.patient_id == "patient_XYZ" for c in chunks)
    assert all(c.chunk_id.startswith("doc3") for c in chunks)
    assert all(len(c.content) > 0 for c in chunks)
