"""Tests for data retention, export, and GDPR deletion."""

from __future__ import annotations

import json

from caremate.db.models_comm import (
    AI_Generation,
    AuditLog,
    Citation,
    Conversation,
    Message,
)
from caremate.db.models_docs import MedicalDocument, DocumentChunk
from caremate.db.models_patients import Patient as OrmPatient
from caremate.security.retention import (
    apply_retention_policy,
    delete_patient_data,
    export_patient_data,
)
import pytest


@pytest.fixture
def patient_with_data(db):
    """Create a patient with associated documents and generations."""
    patient = OrmPatient(
        patient_id="del_patient_1",
        full_name="Delete Me",
        age=45,
        sex="female",
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    doc = MedicalDocument(
        document_id="doc_del_1",
        patient_id=patient.id,
        title="Record",
        document_type="clinical_note",
        source="test",
        raw_text="Some medical text",
    )
    db.add(doc)

    gen = AI_Generation(
        patient_id=patient.id,
        query="test query",
        response_text="test response",
        confidence=0.8,
    )
    db.add(gen)
    db.commit()

    return patient


class TestPatientDataDeletion:
    """Tests for the GDPR data-deletion workflow."""

    def test_delete_patient_removes_all_data(self, db, patient_with_data):
        """delete_patient_data removes documents, chunks, and generations."""
        pid = patient_with_data.id
        pid_str = patient_with_data.patient_id

        deleted = delete_patient_data(pid_str, db)

        assert db.get(OrmPatient, pid) is None
        remaining_docs = db.query(MedicalDocument).filter(
            MedicalDocument.patient_id == pid
        ).all()
        assert len(remaining_docs) == 0
        remaining_gens = db.query(AI_Generation).filter(
            AI_Generation.patient_id == pid
        ).all()
        assert len(remaining_gens) == 0
        assert deleted["patient"] == 1

    def test_delete_nonexistent_patient_is_noop(self, db):
        """delete_patient_data on a non-existent patient returns gracefully."""
        deleted = delete_patient_data("nonexistent_patient", db)
        assert deleted["patient"] == 0

    def test_delete_patient_logs_audit(self, db, patient_with_data):
        """The deletion should create an audit-log entry."""
        pid_str = patient_with_data.patient_id
        delete_patient_data(pid_str, db)

        entries = db.query(AuditLog).filter(
            AuditLog.action == "patient_data_deleted"
        ).all()
        assert len(entries) == 1
        assert entries[0].resource_id == pid_str


    def test_delete_endpoint_requires_admin(self, client, patient_token_a):
        """Non-admin cannot call the DELETE /patients/{id} endpoint."""
        r = client.delete("/patients/patient_A", headers=patient_token_a)
        assert r.status_code == 403

    def test_delete_endpoint_admin(self, client, db, admin_token):
        """Admin can delete a patient via the API."""
        patient = OrmPatient(patient_id="to_delete", full_name="Bye")
        db.add(patient)
        db.commit()

        r = client.delete("/patients/to_delete", headers=admin_token)
        assert r.status_code == 204

        remaining = db.query(OrmPatient).filter(
            OrmPatient.patient_id == "to_delete"
        ).all()
        assert len(remaining) == 0


class TestPatientDataExport:
    """Tests for GDPR data portability export."""

    def test_export_patient_data(self, db, patient_with_data):
        """export_patient_data returns all patient data as a dict."""
        pid_str = patient_with_data.patient_id
        data = export_patient_data(pid_str, db)

        assert data["patient"]["patient_id"] == pid_str
        assert data["patient"]["full_name"] == "Delete Me"
        assert isinstance(data["documents"], list)
        assert isinstance(data["ai_generations"], list)
        assert len(data["documents"]) == 1
        assert len(data["ai_generations"]) == 1

    def test_export_nonexistent_patient(self, db):
        """export_patient_data on a non-existent patient returns an error."""
        data = export_patient_data("no_such_patient", db)
        assert "error" in data


class TestRetentionPolicy:
    """Tests for the retention policy function."""

    def test_apply_retention_policy_deletes_old_logs(self, db):
        """apply_retention_policy deletes audit logs older than the cutoff."""
        from datetime import datetime, timedelta, timezone

        old_entry = AuditLog(
            action="old_action",
            resource_type="old",
            created_at=datetime.now(timezone.utc) - timedelta(days=100),
        )
        db.add(old_entry)

        recent_entry = AuditLog(
            action="recent_action",
            resource_type="recent",
            created_at=datetime.now(timezone.utc),
        )
        db.add(recent_entry)
        db.commit()

        result = apply_retention_policy(db, max_audit_age_days=90)
        assert result["audit_logs"] >= 1

        remaining_recent = db.query(AuditLog).filter(
            AuditLog.action == "recent_action"
        ).all()
        assert len(remaining_recent) == 1

        remaining_old = db.query(AuditLog).filter(
            AuditLog.action == "old_action"
        ).all()
        assert len(remaining_old) == 0
