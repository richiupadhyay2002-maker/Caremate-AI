"""Document and document-chunk models (pgvector-enabled chunk table)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func,
)
from sqlalchemy.orm import relationship

from caremate.db.base import Base, Vector
from caremate.utils.config import get_settings


class DocumentType:
    """Namespace for document-type string constants.

    Matches the fixed set used by DocumentAgent and the ingestion pipeline.
    """
    CLINICAL_NOTE = "clinical_note"
    PATHOLOGY_REPORT = "pathology_report"
    RADIOLOGY_REPORT = "radiology_report"
    LAB_REPORT = "lab_report"
    DISCHARGE_SUMMARY = "discharge_summary"
    PRESCRIPTION = "prescription"
    OTHER = "other"

    _ALL = frozenset({
        CLINICAL_NOTE,
        PATHOLOGY_REPORT,
        RADIOLOGY_REPORT,
        LAB_REPORT,
        DISCHARGE_SUMMARY,
        PRESCRIPTION,
        OTHER,
    })

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls._ALL


# Convenience set for validation checks
DOCUMENT_TYPES = DocumentType._ALL


class MedicalDocument(Base):
    __tablename__ = "medical_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(128), nullable=False, unique=True, index=True)
    patient_id = Column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(300), default="clinical_note")
    document_type = Column(String(50), default=DocumentType.CLINICAL_NOTE)
    source = Column(String(100), default="manual")
    raw_text = Column(Text, default="")
    tags = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    patient = relationship("Patient", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(String(128), nullable=False, unique=True, index=True)
    document_id = Column(ForeignKey("medical_documents.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    section_label = Column(String(100), default="unknown")
    page_number = Column(Integer, nullable=True, doc="1-based page number in the source document")
    confidence = Column(Float, nullable=True, doc="OCR / extraction confidence 0.0-1.0")
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    embedding = Column(Vector(get_settings().vector_dim), nullable=True)
    metadata_json = Column(JSON, default={}, name="metadata")
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    document = relationship("MedicalDocument", back_populates="chunks")
    patient = relationship("Patient", back_populates="chunks")
    citations = relationship("Citation", back_populates="chunk", cascade="all, delete-orphan")

    @property
    def section(self) -> str:
        return self.section_label
