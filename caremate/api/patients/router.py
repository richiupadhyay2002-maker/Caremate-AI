"""Patient-facing endpoints: get context, add documents, list records."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from caremate.api.deps import get_current_user, require_admin, require_patient
from caremate.db.models_clinical import (
    Appointment, LabResult, Medication, Symptom, MedicalEvent,
)
from caremate.db.models_docs import MedicalDocument, DocumentChunk
from caremate.db.models_patients import Patient as OrmPatient
from caremate.db.repository_patients import PatientRepository
from caremate.db.session import get_db
from caremate.models.patient import PatientContext
from caremate.security.authorization import get_client_info
from caremate.security.retention import delete_patient_data
from caremate.utils.config import get_logger, get_settings

logger = get_logger(__name__)

router = APIRouter(prefix="/patients", tags=["patients"])


# ------------------------------------------------------------------
# Path-param helpers
# ------------------------------------------------------------------
def _get_own_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    user = Depends(require_patient),
) -> OrmPatient:
    """Return the patient row for *patient_path_id*, enforcing ownership.

    A patient user can only access their own record (matched via
    ``user.patient_id``); an admin can access any.  If the path-id doesn't
    match the authenticated user's patient, a 403 is raised.
    """
    repo = PatientRepository(db)
    orm_patient = repo.get_by_patient_id(patient_id)
    if orm_patient is None:
        orm_patient = repo.get_or_create(patient_id)
        db.flush()

    if user.role != "admin" and user.patient_id is not None:
        if user.patient_id != orm_patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You can only access your own patient record")
    return orm_patient


# ------------------------------------------------------------------
# Response schemas
# ------------------------------------------------------------------
class PatientResponse(BaseModel):
    patient_id: str
    full_name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    medical_history: list = []
    allergies: list = []
    dietary_restrictions: list = []
    recent_weight: Optional[float] = None
    height: Optional[float] = None
    lab_results: dict = {}
    notes: Optional[str] = None


class DocumentRef(BaseModel):
    document_id: str
    title: str
    document_type: str
    source: str
    created_at: Optional[str] = None


class ChunkRef(BaseModel):
    chunk_id: str
    document_id: str
    section: str
    content: str
    token_count: int


@router.get("/{patient_id}/context", response_model=PatientContext)
def get_patient_context(
    patient_id: str,
    orm_patient: OrmPatient = Depends(_get_own_patient),
    db: Session = Depends(get_db),
):
    """Return the full :class:`PatientContext` for the given patient."""
    repo = PatientRepository(db)
    return repo.to_context(orm_patient)


@router.get("/{patient_id}/documents", response_model=list[DocumentRef])
def list_documents(
    patient_id: str,
    orm_patient: OrmPatient = Depends(_get_own_patient),
    db: Session = Depends(get_db),
):
    """List all medical documents for the authenticated patient."""
    docs = db.query(MedicalDocument).filter(MedicalDocument.patient_id == orm_patient.id).all()
    return [
        DocumentRef(document_id=d.document_id, title=d.title, document_type=d.document_type,
                    source=d.source, created_at=d.created_at.isoformat() if d.created_at else None)
        for d in docs
    ]


@router.get("/{patient_id}/documents/{document_id}/chunks", response_model=list[ChunkRef])
def list_chunks(
    patient_id: str,
    document_id: str,
    orm_patient: OrmPatient = Depends(_get_own_patient),
    db: Session = Depends(get_db),
):
    """List all chunks for a specific document of the authenticated patient."""
    doc = db.query(MedicalDocument).filter(
        MedicalDocument.document_id == document_id,
        MedicalDocument.patient_id == orm_patient.id,
    ).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
    return [
        ChunkRef(chunk_id=c.chunk_id, document_id=c.document_id, section=c.section_label,
                 content=c.content, token_count=c.token_count)
        for c in chunks
    ]


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: str,
    orm_patient: OrmPatient = Depends(_get_own_patient),
):
    """Quick patient profile view (subset of the full context)."""
    return PatientResponse(
        patient_id=orm_patient.patient_id,
        full_name=orm_patient.full_name,
        age=orm_patient.age,
        sex=orm_patient.sex,
        medical_history=orm_patient.medical_history or [],
        allergies=orm_patient.allergies or [],
        dietary_restrictions=orm_patient.dietary_restrictions or [],
        recent_weight=orm_patient.recent_weight,
        height=orm_patient.height,
        lab_results=orm_patient.lab_results or {},
        notes=orm_patient.notes,
    )


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """GDPR right-to-be-forgotten: delete all data for a patient.

    Requires admin role.  Returns 204 on success.  Audit-logged.
    """
    repo = PatientRepository(db)
    orm_patient = repo.get_by_patient_id(patient_id)
    if orm_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Perform the deletion
    deleted = delete_patient_data(
        patient_id=patient_id,
        db=db,
        actor=current_user,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )

    logger.info(
        "Patient %s deleted via GDPR endpoint. Tables: %s",
        patient_id, deleted,
    )
    return None
