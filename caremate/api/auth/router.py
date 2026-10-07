"""Authentication router - login (/token), register, and user management."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from caremate.api.security import create_access_token, hash_password, verify_password
from caremate.db.models_core import User, UserRole, Organization as OrmOrg
from caremate.db.models_patients import Patient as OrmPatient, Doctor as OrmDoctor
from caremate.db.repository_patients import PatientRepository
from caremate.db.session import get_db
from caremate.security.audit import get_audit_logger
from caremate.utils.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


# ------------------------------------------------------------------
# Request / response models
# ------------------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""
    role: UserRole = UserRole.PATIENT
    patient_id: Optional[str] = None
    doctor_id: Optional[str] = None
    organization_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str


class TokenInfo(BaseModel):
    sub: str
    role: str
    email: str = ""
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None


# ------------------------------------------------------------------
# Auth dependency
# ------------------------------------------------------------------
def _resolve_current(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret,
                             algorithms=[settings.jwt_algorithm])
    except (JWTError, Exception):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid token",
                            headers={"WWW-Authenticate": "Bearer"})
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except (JWTError, Exception):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@router.post("/token", response_model=TokenResponse)
def login(form: LoginRequest, db: Session = Depends(get_db)):
    """Exchange credentials for a JWT bearer token."""
    user = db.query(User).filter(User.email == form.email).first()
    if (user is None or not user.is_active
            or not verify_password(form.password, user.hashed_password)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect email or password",
                            headers={"WWW-Authenticate": "Bearer"})
    token = create_access_token(user, expires_delta=timedelta(minutes=settings.jwt_expire_minutes))
    # Audit log: login event
    audit = get_audit_logger(db)
    audit.log(
        action="login",
        resource_type="user",
        resource_id=str(user.id),
        user=user,
        request_body={"email": "[redacted]"},
    )
    return TokenResponse(access_token=token)


@router.post("/register", response_model=UserResponse)
def register(
    req: RegisterRequest,
    db: Session = Depends(get_db),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    """Register a new user.

    - Patients can self-register (no auth required).
    - Registering as a doctor or admin requires an authenticated admin token.
    """
    if req.role in (UserRole.DOCTOR, UserRole.ADMIN):
        if auth is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Admin authentication required",
                                headers={"WWW-Authenticate": "Bearer"})
        payload = _decode_token(auth.credentials)
        caller = db.get(User, int(payload["sub"]))
        if caller is None or caller.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Only admins can register doctors/admins")

    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=req.email, hashed_password=hash_password(req.password),
                full_name=req.full_name, role=req.role)

    org = None
    if req.organization_name:
        org = db.query(OrmOrg).filter(OrmOrg.name == req.organization_name).first()
        if org is None:
            org = OrmOrg(name=req.organization_name)
            db.add(org)
            db.flush()
    if org:
        user.organization_id = org.id

    if req.role == UserRole.PATIENT:
        patient_repo = PatientRepository(db)
        if req.patient_id:
            patient = patient_repo.get_or_create(req.patient_id)
        else:
            # Self-signup: give every new patient user their own private
            # patient record so uploads and analyses are scoped to it.
            import uuid as _uuid
            patient = patient_repo.get_or_create(
                f"P{user.email.split('@')[0]}_{_uuid.uuid4().hex[:6]}".upper()
            )
        user.patient_id = patient.id
    elif req.role == UserRole.DOCTOR and req.doctor_id:
        doc = db.query(OrmDoctor).filter(OrmDoctor.doctor_id == req.doctor_id).first()
        if doc is None:
            doc = OrmDoctor(doctor_id=req.doctor_id, full_name=req.full_name)
            if org:
                doc.organization_id = org.id
            db.add(doc)
            db.flush()
        user.doctor_id = doc.id

    db.add(user)
    db.commit()
    db.refresh(user)
    # Audit log: registration event
    audit = get_audit_logger(db)
    audit.log(
        action="register",
        resource_type="user",
        resource_id=str(user.id),
        user=user,
        request_body={"role": user.role.value},
    )
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name, role=user.role.value)


@router.get("/me", response_model=UserResponse)
def read_users_me(current: User = Depends(_resolve_current)):
    return UserResponse(id=current.id, email=current.email, full_name=current.full_name, role=current.role.value)


@router.get("/me/token-info", response_model=TokenInfo)
def read_token_info(current: User = Depends(_resolve_current)):
    return TokenInfo(sub=str(current.id), role=current.role.value, email=current.email,
                     patient_id=current.patient_id, doctor_id=current.doctor_id)
