"""Patient & document data-access repository."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from caremate.db.models_docs import DocumentChunk as OrmChunk, MedicalDocument as OrmDoc
from caremate.db.models_patients import Patient as OrmPatient
from caremate.db.models_comm import AI_Generation as OrmGen, Citation as OrmCitation
from caremate.models.patient import PatientContext, MedicationEntry, AllergyEntry
from caremate.models.document import DocumentChunk, DocumentMetadata
from caremate.models.response import StructuredAIResponse
from caremate.utils.config import get_logger

logger = get_logger(__name__)


class PatientRepository:
    """Read/write patient records and convert to/from Pydantic models."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_patient_id(self, patient_id: str) -> Optional[OrmPatient]:
        return self._session.execute(
            select(OrmPatient).where(OrmPatient.patient_id == patient_id)
        ).scalars().first()

    def get_or_create(self, patient_id: str, **attrs) -> OrmPatient:
        orm = self.get_by_patient_id(patient_id)
        if orm is None:
            orm = OrmPatient(patient_id=patient_id, **attrs)
            self._session.add(orm)
            self._session.flush()
            logger.info("Created patient record %s", patient_id)
        return orm

    def update_from_context(self, orm: OrmPatient, ctx: PatientContext) -> None:
        """Sync a Pydantic PatientContext into the ORM model."""
        orm.full_name = ctx.name or orm.full_name
        orm.age = ctx.age
        orm.sex = ctx.sex
        orm.medical_history = list(ctx.medical_history)
        orm.allergies = [a.model_dump() for a in ctx.allergies]
        orm.dietary_restrictions = list(ctx.dietary_restrictions)
        orm.recent_weight = ctx.recent_weight
        orm.height = ctx.height
        orm.lab_results = dict(ctx.lab_results)
        orm.notes = ctx.notes or orm.notes
        self._session.add(orm)

    def to_context(self, orm: OrmPatient) -> PatientContext:
        """Convert an ORM Patient into a domain PatientContext."""
        med_entries = [
            MedicationEntry(name=m.name, dosage=m.dosage, frequency=m.frequency)
            for m in (orm.medications or [])
        ]
        allergy_entries = [
            AllergyEntry(**a) if isinstance(a, dict) else a
            for a in (orm.allergies or [])
        ]
        return PatientContext(
            patient_id=orm.patient_id,
            name=orm.full_name,
            age=orm.age,
            sex=orm.sex,
            medical_history=list(orm.medical_history or []),
            current_medications=med_entries,
            allergies=allergy_entries,
            dietary_restrictions=list(orm.dietary_restrictions or []),
            recent_weight=orm.recent_weight,
            height=orm.height,
            lab_results=dict(orm.lab_results or {}),
            notes=orm.notes,
        )

    def save_document(self, doc_metadata: DocumentMetadata,
                      chunks: list[DocumentChunk]) -> OrmDoc:
        """Persist a medical document header and its chunks in one transaction."""
        patient = self.get_or_create(doc_metadata.patient_id)
        orm_doc = OrmDoc(
            document_id=doc_metadata.document_id,
            patient_id=patient.id,
            title=doc_metadata.title,
            document_type=doc_metadata.document_type,
            source=doc_metadata.source,
            raw_text=doc_metadata.raw_text or "",
            tags=list(doc_metadata.tags),
        )
        self._session.add(orm_doc)
        self._session.flush()
        for chunk in chunks:
            orm_chunk = OrmChunk(
                chunk_id=chunk.chunk_id,
                document_id=orm_doc.id,
                patient_id=patient.id,
                section_label=chunk.section_label,
                page_number=chunk.page_number,
                confidence=chunk.confidence,
                content=chunk.content,
                token_count=chunk.token_count,
                embedding=chunk.embedding,
                metadata_json=chunk.metadata,
            )
            self._session.add(orm_chunk)
        self._session.flush()
        logger.info("Persisted document %s (%d chunks) for patient %s",
                    doc_metadata.document_id, len(chunks), doc_metadata.patient_id)
        return orm_doc

    def save_generation(self, response: StructuredAIResponse,
                        patient_id: str, query: str) -> OrmGen:
        """Persist an AI response and its citations."""
        patient = self.get_by_patient_id(patient_id)
        orm_gen = OrmGen(
            patient_id=patient.id if patient else None,
            query=query,
            response_text=response.response,
            confidence=response.confidence,
            safety_flags=[f.value if hasattr(f, "value") else str(f)
                          for f in response.safety_flags],
            full_response_json=response.model_dump(),
        )
        self._session.add(orm_gen)
        self._session.flush()
        for citation in response.citations:
            chunk_orm = self._session.execute(
                select(OrmChunk).where(OrmChunk.chunk_id == citation.chunk_id)
            ).scalars().first()
            orm_cite = OrmCitation(
                ai_generation_id=orm_gen.id,
                chunk_id=chunk_orm.id if chunk_orm else None,
                chunk_ref=citation.chunk_id,
                source_document=citation.source_document,
                section=citation.section,
                page_number=citation.page_number,
                relevance_score=citation.relevance_score,
                text_snippet=citation.text_snippet,
                patient_id=patient.id if patient else None,
            )
            self._session.add(orm_cite)
        self._session.flush()
        logger.info("Persisted AI generation for patient %s", patient_id)
        return orm_gen
