"""Document ingestion endpoints: upload texts, list documents and chunks."""

from __future__ import annotations

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from caremate.api.deps import get_current_user
from caremate.db.models_docs import MedicalDocument, DocumentChunk, DocumentType, DOCUMENT_TYPES
from caremate.db.models_patients import Patient as OrmPatient
from caremate.db.repository_patients import PatientRepository
from caremate.db.session import get_db
from caremate.ingestion.classifier import DocumentClassifier
from caremate.ingestion.extractor import DocumentExtractor, PDF_EXTENSIONS, IMAGE_EXTENSIONS
from caremate.models.document import DocumentMetadata, DocumentChunk as PydanticChunk
from caremate.retrieval.chunker import SectionAwareChunker
from caremate.providers.mock import MockEmbeddingProvider
from caremate.security.audit import get_audit_logger
from caremate.security.authorization import get_client_info
from caremate.security.signed_urls import generate_signed_url, verify_signed_url
from caremate.utils.config import get_logger, get_settings

settings = get_settings()
router = APIRouter(prefix="/patients", tags=["patients"])

# Upload constraints
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = PDF_EXTENSIONS | IMAGE_EXTENSIONS


class IngestRequest(BaseModel):
    text: str = Field(..., description="Raw medical document text to ingest")
    title: str = Field(default="clinical_note")
    document_type: str = Field(default="clinical_note")
    source: str = Field(default="manual")
    tags: list[str] = Field(default_factory=list)
    document_id: Optional[str] = None


class IngestResponse(BaseModel):
    document_id: str
    num_chunks: int
    chunk_ids: list[str]


class UploadResponse(BaseModel):
    """Response for the file upload endpoint."""
    document_id: str
    num_chunks: int
    chunk_ids: list[str]
    pages_extracted: int
    ocr_used: bool
    document_type: str = Field(..., description="Auto-classified or user-specified document type")
    classification_confidence: float = Field(..., description="Confidence of auto-classification")


def _get_own_patient(patient_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Shared ownership check + patient lookup.

    Authenticated patients may only access their own record; doctors and
    admins may access any patient's record (documents are part of care).
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


@router.post("/{patient_id}/documents", response_model=IngestResponse)
def ingest_document(
    patient_id: str,
    req: IngestRequest,
    orm_patient: OrmPatient = Depends(_get_own_patient),
    db: Session = Depends(get_db),
):
    """Ingest a medical document: chunk, embed, and persist to the DB."""
    chunker = SectionAwareChunker()
    embedder = MockEmbeddingProvider(dim=settings.vector_dim)

    doc_id = req.document_id or f"doc_{patient_id}_{uuid.uuid4().hex[:8]}"
    chunks = chunker.chunk_document(
        text=req.text, document_id=doc_id, patient_id=patient_id,
        title=req.title, document_type=req.document_type,
    )

    pydantic_chunks: list[PydanticChunk] = []
    for c in chunks:
        emb = embedder.embed(c.content)
        pyd = PydanticChunk(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            patient_id=c.patient_id,
            section_label=c.section_label,
            page_number=c.page_number,
            confidence=c.confidence,
            content=c.content,
            token_count=c.token_count,
            embedding=emb,
            metadata=c.metadata,
        )
        pydantic_chunks.append(pyd)

    repo = PatientRepository(db)
    doc_meta = DocumentMetadata(
        document_id=doc_id,
        patient_id=patient_id,
        title=req.title,
        document_type=req.document_type,
        source=req.source,
        tags=req.tags,
        raw_text=req.text,
    )
    repo.save_document(doc_meta, pydantic_chunks)
    db.commit()

    return IngestResponse(
        document_id=doc_id,
        num_chunks=len(pydantic_chunks),
        chunk_ids=[c.chunk_id for c in pydantic_chunks],
    )


@router.post("/{patient_id}/documents/upload", response_model=UploadResponse)
async def upload_document(
    patient_id: str,
    file: UploadFile = File(...),
    title: str = Form(default=None),
    document_type: Optional[str] = Form(default=None),
    tags: list[str] = Form(default=None),
    orm_patient: OrmPatient = Depends(_get_own_patient),
    db: Session = Depends(get_db),
):
    """Upload a real medical document (PDF or image) for ingestion.

    The file is validated, stored locally, text is extracted (with OCR
    fallback for scanned documents), the document type is auto-classified,
    and the resulting text is chunked and persisted with full provenance
    (page number, section, confidence).

    Patients can only upload to their own records; doctors and admins
    may upload for any patient.
    """
    # --- 1. File validation ---
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # Read file content and validate size
    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {file_size} bytes. Maximum is {MAX_UPLOAD_BYTES} bytes.",
        )
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # --- 2. Security check: validate magic bytes ---
    # Allow only known safe medical document formats: PDF, PNG, JPEG, TIFF, BMP, GIF
    SAFE_MAGIC = [
        b"%PDF",  # PDF
        b"\x89PNG",  # PNG
        b"\xff\xd8\xff",  # JPEG
        b"II*\x00",  # TIFF (little-endian)
        b"MM\x00*",  # TIFF (big-endian)
        b"BM",  # BMP
        b"GIF8",  # GIF
    ]
    is_safe = any(file_bytes.startswith(m) for m in SAFE_MAGIC)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match expected medical document format.",
        )

    # --- 3. Store file locally with UUID naming (patient-scoped) ---
    # The stored binary is keyed to the document id so the delete endpoint
    # can remove it along with the DB records.
    doc_id = f"doc_{patient_id}_{uuid.uuid4().hex[:8]}"
    stored_filename = f"{doc_id}{ext}"
    upload_dir = os.path.join(settings.upload_dir, patient_id)
    os.makedirs(upload_dir, exist_ok=True)
    stored_path = os.path.join(upload_dir, stored_filename)
    with open(stored_path, "wb") as f:
        f.write(file_bytes)

    # --- 4. Extract text (with OCR fallback) ---
    extractor = DocumentExtractor()
    pages: list = extractor.extract(stored_path)
    ocr_used = any(p.source == "ocr" for p in pages)

    # Combine all pages into full text, preserving page boundaries
    full_text = "\n".join(p.text for p in pages if p.text)

    # --- 5. Classify document type ---
    classifier = DocumentClassifier()
    if document_type and document_type in DOCUMENT_TYPES:
        classification_result = classifier.classify(full_text)
        doc_type = document_type  # user override
        classification_confidence = classification_result.confidence
    else:
        classification_result = classifier.classify(full_text)
        doc_type = classification_result.document_type
        classification_confidence = classification_result.confidence

    # --- 6. Chunk with page-level provenance ---
    chunker = SectionAwareChunker()
    embedder = MockEmbeddingProvider(dim=settings.vector_dim)

    pydantic_chunks: list[PydanticChunk] = []

    for page in pages:
        if not page.text.strip():
            continue
        chunks = chunker.chunk_document(
            text=page.text,
            document_id=doc_id,
            patient_id=patient_id,
            title=title or doc_type,
            document_type=doc_type,
            page_number=page.page_number,
            confidence=page.confidence,
        )
        for c in chunks:
            emb = embedder.embed(c.content)
            pyd = PydanticChunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                patient_id=c.patient_id,
                section_label=c.section_label,
                page_number=c.page_number,
                confidence=c.confidence,
                content=c.content,
                token_count=c.token_count,
                embedding=emb,
                metadata=c.metadata,
            )
            pydantic_chunks.append(pyd)

    # --- 7. Persist ---
    repo = PatientRepository(db)
    doc_meta = DocumentMetadata(
        document_id=doc_id,
        patient_id=patient_id,
        title=title or doc_type,
        document_type=doc_type,
        source=f"upload:{file.filename or stored_filename}",
        tags=tags or [],
        raw_text=full_text,
    )
    repo.save_document(doc_meta, pydantic_chunks)
    db.commit()

    return UploadResponse(
        document_id=doc_id,
        num_chunks=len(pydantic_chunks),
        chunk_ids=[c.chunk_id for c in pydantic_chunks],
        pages_extracted=len([p for p in pages if p.text.strip()]),
        ocr_used=ocr_used,
        document_type=doc_type,
        classification_confidence=round(classification_confidence, 4),
    )


@router.get("/{patient_id}/documents", response_model=list)
def list_documents(
    patient_id: str,
    orm_patient: OrmPatient = Depends(_get_own_patient),
    db: Session = Depends(get_db),
):
    """List all documents for a patient."""
    docs = db.query(MedicalDocument).filter(MedicalDocument.patient_id == orm_patient.id).all()
    return [
        {"document_id": d.document_id, "title": d.title, "document_type": d.document_type,
         "source": d.source, "created_at": d.created_at.isoformat() if d.created_at else None}
        for d in docs
    ]


@router.get("/{patient_id}/documents/{document_id}/signed-url")
def get_signed_url(
    patient_id: str,
    document_id: str,
    request: Request,
    expires_in: int = 3600,
    orm_patient: OrmPatient = Depends(_get_own_patient),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate a time-limited signed download URL for a document."""
    doc = (
        db.query(MedicalDocument)
        .filter(
            MedicalDocument.document_id == document_id,
            MedicalDocument.patient_id == orm_patient.id,
        )
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Audit-log the document access request
    client_info = get_client_info(request) if request else {"ip_address": "", "user_agent": ""}
    audit = get_audit_logger(db)
    audit.log_document_access(
        document_id=document_id,
        patient_id=patient_id,
        user=current_user,
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
    )

    url = generate_signed_url(document_id, expires_in=expires_in)
    return {"signed_url": url, "expires_in": expires_in}
