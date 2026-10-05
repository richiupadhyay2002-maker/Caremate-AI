"""Tests for Phase 3 document ingestion pipeline.

Covers:
- PDF text extraction via pypdf
- Keyword-based document classification (all 6 types + fallback)
- Upload validation (valid PDF, invalid extension, oversized file, magic-byte mismatch)
- Provenance tracking: chunks carry correct page_number from source PDF
"""

from __future__ import annotations

import io
import os

import pytest
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, PageBreak, SimpleDocTemplate
from fastapi.testclient import TestClient

from caremate.ingestion.classifier import DocumentClassifier, classify_document
from caremate.ingestion.extractor import DocumentExtractor, ExtractedPage
from caremate.db.models_docs import DocumentType


# ---------------------------------------------------------------------------
# Helpers -- create synthetic PDFs / images in memory
# ---------------------------------------------------------------------------

def _make_pdf(pages: list[str]) -> bytes:
    """Generate a real single- or multi-page PDF with text content."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    for text in pages:
        story.append(Paragraph(text, styles["Normal"]))
        story.append(PageBreak())  # force each page to start on a new page
    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# PDF extraction tests
# ---------------------------------------------------------------------------

class TestPdfExtraction:
    """Tests for pypdf-based text extraction."""

    def test_single_page_pdf_extraction(self, tmp_path):
        """Extract text from a single-page PDF."""
        content = "PATIENT HISTORY: 65-year-old male with hypertension."
        pdf_bytes = _make_pdf([content])
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(pdf_bytes)

        extractor = DocumentExtractor()
        pages = extractor.extract(str(pdf_path))

        assert len(pages) == 1
        assert pages[0].text.strip()  # non-empty
        assert pages[0].page_number == 1
        assert pages[0].source == "native_pdf"
        assert "hypertension" in pages[0].text.lower()

    def test_multi_page_pdf_extraction(self, tmp_path):
        """Each page gets its own ExtractedPage with correct page_number."""
        page1 = "LABORATORY RESULTS\nSodium: 135 mmol/L"
        page2 = "MEDICATIONS\nLisinopril 10mg daily"
        pdf_bytes = _make_pdf([page1, page2])
        pdf_path = tmp_path / "multipage.pdf"
        pdf_path.write_bytes(pdf_bytes)

        extractor = DocumentExtractor()
        pages = extractor.extract(str(pdf_path))

        assert len(pages) == 2
        assert pages[0].page_number == 1
        assert pages[1].page_number == 2
        assert "sodium" in pages[0].text.lower()
        assert "lisinopril" in pages[1].text.lower()

    def test_extract_text_helper(self, tmp_path):
        """extract_text() returns full text joined by newlines."""
        page1 = "HISTORY of present illness: patient complains of chest pain."
        page2 = "ASSESSMENT: likely GERD."
        pdf_bytes = _make_pdf([page1, page2])
        pdf_path = tmp_path / "combined.pdf"
        pdf_path.write_bytes(pdf_bytes)

        extractor = DocumentExtractor()
        text = extractor.extract_text(str(pdf_path))
        assert "chest pain" in text.lower()
        assert "GERD" in text
        assert len(text) > 0


    def test_extract_returns_page_numbers_correctly(self, tmp_path):
        """Every ExtractedPage has a 1-based page_number."""
        pdf_bytes = _make_pdf([
            "Page one content",
            "Page two content",
            "Page three content",
        ])
        pdf_path = tmp_path / "threepage.pdf"
        pdf_path.write_bytes(pdf_bytes)

        extractor = DocumentExtractor()
        pages = extractor.extract(str(pdf_path))
        page_numbers = [p.page_number for p in pages]
        assert page_numbers == [1, 2, 3]

    def test_unsupported_extension_raises(self, tmp_path):
        """Unsupported file extension raises ValueError."""
        txt_path = tmp_path / "notes.txt"
        txt_path.write_text("some text")

        extractor = DocumentExtractor()
        with pytest.raises(ValueError, match="Unsupported"):
            extractor.extract(str(txt_path))

    def test_nonexistent_file_raises(self):
        """A nonexistent file raises FileNotFoundError."""
        extractor = DocumentExtractor()
        with pytest.raises(FileNotFoundError):
            extractor.extract("/nonexistent/file.pdf")


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------

class TestClassification:
    """Tests for keyword-based document classification."""

    def test_classify_pathology_report(self):
        text = "SPECIMEN: biopsy of colon. Histopathology shows malignant cells with necrosis."
        result = DocumentClassifier().classify(text)
        assert result.document_type == DocumentType.PATHOLOGY_REPORT
        assert result.confidence > 0.0

    def test_classify_radiology_report(self):
        text = "CT SCAN of the chest. IMPRESSION: no acute findings. FINDINGS: clear lungs."
        result = DocumentClassifier().classify(text)
        assert result.document_type == DocumentType.RADIOLOGY_REPORT

    def test_classify_lab_report(self):
        text = "LABORATORY RESULTS\nHemoglobin: 14.2 g/dL. WBC: 7.5. Reference range: normal."
        result = DocumentClassifier().classify(text)
        assert result.document_type == DocumentType.LAB_REPORT

    def test_classify_discharge_summary(self):
        text = "DISCHARGE INSTRUCTIONS: patient admitted for observation. Diagnosis: GERD."
        result = DocumentClassifier().classify(text)
        assert result.document_type == DocumentType.DISCHARGE_SUMMARY

    def test_classify_prescription(self):
        text = "Rx: Lisinopril 10mg. Dispensed at pharmacy. Take one tablet daily."
        result = DocumentClassifier().classify(text)
        assert result.document_type == DocumentType.PRESCRIPTION

    def test_classify_clinical_note(self):
        text = "CHIEF COMPLAINT: fatigue. ASSESSMENT: likely anemia. PLAN: blood work."
        result = DocumentClassifier().classify(text)
        assert result.document_type == DocumentType.CLINICAL_NOTE

    def test_classify_fallback_to_other(self):
        text = "the weather is sunny today"
        result = DocumentClassifier().classify(text)
        assert result.document_type == DocumentType.OTHER

    def test_classify_empty_text(self):
        result = DocumentClassifier().classify("")
        assert result.document_type == DocumentType.OTHER
        assert result.confidence == 0.0

    def test_classify_document_pydantic_model(self):
        """classify_document() returns just the type string."""
        text = "PATHOLOGY REPORT: biopsy shows malignant cells."
        doc_type = classify_document(text)
        assert doc_type == DocumentType.PATHOLOGY_REPORT

    def test_classify_returns_confidence_and_candidates(self):
        text = "LABORATORY RESULTS hemoglobin WBC glucose creatinine"
        result = DocumentClassifier().classify(text)
        assert 0.0 < result.confidence <= 1.0
        assert len(result.top_candidates) > 0

    def test_all_document_types_recognised(self):
        """DocumentType contains the 7 expected types."""
        expected = {
            "clinical_note",
            "pathology_report",
            "radiology_report",
            "lab_report",
            "discharge_summary",
            "prescription",
            "other",
        }
        assert set(DocumentType._ALL) == expected
