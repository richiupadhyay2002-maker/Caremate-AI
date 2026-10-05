
"""API tests for document upload endpoint."""

from __future__ import annotations

import io

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, PageBreak, SimpleDocTemplate

from caremate.db.models_docs import DocumentType


def _make_pdf(pages: list[str]) -> bytes:
    """Generate a real single- or multi-page PDF with text content."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    for text in pages:
        story.append(Paragraph(text, styles["Normal"]))
        story.append(PageBreak())
    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Upload endpoint tests
# ---------------------------------------------------------------------------

class TestUploadEndpoint:

    """Tests for POST /patients/{id}/documents/upload."""

    def test_upload_valid_pdf(self, client, patient_token, db, tmp_path):
        """A valid PDF is accepted, extracted, classified, and persisted."""
        pdf_bytes = _make_pdf([
            "LABORATORY RESULTS\n"
            "Hemoglobin: 14.2 g/dL\n"
            "WBC: 7.5 /mm3\n"
            "Reference range: 4.0-11.0"
        ])

        resp = client.post(
            "/patients/api_patient_1/documents/upload",
            files={"file": ("lab_report.pdf", pdf_bytes, "application/pdf")},
            data={"title": "Lab Results"},
            headers=patient_token,
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["document_id"].startswith("doc_")
        assert data["num_chunks"] > 0
        assert data["pages_extracted"] >= 1
        assert data["ocr_used"] is False
        assert data["document_type"] == DocumentType.LAB_REPORT
        assert 0.0 < data["classification_confidence"] <= 1.0

        from caremate.db.models_docs import DocumentChunk as OrmChunk
        from caremate.db.models_patients import Patient as OrmPatient
        patient = db.query(OrmPatient).filter(OrmPatient.patient_id == "api_patient_1").first()
        chunks = db.query(OrmChunk).filter(OrmChunk.patient_id == patient.id).all()
        assert len(chunks) == data["num_chunks"]
        assert all(c.page_number == 1 for c in chunks if c.page_number is not None)

    def test_upload_multi_page_pdf_provenance(self, client, patient_token, db, tmp_path):
        """Chunks from a 2-page PDF carry the correct page_number."""
        pdf_bytes = _make_pdf([
            "PATHOLOGY REPORT: biopsy shows malignant cells.",
            "DISCHARGE INSTRUCTIONS: patient recovered well.",
        ])

        resp = client.post(
            "/patients/api_patient_1/documents/upload",
            files={"file": ("multi_doc.pdf", pdf_bytes, "application/pdf")},
            headers=patient_token,
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["pages_extracted"] == 2

        from caremate.db.models_docs import DocumentChunk as OrmChunk
        from caremate.db.models_patients import Patient as OrmPatient
        patient = db.query(OrmPatient).filter(OrmPatient.patient_id == "api_patient_1").first()
        chunks = db.query(OrmChunk).filter(OrmChunk.patient_id == patient.id).all()
        page_numbers = sorted(set(c.page_number for c in chunks if c.page_number is not None))
        assert page_numbers == [1, 2]

    def test_upload_invalid_extension(self, client, patient_token):
        """A .txt file is rejected with 400."""
        resp = client.post(
            "/patients/api_patient_1/documents/upload",
            files={"file": ("notes.txt", b"some text", "text/plain")},
            headers=patient_token,
        )
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.json()["detail"]

    def test_upload_empty_file(self, client, patient_token):
        """An empty file is rejected with 400."""
        resp = client.post(
            "/patients/api_patient_1/documents/upload",
            files={"file": ("empty.pdf", b"", "application/pdf")},
            headers=patient_token,
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_upload_oversized_file(self, client, patient_token):
        """A file exceeding MAX_UPLOAD_BYTES is rejected with 413."""
        large_content = b"%PDF-1.4\n" + b"X" * (11 * 1024 * 1024)
        resp = client.post(
            "/patients/api_patient_1/documents/upload",
            files={"file": ("big.pdf", large_content, "application/pdf")},
            headers=patient_token,
        )
        assert resp.status_code == 413
        assert "too large" in resp.json()["detail"].lower()


    def test_upload_magic_byte_mismatch(self, client, patient_token):
        """A .pdf file with non-PDF content is rejected with 400."""
        resp = client.post(
            "/patients/api_patient_1/documents/upload",
            files={"file": ("fake.pdf", b"this is not a pdf", "application/pdf")},
            headers=patient_token,
        )
        assert resp.status_code == 400
        assert "content does not match" in resp.json()["detail"].lower()

    def test_upload_requires_auth(self, client):
        """An unauthenticated request is rejected with 401."""
        pdf_bytes = _make_pdf(["test content"])
        resp = client.post(
            "/patients/api_patient_1/documents/upload",
            files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 401

    def test_upload_patient_isolation(self, client, db, tmp_path):
        """A patient cannot upload to another patient's record."""
        from caremate.db.models_core import User
        from caremate.api.security import hash_password
        other_user = User(
            email="other_patient@e.com",
            hashed_password=hash_password("pass123"),
            full_name="Other Patient",
            role="patient",
            patient_id="other_patient_1",
        )
        db.add(other_user)
        db.commit()

        resp = client.post("/auth/token", json={
            "email": "other_patient@e.com", "password": "pass123"
        })
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {token}"}

        pdf_bytes = _make_pdf(["test content"])
        resp = client.post(
            "/patients/api_patient_1/documents/upload",
            files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
            headers=other_headers,
        )
        assert resp.status_code == 403

    def test_upload_with_document_type_override(self, client, patient_token, db):
        """User can override the auto-classified document type."""
        pdf_bytes = _make_pdf([
            "PATHOLOGY REPORT: biopsy shows malignant cells.\n"
            "specimen, histopathology, necrosis."
        ])

        resp = client.post(
            "/patients/api_patient_1/documents/upload",
            files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
            data={"document_type": "prescription"},
            headers=patient_token,
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["document_type"] == "prescription"


# ---------------------------------------------------------------------------
# Chunker provenance tests
# ---------------------------------------------------------------------------

class TestChunkerProvenance:
    """Tests that the chunker propagates page_number and confidence."""

    def test_chunker_propagates_page_number(self):
        """Chunks created from page-specific text carry the page_number."""
        from caremate.retrieval.chunker import SectionAwareChunker
        chunker = SectionAwareChunker()

        text = "PATIENT HISTORY\nPatient has diabetes type 2.\nMEDICATIONS\nMetformin 500mg."
        chunks = chunker.chunk_document(
            text=text, document_id="doc1", patient_id="pat1",
            page_number=3, confidence=0.92,
        )

        assert len(chunks) >= 1
        assert all(c.page_number == 3 for c in chunks)
        assert all(c.confidence == 0.92 for c in chunks)
        assert all(c.metadata.get("page_number") == 3 for c in chunks)

    def test_chunker_without_page_number(self):
        """Chunks without page_number have page_number=None."""
        from caremate.retrieval.chunker import SectionAwareChunker
        chunker = SectionAwareChunker()

        text = "PATIENT HISTORY\nPatient has diabetes."
        chunks = chunker.chunk_document(
            text=text, document_id="doc2", patient_id="pat2",
        )

        assert len(chunks) >= 1
        assert all(c.page_number is None for c in chunks)
        assert all(c.confidence is None for c in chunks)
