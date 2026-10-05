"""Data retention and deletion workflow (GDPR right-to-be-forgotten).

Provides:
    * :func:`delete_patient_data` — hard-delete every trace of a patient.
    * :func:`export_patient_data`  — GDPR data-portability export.
    * :func:`apply_retention_policy` — delete expired audit logs / generations.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from caremate.db.models_clinical import LabResult, Medication
from caremate.db.models_comm import (
    AI_Generation,
    Citation,
    Conversation,
)
from caremate.db.models_core import User
from caremate.db.models_docs import DocumentChunk, MedicalDocument
from caremate.db.models_patients import (
    Doctor,
    Patient as OrmPatient,
    PatientDoctorRelationship,
)
from caremate.security.redaction import redact_phi
from caremate.utils.config import get_logger

logger = get_logger(__name__)

# Tables that reference the patient via patient_id (FK), in deletion order.
_PATIENT_TABLES: list[Any] = [
    Citation,
    AI_Generation,
    DocumentChunk,
    MedicalDocument,
    LabResult,
    Medication,
    Conversation,
    PatientDoctorRelationship,
]


def delete_patient_data(
    patient_id: str,
    db: Session,
    actor=None,
    ip_address: str = "",
    user_agent: str = "",
) -> dict[str, int]:
    """Hard-delete every record belonging to *patient_id*.

    The patient row itself is deleted last, but all related records are
    cleared first to avoid FK cascades being the sole protection.

    Returns a dict mapping table-name to number of rows deleted.
    """
    from caremate.db.repository_patients import PatientRepository

    repo = PatientRepository(db)
    orm_patient = repo.get_by_patient_id(patient_id)

    if orm_patient is None:
        logger.info("delete_patient_data: patient %s not found (no-op)", patient_id)
        return {"patient": 0}

    deleted: dict[str, int] = {}
    patient_orm_id = orm_patient.id

    # Delete from child tables first (before patient row)
    for table in _PATIENT_TABLES:
        try:
            count = db.execute(
                delete(table).where(table.patient_id == patient_orm_id)
            ).rowcount
            deleted[table.__tablename__] = count
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to delete from %s for patient %s: %s",
                           table.__tablename__, patient_id, exc)
            deleted[table.__tablename__] = -1

    # Remove the relationship rows
    try:
        count = db.execute(
            delete(PatientDoctorRelationship)
            .where(PatientDoctorRelationship.patient_id == patient_orm_id)
        ).rowcount
        deleted["patient_doctor_relationships"] = count
    except Exception:
        pass

    # Remove the patient row itself
    try:
        db.delete(orm_patient)
        deleted["patient"] = 1
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to delete patient row for %s: %s", patient_id, exc)

    # Also null out any User.patient_id that pointed here
    try:
        count = db.execute(
            delete(User).where(User.patient_id == patient_orm_id)
        ).rowcount
        deleted["user_patient_links"] = count
    except Exception:
        pass

    # Write an audit-log entry for this deletion
    try:
        from caremate.security.audit import AuditLogger
        audit = AuditLogger(db)
        audit.log_data_deletion(
                patient_id=patient_id,
                deleted_tables=list(deleted.keys()),
                user=actor,
                ip_address=ip_address,
                user_agent=user_agent,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to write audit log for deletion: %s", exc)

    db.commit()
    logger.info(
        "Deleted patient data for %s: %s (actor=%s, ip=%s)",
        patient_id, deleted,
        getattr(actor, "email", "unknown") if actor else "anonymous",
        redact_phi(ip_address),
    )
    return deleted


def export_patient_data(patient_id: str, db: Session) -> dict[str, Any]:
    """Return a JSON-serializable export of all data for *patient_id* (GDPR)."""
    from caremate.db.repository_patients import PatientRepository

    repo = PatientRepository(db)
    orm_patient = repo.get_by_patient_id(patient_id)

    if orm_patient is None:
        return {"patient_id": patient_id, "error": "not found"}

    data: dict[str, Any] = {
        "patient": {
            "patient_id": orm_patient.patient_id,
            "full_name": orm_patient.full_name,
            "age": orm_patient.age,
            "sex": orm_patient.sex,
            "medical_history": orm_patient.medical_history or [],
            "allergies": orm_patient.allergies or [],
            "dietary_restrictions": orm_patient.dietary_restrictions or [],
            "recent_weight": orm_patient.recent_weight,
            "height": orm_patient.height,
            "lab_results": orm_patient.lab_results or {},
            "notes": orm_patient.notes,
            "created_at": orm_patient.created_at.isoformat() if orm_patient.created_at else None,
        },
        "documents": [],
        "medications": [],
        "lab_results": [],
        "ai_generations": [],
    }

    # Documents + chunks
    docs = db.query(MedicalDocument).filter(
        MedicalDocument.patient_id == orm_patient.id
    ).all()
    for d in docs:
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == d.id
        ).all()
        data["documents"].append({
            "document_id": d.document_id,
            "title": d.title,
            "document_type": d.document_type,
            "source": d.source,
            "raw_text": d.raw_text,
            "tags": d.tags,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "section_label": c.section_label,
                    "page_number": c.page_number,
                    "content": c.content,
                    "token_count": c.token_count,
                }
                for c in chunks
            ],
        })

    # Medications
    for m in db.query(Medication).filter(Medication.patient_id == orm_patient.id).all():
        data["medications"].append({
            "name": m.name, "dosage": m.dosage,
            "frequency": m.frequency,
            "started_date": m.started_date.isoformat() if m.started_date else None,
            "notes": m.notes, "is_active": m.is_active,
        })

    # Lab results
    for l in db.query(LabResult).filter(LabResult.patient_id == orm_patient.id).all():
        data["lab_results"].append({
            "test_name": l.test_name, "value": l.value, "unit": l.unit,
            "reference_low": l.reference_low, "reference_high": l.reference_high,
            "flag": l.flag,
            "performed_at": l.performed_at.isoformat() if l.performed_at else None,
        })

    # AI Generations
    for g in db.query(AI_Generation).filter(AI_Generation.patient_id == orm_patient.id).all():
        data["ai_generations"].append({
            "id": g.id,
            "query": g.query,
            "response_text": g.response_text,
            "confidence": g.confidence,
            "status": g.status,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        })

    return data


def apply_retention_policy(db: Session, max_audit_age_days: int = 90) -> dict[str, int]:
    """Delete audit logs beyond the retention window.

    Args:
        db: SQLAlchemy session.
        max_audit_age_days: How long to keep ``AuditLog`` entries (default 90).
    """
    from caremate.db.models_comm import AuditLog

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_audit_age_days)
    result: dict[str, int] = {}

    try:
        count = db.execute(
            delete(AuditLog).where(AuditLog.created_at < cutoff)
        ).rowcount
        result["audit_logs"] = count
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to apply audit-log retention: %s", exc)
        result["audit_logs"] = -1

    db.commit()
    logger.info("Retention policy applied: %s", result)
    return result
