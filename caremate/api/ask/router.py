"""Ask/summarize endpoints: medical Q&A and nutrition Q&A, DB-backed."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from caremate.api.deps import get_current_user, require_patient
from caremate.security.audit import get_audit_logger
from caremate.security.authorization import get_client_info
from caremate.db.models_core import User
from caremate.db.repository_patients import PatientRepository
from caremate.db.session import get_db
from caremate.models.response import StructuredAIResponse
from caremate.orchestration.ask import AskMedicalRecordOrchestrator
from caremate.orchestration.nutrition import NutritionQAOrchestrator
from caremate.utils.config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/patients", tags=["patients"])


def _check_patient_access(patient_id: str, db: Session, user: User) -> None:
    """Enforce that the authenticated *user* may access *patient_id*.

    Admin users may access any patient.  Non-admin patient users may only
    access their own record.  Raises HTTPException(403) on violation.
    """
    if user.role.value != "admin":
        from caremate.db.repository_patients import PatientRepository
        repo = PatientRepository(db)
        orm_patient = repo.get_by_patient_id(patient_id)
        if orm_patient and user.patient_id is not None:
            if user.patient_id != orm_patient.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only access your own patient record",
                )


class AskRequest(BaseModel):
    query: str = Field(..., description="The patient's medical question")
    raw_documents: list[str] = Field(default_factory=list,
                                      description="Optional additional documents to include")


def _get_orchestrator(
    patient_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_patient),
) -> AskMedicalRecordOrchestrator:
    """Build (or reuse) an orchestrator with ownership enforcement.

    A non-admin patient can only ask about their own patient_id.
    """
    repo = PatientRepository(db)
    orm_patient = repo.get_by_patient_id(patient_id)
    if orm_patient is None:
        orm_patient = repo.get_or_create(patient_id)
        db.flush()

    if user.role != "admin" and user.patient_id is not None:
        if user.patient_id != orm_patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You can only ask questions about your own patient record")

    orchestrator = AskMedicalRecordOrchestrator(db_session=db)
    return orchestrator


@router.post("/{patient_id}/ask", response_model=StructuredAIResponse)
def ask_patient(
    patient_id: str,
    req: AskRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    orchestrator: AskMedicalRecordOrchestrator = Depends(_get_orchestrator),
):
    """Run the medical-record Q&A pipeline for a patient.

    The orchestration loads the patient context from Postgres, runs the
    six-agent pipeline with the :class:`PgVectorStore` as the retriever,
    and persists the AI_generation + citations to the database.
    """
    # Enforce patient ownership at the API layer
    _check_patient_access(patient_id, db, current_user)

    response = orchestrator.answer(
        query=req.query,
        patient_id=patient_id,
        raw_documents=req.raw_documents,
    )

    # Audit-log the AI generation
    client_info = get_client_info(request) if request else {"ip_address": "", "user_agent": ""}
    audit = get_audit_logger(db)
    audit.log_ai_generation(
        patient_id=patient_id,
        query=req.query,
        response_text=response.answer if hasattr(response, "answer") else str(response),
        confidence=getattr(response, "confidence", 0.0),
        user=current_user,
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
    )

    return response


@router.post("/{patient_id}/ask/nutrition", response_model=StructuredAIResponse)
def ask_nutrition(
    patient_id: str,
    req: AskRequest,
    db: Session = Depends(get_db),
    user=Depends(require_patient),
):
    """Run the nutrition Q&A pipeline for a patient (DB-backed)."""
    repo = PatientRepository(db)
    orm_patient = repo.get_by_patient_id(patient_id)
    if orm_patient is None:
        orm_patient = repo.get_or_create(patient_id)
        db.flush()

    if user.role != "admin" and user.patient_id is not None:
        if user.patient_id != orm_patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You can only ask about your own nutrition")

    orchestrator = NutritionQAOrchestrator(db_session=db)
    response = orchestrator.answer(
        query=req.query,
        patient_id=patient_id,
        raw_documents=req.raw_documents,
    )
    return response
