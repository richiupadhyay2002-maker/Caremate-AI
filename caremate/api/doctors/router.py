"""Doctor-facing endpoints: patient list, patient brief, AI draft review."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from caremate.api.deps import require_doctor
from caremate.db.models_comm import AI_Generation as OrmGen, Citation as OrmCitation
from caremate.db.models_docs import DocumentChunk as OrmChunk, MedicalDocument as OrmDoc
from caremate.db.models_patients import Patient as OrmPatient, Doctor as OrmDoctor, PatientDoctorRelationship
from caremate.db.repository_patients import PatientRepository
from caremate.db.session import get_db
from caremate.security.audit import get_audit_logger
from caremate.utils.config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/doctors", tags=["doctors"])


# ------------------------------------------------------------------
# Response schemas
# ------------------------------------------------------------------
class DoctorPatientSummary(BaseModel):
    """Compact patient summary for the doctor's patient list."""
    patient_id: str
    full_name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    medical_history: list = []
    allergies: list = []
    recent_weight: Optional[float] = None
    last_activity: Optional[str] = None

    model_config = {"from_attributes": True}


class GenerationCitation(BaseModel):
    chunk_id: str
    source_document: str
    section: str
    page_number: Optional[int] = None
    relevance_score: float
    text_snippet: str


class GenerationSummary(BaseModel):
    id: int
    patient_id: str
    patient_name: Optional[str] = None
    query: str
    response_text: str
    confidence: float
    safety_flags: list = []
    status: str = "pending"
    created_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_status: str = "pending"
    citation_count: int = 0
    full_response_json: dict = {}


class GenerationDetail(GenerationSummary):
    citations: list[GenerationCitation] = []
    doctor_notes: str = ""
    metadata: dict = {}


class ReviewRequest(BaseModel):
    status: str = Field(..., description="New status: approved, rejected, or edited")
    doctor_notes: Optional[str] = None
    edited_response: Optional[str] = None


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _get_doctor_orm(user, db: Session):
    """Resolve the ORM Doctor row for the authenticated user."""
    if user.doctor_id is None:
        return None
    return db.get(OrmDoctor, user.doctor_id)


def _list_patients(user, db: Session) -> list[OrmPatient]:
    """Return patients assigned to this doctor (via PatientDoctorRelationship).

    Admin users see all patients.
    """
    if user.role == "admin" or user.doctor_id is None:
        return db.query(OrmPatient).all()
    rows = (
        db.query(OrmPatient)
        .join(PatientDoctorRelationship, OrmPatient.id == PatientDoctorRelationship.patient_id)
        .where(PatientDoctorRelationship.doctor_id == user.doctor_id)
        .all()
    )
    return rows


def _resolve_patient(patient_id: str, db: Session) -> OrmPatient:
    """Look up an ORM Patient by its string patient_id."""
    repo = PatientRepository(db)
    orm_patient = repo.get_by_patient_id(patient_id)
    if orm_patient is None:
        orm_patient = repo.get_or_create(patient_id)
        db.flush()
    return orm_patient


def _fetch_citations(db: Session, gen_id: int) -> list[OrmCitation]:
    """Fetch all citations for a generation."""
    return db.query(OrmCitation).where(OrmCitation.ai_generation_id == gen_id).all()


def _citations_to_schema(citations: list[OrmCitation]) -> list[GenerationCitation]:
    return [
        GenerationCitation(
            chunk_id=c.chunk_ref or "",
            source_document=c.source_document,
            section=c.section,
            page_number=c.page_number,
            relevance_score=c.relevance_score or 0.0,
            text_snippet=c.text_snippet,
        )
        for c in citations
    ]


def _check_patient_access(user, patient_orm_id: int, patient_str_id: str, db: Session) -> None:
    """Raise 403 if the doctor does not have access to this patient."""
    if user.role == "admin" or user.doctor_id is None:
        return
    rel = (
        db.query(PatientDoctorRelationship)
        .where(
            PatientDoctorRelationship.doctor_id == user.doctor_id,
            PatientDoctorRelationship.patient_id == patient_orm_id,
        )
        .first()
    )
    if rel is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this patient",
        )


def _build_generation_detail(gen: OrmGen, orm_patient: OrmPatient, db: Session) -> GenerationDetail:
    citations = _fetch_citations(db, gen.id)
    return GenerationDetail(
        id=gen.id,
        patient_id=orm_patient.patient_id if orm_patient else "",
        patient_name=orm_patient.full_name if orm_patient else None,
        query=gen.query,
        response_text=gen.response_text,
        confidence=gen.confidence,
        safety_flags=gen.safety_flags or [],
        status=gen.status or "pending",
        created_at=gen.created_at.isoformat() if gen.created_at else None,
        reviewed_at=gen.reviewed_at.isoformat() if gen.reviewed_at else None,
        review_status=gen.status or "pending",
        citation_count=len(citations),
        full_response_json=gen.full_response_json or {},
        citations=_citations_to_schema(citations),
        doctor_notes=gen.doctor_notes or "",
                metadata=gen.metadata_json or {},
    )


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------
@router.get("/me", response_model=dict)
def read_doctor_profile(user=Depends(require_doctor)):
    """Return basic profile info for the authenticated doctor."""
    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "doctor_id": user.doctor_id,
    }


@router.get("/me/patients", response_model=list[DoctorPatientSummary])
def list_my_patients(
    user=Depends(require_doctor),
    db: Session = Depends(get_db),
):
    """List all patients assigned to the current doctor."""
    patients = _list_patients(user, db)
    results = []
    for p in patients:
        last_gen = (
            db.query(OrmGen)
            .where(OrmGen.patient_id == p.id)
            .order_by(OrmGen.created_at.desc())
            .first()
        )
        results.append(DoctorPatientSummary(
            patient_id=p.patient_id,
            full_name=p.full_name,
            age=p.age,
            sex=p.sex,
            medical_history=p.medical_history or [],
            allergies=p.allergies or [],
            recent_weight=p.recent_weight,
            last_activity=last_gen.created_at.isoformat() if last_gen else None,
        ))
    return results


@router.get("/me/patients/{patient_id}/context", response_model=dict)
def get_patient_brief(
    patient_id: str,
    user=Depends(require_doctor),
    db: Session = Depends(get_db),
):
    """Return the full patient context for the doctor's review."""
    patients = _list_patients(user, db)
    patient_ids = {p.patient_id for p in patients}
    if user.role != "admin" and patient_id not in patient_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this patient",
        )
    orm_patient = _resolve_patient(patient_id, db)
    repo = PatientRepository(db)
    ctx = repo.to_context(orm_patient)
    doc_count = db.query(OrmDoc).where(OrmDoc.patient_id == orm_patient.id).count()
    gen_count = db.query(OrmGen).where(OrmGen.patient_id == orm_patient.id).count()
    return {
        "patient_id": ctx.patient_id,
        "name": ctx.name,
        "age": ctx.age,
        "sex": ctx.sex,
        "medical_history": ctx.medical_history,
        "current_medications": [m.model_dump() for m in ctx.current_medications],
        "allergies": [a.model_dump() for a in ctx.allergies],
        "dietary_restrictions": ctx.dietary_restrictions,
        "recent_weight": ctx.recent_weight,
        "height": ctx.height,
        "lab_results": ctx.lab_results,
        "notes": ctx.notes,
                "document_count": doc_count,
        "generation_count": gen_count,
    }


@router.get("/me/patients/{patient_id}/generations", response_model=list[GenerationSummary])
def list_patient_generations(
    patient_id: str,
    user=Depends(require_doctor),
    db: Session = Depends(get_db),
):
    """List all AI generations for a patient, newest first."""
    patients = _list_patients(user, db)
    patient_ids = {p.patient_id for p in patients}
    if user.role != "admin" and patient_id not in patient_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this patient",
        )
    orm_patient = _resolve_patient(patient_id, db)
    gens = (
        db.query(OrmGen)
        .where(OrmGen.patient_id == orm_patient.id)
        .order_by(OrmGen.created_at.desc())
        .all()
    )
    results = []
    for g in gens:
        cite_count = db.query(OrmCitation).where(OrmCitation.ai_generation_id == g.id).count()
        results.append(GenerationSummary(
            id=g.id,
            patient_id=orm_patient.patient_id,
            patient_name=orm_patient.full_name,
            query=g.query,
            response_text=g.response_text,
            confidence=g.confidence,
            safety_flags=g.safety_flags or [],
            status=g.status or "pending",
            created_at=g.created_at.isoformat() if g.created_at else None,
            reviewed_at=g.reviewed_at.isoformat() if g.reviewed_at else None,
            citation_count=cite_count,
            full_response_json=g.full_response_json or {},
        ))
    return results


@router.get("/me/generations/{generation_id}", response_model=GenerationDetail)
def get_generation_detail(
    generation_id: int,
    user=Depends(require_doctor),
    db: Session = Depends(get_db),
):
    """Return a single AI generation with its citations for review."""
    gen = db.get(OrmGen, generation_id)
    if gen is None:
        raise HTTPException(status_code=404, detail="Generation not found")
    orm_patient = db.get(OrmPatient, gen.patient_id)
    if orm_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    _check_patient_access(user, gen.patient_id, orm_patient.patient_id, db)
    return _build_generation_detail(gen, orm_patient, db)


@router.patch("/me/generations/{generation_id}", response_model=GenerationDetail)
def review_generation(
    generation_id: int,
    req: ReviewRequest,
    user=Depends(require_doctor),
    db: Session = Depends(get_db),
):
    """Approve, reject, or edit an AI generation draft."""
    valid_statuses = {"approved", "rejected", "edited", "pending"}
    if req.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"status must be one of {valid_statuses}",
        )
    gen = db.get(OrmGen, generation_id)
    if gen is None:
        raise HTTPException(status_code=404, detail="Generation not found")
    orm_patient = db.get(OrmPatient, gen.patient_id)
    if orm_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    _check_patient_access(user, gen.patient_id, orm_patient.patient_id, db)

    gen.status = req.status
    if req.doctor_notes is not None:
        gen.doctor_notes = req.doctor_notes
    gen.reviewed_by = user.id
    gen.reviewed_at = datetime.now(timezone.utc)
    if req.status == "edited" and req.edited_response is not None:
        gen.response_text = req.edited_response
        if gen.full_response_json:
            gen.full_response_json = {
                **gen.full_response_json,
                "response": req.edited_response,
            }
    db.commit()
    db.refresh(gen)
    # Audit log: doctor reviewed an AI generation
    audit = get_audit_logger(db)
    audit.log_doctor_review(
        generation_id=gen.id,
        patient_id=orm_patient.patient_id,
        status=req.status,
        user=user,
    )
    return _build_generation_detail(gen, orm_patient, db)
