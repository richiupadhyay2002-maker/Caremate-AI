"""Persistent, patient-isolated vector store backed by PostgreSQL + pgvector.

This is a **drop-in replacement** for the in-memory
:class:`caremate.retrieval.vector_store.PatientIsolatedVectorStore`.  It
implements the exact same public interface so the existing pipeline and
retriever work unchanged.

Patient isolation is enforced structurally: every ``search`` /
``get_patient_chunks`` query includes ``WHERE patient_id = :pid`` at the SQL
level, making it architecturally impossible for one patient's chunks to appear
in another's results.
"""

from __future__ import annotations

import math

from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session

from caremate.db.models_docs import DocumentChunk as OrmChunk
from caremate.db.models_patients import Patient as OrmPatient
from caremate.models.document import DocumentChunk as PydanticChunk
from caremate.utils.config import get_logger

logger = get_logger(__name__)


class PgVectorStore:
    """PG/pgvector-backed vector store with strict patient isolation.

    Args:
        session: A SQLAlchemy ``Session`` (live) or a session factory/scope
                 callable.  The FastAPI dependency provides a per-request
                 session factory.
        dim:    Embedding dimensionality (informational; enforced on ingest).
    """

    def __init__(self, session, dim: int = 384):
        self._session = session
        self._dim = dim

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _sess(self) -> Session:
        if isinstance(self._session, Session):
            return self._session
        sess = self._session()
        self._session = sess  # cache for the life of this store
        return sess

    # ------------------------------------------------------------------
    # Properties (mirror the FAISS store interface)
    # ------------------------------------------------------------------
    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def total_chunks(self) -> int:
        return self._sess().execute(select(func.count()).select_from(OrmChunk)).scalar()

    @property
    def patients(self) -> list[str]:
        rows = self._sess().execute(select(OrmPatient.patient_id).distinct()).scalars().all()
        return list(rows)

    # ------------------------------------------------------------------
    # Insertion
    # ------------------------------------------------------------------
    def add_chunk(self, chunk: PydanticChunk) -> int:
        """Persist a single chunk into the database; returns the row id."""
        if not chunk.patient_id:
            raise ValueError("Chunk must have a patient_id — patient isolation enforced")
        if chunk.embedding is None:
            raise ValueError("Chunk must have an embedding vector")

        sess = self._sess()
        patient = sess.execute(
            select(OrmPatient).where(OrmPatient.patient_id == chunk.patient_id)
        ).scalars().first()

        orm = OrmChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            patient_id=chunk.patient_id,
            section_label=chunk.section_label,
            content=chunk.content,
            token_count=chunk.token_count,
            embedding=chunk.embedding,
            metadata_json=chunk.metadata,
        )
        if patient is not None:
            orm.patient = patient
        sess.add(orm)
        sess.flush()
        return orm.id

    

    # ------------------------------------------------------------------
    # Search (patient-isolated — enforced in SQL)
    # ------------------------------------------------------------------
    def search(
        self,
        query_embedding: list[float],
        patient_id: str,
        k: int = 5,
    ) -> list[tuple[PydanticChunk, float]]:
        """Search for similar chunks, **filtered to a single patient**.

        The ``WHERE patient_id = :pid`` clause is the structural isolation
        guarantee — cross-patient leakage is impossible at the SQL layer.
        """
        sess = self._sess()
        if not patient_id:
            raise ValueError("patient_id is required for search — isolation enforced")

        patient_row = sess.execute(
            select(OrmPatient).where(OrmPatient.patient_id == str(patient_id))
        ).scalars().first()
        if patient_row is None:
            return []

        is_pg = sess.bind.dialect.name == "postgresql"
        if is_pg:
            distance = func.l2_distance(OrmChunk.embedding, query_embedding)
            stmt = (
                select(OrmChunk, distance.label("score"))
                .where(OrmChunk.patient_id == patient_row.id)
                .where(OrmChunk.embedding.is_not(None))
                .order_by(distance.asc())
                .limit(k)
            )
            rows = sess.execute(stmt).all()
            return [(self._to_pydantic(r[0]), 1.0 - float(r[1])) for r in rows]

        # SQLite fallback — fetch matching chunks and compute cosine in Python
        stmt = (
            select(OrmChunk)
            .where(OrmChunk.patient_id == patient_row.id)
            .where(OrmChunk.embedding.is_not(None))
        )
        rows = sess.execute(stmt).scalars().all()
        scored: list[tuple[OrmChunk, float]] = []
        for orm_chunk in rows:
            emb = orm_chunk.embedding or []
            sim = self._cosine(query_embedding, emb) if emb else 0.0
            scored.append((orm_chunk, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(self._to_pydantic(c), s) for c, s in scored[:k]]

    def search_by_text(
        self,
        query: str,
        patient_id: str,
        embedding_provider,
        k: int = 5,
    ) -> list[tuple[PydanticChunk, float]]:
        """Convenience: embed the query text, then search."""
        emb = embedding_provider.embed(query)
        return self.search(emb, patient_id=patient_id, k=k)

    # ------------------------------------------------------------------
    # Patient management
    # ------------------------------------------------------------------
    def get_patient_chunks(self, patient_id: str) -> list[PydanticChunk]:
        sess = self._sess()
        patient_row = sess.execute(
            select(OrmPatient).where(OrmPatient.patient_id == str(patient_id))
        ).scalars().first()
        if patient_row is None:
            return []
        rows = sess.execute(
            select(OrmChunk).where(OrmChunk.patient_id == patient_row.id)
        ).scalars().all()
        return [self._to_pydantic(r) for r in rows]

    def has_patient(self, patient_id: str) -> bool:
        sess = self._sess()
        patient_row = sess.execute(
            select(OrmPatient).where(OrmPatient.patient_id == str(patient_id))
        ).scalars().first()
        if patient_row is None:
            return False
        count = sess.execute(
            select(func.count()).select_from(OrmChunk).where(OrmChunk.patient_id == patient_row.id)
        ).scalar()
        return count > 0

    def remove_patient(self, patient_id: str) -> int:
        sess = self._sess()
        patient_row = sess.execute(
            select(OrmPatient).where(OrmPatient.patient_id == str(patient_id))
        ).scalars().first()
        if patient_row is None:
            return 0
        count = sess.execute(
            select(func.count()).select_from(OrmChunk).where(OrmChunk.patient_id == patient_row.id)
        ).scalar()
        sess.execute(delete(OrmChunk).where(OrmChunk.patient_id == patient_row.id))
        sess.flush()
        logger.info("Removed %d chunks for patient %s", count, patient_id)
        return count

    def clear(self) -> None:
        sess = self._sess()
        sess.execute(delete(OrmChunk))
        sess.flush()

    
    @staticmethod
    def _to_pydantic(orm: OrmChunk) -> PydanticChunk:
        """Convert an ORM DocumentChunk to a pydantic DocumentChunk.

        Note: the ORM ``document_id`` / ``patient_id`` columns are integer
        foreign keys, but the pydantic model expects the *string* identifiers.
        We traverse the relationships to obtain the correct string values.
        """
        return PydanticChunk(
            chunk_id=orm.chunk_id,
            document_id=orm.document.document_id if orm.document else str(orm.document_id),
            patient_id=orm.patient.patient_id if orm.patient else "",
            section_label=orm.section_label,
            page_number=orm.page_number,
            confidence=orm.confidence,
            content=orm.content,
            token_count=orm.token_count,
            embedding=(list(orm.embedding) if orm.embedding is not None else None),
            metadata=dict(orm.metadata_json or {}),
        )

    @staticmethod
    def _cosine(vec_a: list[float], vec_b: list[float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        na = math.sqrt(sum(a * a for a in vec_a))
        nb = math.sqrt(sum(b * b for b in vec_b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

