"""RBAC + patient-ownership FastAPI dependencies.

These dependencies sit at the **API layer** — the outermost boundary — so
that patient isolation and role enforcement happen before any business
logic runs.  The same guarantees also exist inside the vector store
(``WHERE patient_id = ?``) and the agent layer, but defence-in-depth means
the API must reject cross-patient requests immediately.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from caremate.api.deps import get_current_user
from caremate.db.models_core import User
from caremate.db.models_patients import Patient as OrmPatient, PatientDoctorRelationship
from caremate.db.repository_patients import PatientRepository
from caremate.db.session import get_db


def get_client_info(request: Request) -> dict[str, str]:
    """Extract client IP and User-Agent from a FastAPI request."""
    ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "")
        or ""
    )
    user_agent = request.headers.get("user-agent", "") or ""
    return {"ip_address": ip, "user_agent": user_agent}


def require_own_patient(
    patient_path_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> tuple[OrmPatient, User, dict[str, str]]:
    """Resolve the patient for *patient_path_id* and enforce ownership.

    A non-admin **patient** user can only access their own record.
    An **admin** can access any patient.

    Returns ``(orm_patient, user, client_info)`` so callers have everything
    they need without a second DB hit.
    """
    repo = PatientRepository(db)
    orm_patient = repo.get_by_patient_id(patient_path_id)
    if orm_patient is None:
        orm_patient = repo.get_or_create(patient_path_id)
        db.flush()

    if user.role.value != "admin" and user.patient_id is not None:
        if user.patient_id != orm_patient.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own patient record",
            )

    info = get_client_info(request)
    return orm_patient, user, info


def require_doctor_patient(
    patient_path_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> tuple[OrmPatient, User, dict[str, str]]:
    """Resolve the patient for *patient_path_id* and enforce **doctor** access.

    A doctor can only access patients assigned to them via
    ``PatientDoctorRelationship``.  An admin can access any patient.

    Returns ``(orm_patient, user, client_info)``.
    """
    repo = PatientRepository(db)
    orm_patient = repo.get_by_patient_id(patient_path_id)
    if orm_patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    if user.role.value != "admin":
        rel = (
            db.query(PatientDoctorRelationship)
            .filter(
                PatientDoctorRelationship.doctor_id == user.doctor_id,
                PatientDoctorRelationship.patient_id == orm_patient.id,
            )
            .first()
        )
        if rel is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this patient",
            )

    info = get_client_info(request)
    return orm_patient, user, info


def require_self_or_admin(target_user_id: int, user: User = Depends(get_current_user)) -> None:
    """Ensure the authenticated user is acting on their own record (or is admin)."""
    if user.role.value != "admin" and user.id != target_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own user record",
        )
