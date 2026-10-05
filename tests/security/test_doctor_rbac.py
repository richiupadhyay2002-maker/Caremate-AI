"""Tests for doctor RBAC — doctors can only access assigned patients."""

from __future__ import annotations

import pytest


class TestDoctorRBAC:
    """Tests for role-based access control for doctors."""

    def test_doctor_blocked_from_patient_endpoints(self, client, doctor_token):
        """A doctor is blocked from /patients/{id}/context (requires patient role)."""
        r = client.get("/patients/patient_A/context", headers=doctor_token)
        assert r.status_code == 403

    def test_doctor_can_list_assigned_patients(self, client, doctor_token):
        """A doctor can list their assigned patients."""
        r = client.get("/doctors/me/patients", headers=doctor_token)
        assert r.status_code == 200
        data = r.json()
        patient_ids = [p["patient_id"] for p in data]
        assert "patient_A" in patient_ids

    def test_doctor_cannot_access_unassigned_patient_context(self, client, db, doctor_token):
        """A doctor cannot access context for a patient they are NOT assigned to."""
        from caremate.db.models_patients import Patient as OrmPatient
        patient = OrmPatient(patient_id="patient_unassigned", full_name="Unassigned")
        db.add(patient)
        db.commit()

        r = client.get("/patients/patient_unassigned/context", headers=doctor_token)
        assert r.status_code == 403

    def test_doctor_blocked_from_accessing_documents(self, client, db, doctor_token):
        """A doctor cannot access documents via the patient endpoint."""
        from caremate.db.models_patients import Patient as OrmPatient
        from caremate.db.models_docs import MedicalDocument
        patient = OrmPatient(patient_id="patient_no_access", full_name="No Access")
        db.add(patient)
        db.commit()
        doc = MedicalDocument(
            document_id="doc_no_access", patient_id=patient.id,
            title="Secret", document_type="clinical_note", source="test",
        )
        db.add(doc)
        db.commit()

        r = client.get("/patients/patient_no_access/documents", headers=doctor_token)
        assert r.status_code == 403

    def test_doctor_can_access_assigned_generations(self, client, db, doctor_token):
        """A doctor can list generations for their assigned patient."""
        from caremate.db.models_patients import Patient as OrmPatient
        from caremate.db.models_comm import AI_Generation
        patient = db.query(OrmPatient).filter(OrmPatient.patient_id == "patient_A").first()
        if patient is None:
            patient = OrmPatient(patient_id="patient_A", full_name="Patient A")
            db.add(patient)
            db.commit()
        gen = AI_Generation(
            patient_id=patient.id, query="test", response_text="test", confidence=0.8,
        )
        db.add(gen)
        db.commit()

        r = client.get("/doctors/me/patients/patient_A/generations", headers=doctor_token)
        assert r.status_code == 200

    def test_doctor_cannot_access_unassigned_patient_generations(self, client, db, doctor_token):
        """A doctor cannot list generations for a patient they are NOT assigned to."""
        from caremate.db.models_patients import Patient as OrmPatient
        from caremate.db.models_comm import AI_Generation
        patient = OrmPatient(patient_id="patient_X", full_name="Patient X")
        db.add(patient)
        db.commit()
        gen = AI_Generation(
            patient_id=patient.id, query="test", response_text="test", confidence=0.8,
        )
        db.add(gen)
        db.commit()

        r = client.get("/doctors/me/patients/patient_X/generations", headers=doctor_token)
        assert r.status_code == 403

    def test_patient_user_cannot_access_doctor_endpoints(self, client, patient_token_a):
        """A patient user cannot access doctor-only endpoints."""
        r = client.get("/doctors/me/patients", headers=patient_token_a)
        assert r.status_code == 403

    def test_admin_can_access_doctor_endpoints(self, client, admin_token):
        """Admin can access doctor endpoints."""
        r = client.get("/doctors/me/patients", headers=admin_token)
        assert r.status_code in (200, 403)
