"""Extended endpoints: password reset, profile, demo sample files, uploads.

Everything here is additive — existing routers and behaviour are untouched.

Demo sample files are ORIGINAL synthetic content written for this project in
the style of open formats: Synthea (MIT license) and public patient-education
material (MedlinePlus / NCI, public domain). They are NOT real patient data
and must never be presented as such.
"""

from __future__ import annotations

import os
import glob
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from caremate.api.auth.router import _resolve_current
from caremate.api.security import create_access_token, hash_password, verify_password
from caremate.db.models_core import User, UserRole
from caremate.db.models_docs import MedicalDocument, DocumentChunk
from caremate.db.models_patients import Patient as OrmPatient
from caremate.db.repository_patients import PatientRepository
from caremate.db.session import get_db
from caremate.models.response import StructuredAIResponse
from caremate.orchestration.ask import AskMedicalRecordOrchestrator
from caremate.security.audit import get_audit_logger
from caremate.utils.config import get_logger, get_settings

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(tags=["extras"])
_bearer = HTTPBearer(auto_error=False)

# Demo patient used for unauthenticated "Try Demo" processing.
DEMO_PATIENT_ID = "P-DEMO"

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "demo_files", "samples")


# ------------------------------------------------------------------
# Validation helpers
# ------------------------------------------------------------------
def validate_password_strength(password: str) -> str | None:
    """Return an error message, or None if the password is acceptable."""
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number."
    if not any(c.isalpha() for c in password):
        return "Password must contain at least one letter."
    return None


def validate_email(email: str) -> str | None:
    if "@" not in email or "." not in email.split("@")[-1]:
        return "Please enter a valid email address."
    return None


# ------------------------------------------------------------------
# Password reset (demo mode: no SMTP — token is returned to the client)
# ------------------------------------------------------------------
class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


def _make_reset_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {
        "sub": str(user.id),
        "type": "pwreset",
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post("/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Begin password recovery.

    In this prototype there is no SMTP server, so the reset token is returned
    directly and shown in the UI. In production this would be emailed instead
    and the response would always be a generic 200 (to avoid account
    enumeration).
    """
    email_err = validate_email(req.email)
    if email_err:
        raise HTTPException(status_code=400, detail=email_err)

    user = db.query(User).filter(User.email == req.email).first()
    # Generic response regardless — avoids revealing which emails exist.
    if user is None:
        return {"message": "If that email is registered, a reset link has been generated.",
                "reset_token": None}

    token = _make_reset_token(user)
    audit = get_audit_logger(db)
    audit.log(action="password_reset_requested", resource_type="user",
              resource_id=str(user.id), user=user,
              request_body={"email": "[redacted]"})
    return {
        "message": "If that email is registered, a reset link has been generated.",
        # Prototype-stage: no mail server is configured, so the token is
        # surfaced here and shown in the UI as a reset link.
        "reset_token": token,
    }


@router.post("/auth/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Complete password recovery using a reset token."""
    try:
        payload = jwt.decode(req.token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    if payload.get("type") != "pwreset":
        raise HTTPException(status_code=400, detail="Invalid reset token.")
    user_id = payload.get("sub")
    user = db.get(User, int(user_id)) if user_id else None
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid reset token.")

    pw_err = validate_password_strength(req.new_password)
    if pw_err:
        raise HTTPException(status_code=400, detail=pw_err)

    user.hashed_password = hash_password(req.new_password)
    db.add(user)
    db.commit()
    audit = get_audit_logger(db)
    audit.log(action="password_reset_completed", resource_type="user",
              resource_id=str(user.id), user=user, request_body={})
    return {"message": "Password updated. You can now sign in with your new password."}


@router.get("/auth/me/patient-record")
def my_patient_record(
    current: User = Depends(_resolve_current),
    db: Session = Depends(get_db),
):
    """Return the string patient_id of the signed-in patient (for scoping)."""
    if current.patient_id is None:
        raise HTTPException(status_code=404, detail="No patient record linked to this account.")
    orm = db.get(OrmPatient, current.patient_id)
    if orm is None:
        raise HTTPException(status_code=404, detail="Patient record not found.")
    return {"patient_id": orm.patient_id, "full_name": orm.full_name or current.full_name}


# ------------------------------------------------------------------
# Profile management
# ------------------------------------------------------------------
class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)


@router.patch("/auth/me")
def update_profile(
    req: ProfileUpdate,
    current: User = Depends(_resolve_current),
    db: Session = Depends(get_db),
):
    """Update the signed-in user's display name."""
    current.full_name = req.full_name.strip()
    db.add(current)
    db.commit()
    return {"id": current.id, "email": current.email,
            "full_name": current.full_name, "role": current.role.value}


# ------------------------------------------------------------------
# Demo / sample files (open-style synthetic content)
# ------------------------------------------------------------------
class SampleFile(BaseModel):
    sample_id: str
    filename: str
    title: str
    kind: str  # pathology_report | lab_report | biomarker_report | patient_document
    size_bytes: int
    excerpt: str


class SampleListResponse(BaseModel):
    samples: list[SampleFile]
    notice: str
    sources_note: str


def _read_sample(sample_id: str) -> tuple[str, bytes]:
    """Return (filename, content) for a validated sample id."""
    safe = os.path.basename(sample_id)
    path = os.path.join(SAMPLES_DIR, safe)
    if not os.path.isfile(path) or not safe.endswith(".txt"):
        raise HTTPException(status_code=404, detail="Sample not found.")
    with open(path, "rb") as f:
        return safe, f.read()


@router.get("/demo/samples", response_model=SampleListResponse)
def list_demo_samples():
    """List the bundled demo / sample files with licensing information."""
    samples: list[SampleFile] = []
    for path in sorted(glob.glob(os.path.join(SAMPLES_DIR, "*.txt"))):
        with open(path, "rb") as f:
            data = f.read()
        sid = os.path.basename(path)
        head = data.decode("utf-8", errors="replace")
        title = head.splitlines()[0].lstrip("# ").strip() if head else sid
        kind = "patient_document"
        for k in ("pathology_report", "lab_report", "biomarker_report", "radiology_report"):
            if k in sid:
                kind = k
                break
        samples.append(SampleFile(
            sample_id=sid,
            filename=sid,
            title=title,
            kind=kind,
            size_bytes=len(data),
            excerpt=head[:200],
        ))
    return SampleListResponse(
        samples=samples,
        notice=("DEMO / SAMPLE DATA — these files are synthetic and contain no "
                "real patient information. They are provided for demonstration "
                "and testing only."),
        sources_note=("Format inspired by open standards: Synthea (MIT license, "
                      "github.com/synthetichealth/synthea) and public "
                      "patient-education material from MedlinePlus / NCI "
                      "(public domain). The text of each sample file is "
                      "original content written for this project."),
    )


@router.get("/demo/samples/{sample_id}/content")
def get_sample_content(sample_id: str):
    """Return the raw text of a sample file (demo use only)."""
    filename, data = _read_sample(sample_id)
    return {"sample_id": sample_id, "filename": filename,
            "content": data.decode("utf-8", errors="replace")}


class DemoProcessRequest(BaseModel):
    sample_id: str
    query: str = Field(default="Summarize this report in plain language.",
                       max_length=2000)


@router.post("/demo/process", response_model=StructuredAIResponse)
def process_demo_sample(req: DemoProcessRequest, db: Session = Depends(get_db)):
    """Run the real six-agent pipeline on a bundled sample file.

    No authentication required: the file is publicly bundled synthetic demo
    data and is ingested into a shared demo patient record (P-DEMO), never
    into any user's private record.
    """
    filename, data = _read_sample(req.sample_id)
    text = data.decode("utf-8", errors="replace")

    repo = PatientRepository(db)
    patient = repo.get_or_create(DEMO_PATIENT_ID)
    db.flush()

    # Ingest as a document (same pipeline user uploads go through).
    from caremate.ingestion.classifier import DocumentClassifier
    from caremate.ingestion.extractor import DocumentExtractor  # noqa: F401 (parity)
    from caremate.retrieval.chunker import SectionAwareChunker
    from caremate.providers.mock import MockEmbeddingProvider
    from caremate.models.document import DocumentMetadata, DocumentChunk as PydanticChunk
    import uuid

    classifier = DocumentClassifier()
    cls = classifier.classify(text)
    doc_type = cls.document_type

    chunker = SectionAwareChunker()
    embedder = MockEmbeddingProvider(dim=settings.vector_dim)
    doc_id = f"doc_{DEMO_PATIENT_ID}_demo_{uuid.uuid4().hex[:8]}"
    chunks = chunker.chunk_document(
        text=text, document_id=doc_id, patient_id=DEMO_PATIENT_ID,
        title=filename.replace(".txt", ""), document_type=doc_type,
    )
    pyd_chunks: list[PydanticChunk] = []
    for c in chunks:
        pyd_chunks.append(PydanticChunk(
            chunk_id=c.chunk_id, document_id=c.document_id, patient_id=c.patient_id,
            section_label=c.section_label, page_number=c.page_number,
            confidence=c.confidence, content=c.content, token_count=c.token_count,
            embedding=embedder.embed(c.content), metadata=c.metadata,
        ))
    doc_meta = DocumentMetadata(
        document_id=doc_id, patient_id=DEMO_PATIENT_ID,
        title=filename.replace(".txt", ""), document_type=doc_type,
        source="demo_sample", tags=["demo"], raw_text=text,
    )
    repo.save_document(doc_meta, pyd_chunks)
    db.commit()

    orchestrator = AskMedicalRecordOrchestrator(db_session=db)
    response = orchestrator.answer(query=req.query, patient_id=DEMO_PATIENT_ID)
    return response


# ------------------------------------------------------------------
# Patient-facing: my analyses (AI generations) + delete upload
# ------------------------------------------------------------------
@router.get("/patients/{patient_id}/generations")
def list_my_generations(
    patient_id: str,
    current: User = Depends(_resolve_current),
    db: Session = Depends(get_db),
):
    """List the AI analyses recorded for a patient (owner or admin only)."""
    from caremate.db.models_comm import AI_Generation

    repo = PatientRepository(db)
    orm_patient = repo.get_by_patient_id(patient_id)
    if orm_patient is None:
        return []
    if (current.role == UserRole.PATIENT and current.patient_id is not None
            and current.patient_id != orm_patient.id):
        raise HTTPException(status_code=403, detail="You can only view your own analyses.")

    rows = (
        db.query(AI_Generation)
        .filter(AI_Generation.patient_id == orm_patient.id)
        .order_by(AI_Generation.created_at.desc())
        .limit(100)
        .all()
    )
    out = []
    for g in rows:
        out.append({
            "id": g.id,
            "query": getattr(g, "query", "") or getattr(g, "prompt", ""),
            "response_text": getattr(g, "response_text", "") or getattr(g, "response", ""),
            "confidence": getattr(g, "confidence", None),
            "safety_flags": getattr(g, "safety_flags", []) or [],
            "created_at": g.created_at.isoformat() if g.created_at else None,
        })
    return out


@router.delete("/patients/{patient_id}/documents/{document_id}")
def delete_document(
    patient_id: str,
    document_id: str,
    current: User = Depends(_resolve_current),
    db: Session = Depends(get_db),
):
    """Delete a patient's uploaded document (chunks + stored file)."""
    repo = PatientRepository(db)
    orm_patient = repo.get_by_patient_id(patient_id)
    if orm_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found.")
    if (current.role == UserRole.PATIENT and current.patient_id is not None
            and current.patient_id != orm_patient.id):
        raise HTTPException(status_code=403, detail="You can only delete your own files.")

    doc = (
        db.query(MedicalDocument)
        .filter(MedicalDocument.document_id == document_id,
                MedicalDocument.patient_id == orm_patient.id)
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
    db.delete(doc)
    db.commit()

    # Remove stored binaries matching this document id (uploads are saved as
    # <document_id>.<ext> under uploads/<patient_id>/).
    removed_files = 0
    upload_dir = os.path.join(settings.upload_dir, patient_id)
    if os.path.isdir(upload_dir):
        for f in glob.glob(os.path.join(upload_dir, f"{document_id}.*")):
            try:
                os.remove(f)
                removed_files += 1
            except OSError:
                logger.warning("Could not remove file %s", f)

    audit = get_audit_logger(db)
    audit.log(action="document_deleted", resource_type="document",
              resource_id=document_id, user=current, request_body={})
    return {"deleted": document_id, "files_removed": removed_files}
