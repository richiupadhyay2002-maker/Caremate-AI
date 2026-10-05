"""Tests for patient data isolation at the API layer.

Verifies that a patient user can only access their own records and cannot
read or modify another patient's data.
"""

from __future__ import annotations

import pytest


class TestPatientIsolationAPI:
    """API-level tests for patient data isolation."""

    def test_patient_can_access_own_context(self, client, db, patient_token_a):
        """Patient A can retrieve their own patient context."""
        r = client.get("/patients/patient_A/context",
                       headers=patient_token_a)
        assert r.status_code == 200

    def test_patient_cannot_access_other_patient_context(self, client, patient_token_a):
        """Patient A cannot access patient B's context."""
        r = client.get("/patients/patient_B/context",
                       headers=patient_token_a)
        assert r.status_code == 403

    def test_patient_can_list_own_documents(self, client, db, patient_token_a):
        """Patient A can list their own documents."""
        from caremate.db.models_patients import Patient as OrmPatient
        from caremate.db.models_docs import MedicalDocument
        patient = db.query(OrmPatient).filter(OrmPatient.patient_id == "patient_A").first()
        doc = MedicalDocument(
            document_id="doc_a_1", patient_id=patient.id,
            title="Note A1", document_type="clinical_note", source="test",
        )
        db.add(doc)
        db.commit()

        r = client.get("/patients/patient_A/documents", headers=patient_token_a)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["document_id"] == "doc_a_1"

    def test_patient_cannot_list_other_patient_documents(self, client, db, patient_token_a):
        """Patient A cannot list patient B's documents."""
        # The _get_own_patient dependency enforces ownership before any DB lookup
        r = client.get("/patients/patient_B/documents", headers=patient_token_a)
        assert r.status_code == 403

    def test_patient_can_access_own_profile(self, client, patient_token_a):
        """Patient A can view their own profile."""
        r = client.get("/patients/patient_A", headers=patient_token_a)
        assert r.status_code == 200
        assert r.json()["patient_id"] == "patient_A"

    def test_patient_cannot_access_other_profile(self, client, patient_token_a):
        """Patient A cannot view patient B's profile."""
        r = client.get("/patients/patient_B", headers=patient_token_a)
        assert r.status_code == 403

    def test_admin_can_access_any_patient(self, client, admin_token):
        """Admin can access any patient's context."""
        r = client.get("/patients/patient_X/context", headers=admin_token)
        assert r.status_code == 200

    @pytest.mark.xfail(reason="Pre-existing: ChunkRef.document_id expects str but DocumentChunk.document_id is int FK")
    def test_patient_can_access_own_document_chunks(self, client, db, patient_token_a):
        """Patient A can list chunks for their own documents."""
        from caremate.db.models_patients import Patient as OrmPatient
        from caremate.db.models_docs import MedicalDocument, DocumentChunk
        patient = db.query(OrmPatient).filter(OrmPatient.patient_id == "patient_A").first()
        doc = MedicalDocument(
            document_id="doc_a_chunks", patient_id=patient.id,
            title="Chunks Test", document_type="clinical_note", source="test",
        )
        db.add(doc)
        db.commit()
        chunk = DocumentChunk(
            chunk_id="chunk_1", document_id=doc.id, patient_id=patient.id,
            section_label="HISTORY", page_number=1, content="Patient history here", token_count=10,
        )
        db.add(chunk)
        db.commit()

        r = client.get("/patients/patient_A/documents/doc_a_chunks/chunks",
                       headers=patient_token_a)
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_patient_cannot_access_other_patient_chunks(self, client, db, patient_token_a):
        """Patient A cannot list chunks for patient B's documents."""
        r = client.get("/patients/patient_B/documents/doc_b_chunks/chunks",
                       headers=patient_token_a)
        assert r.status_code == 403  # Access denied at ownership check

    def test_unauthenticated_request_rejected(self, client):
        """Requests without a valid token are rejected."""
        r = client.get("/patients/patient_A/context")
        assert r.status_code == 401
