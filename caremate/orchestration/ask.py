"""AskMedicalRecordOrchestrator — wires the pipeline to the database-backed vector store.

This is the orchestration entry-point for the ``POST /patients/{id}/ask`` API
endpoint.  It replaces the old script-style flow that used an in-memory
``PatientIsolatedVectorStore`` with the persistent
:class:`~caremate.db.vector_store.PgVectorStore`, so that:

- retrieved context comes from the real Postgres document_chunks table,
- patient isolation is enforced at the SQL level (`WHERE patient_id = ?`),
- every AI response is persisted in ``ai_generations`` with citations.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from caremate.db.repository_patients import PatientRepository
from caremate.db.vector_store import PgVectorStore
from caremate.models.patient import PatientContext
from caremate.models.response import StructuredAIResponse
from caremate.pipeline import CarematePipeline
from caremate.providers.base import EmbeddingProvider, LLMProvider
from caremate.providers.mock import MockEmbeddingProvider, MockLLMProvider
from caremate.retrieval.retriever import HybridRetriever
from caremate.utils.config import get_logger, get_settings

logger = get_logger(__name__)


class AskMedicalRecordOrchestrator:
    """Run the medical-record Q&A pipeline against the database-backed store.

    Args:
        db_session:      An open SQLAlchemy session.
        llm:             Optional custom LLMProvider (defaults to mock / config).
        embedding_provider: Optional custom EmbeddingProvider.
    """

    def __init__(
        self,
        db_session: Session,
        llm: Optional[LLMProvider] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        self._db = db_session
        settings = get_settings()
        self._embedding_provider = embedding_provider or (
            MockEmbeddingProvider(dim=settings.vector_dim) if settings.is_mock_mode
            else embedding_provider
        )
        self._pipeline: Optional[CarematePipeline] = None
        self._repo = PatientRepository(db_session)

    @property
    def pipeline(self) -> CarematePipeline:
        """Lazily build a CarematePipeline wired with a PgVectorStore."""
        if self._pipeline is None:
            settings = get_settings()
            store = PgVectorStore(session=self._db, dim=settings.vector_dim)
            self._pipeline = CarematePipeline(
                llm=MockLLMProvider() if True else None,
                embedding_provider=self._embedding_provider,
                vector_store=store,
                use_mock=True,
            )
        return self._pipeline

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        return self._embedding_provider

    @property
    def vector_store(self) -> PgVectorStore:
        return self.pipeline.vector_store

    def build_patient_context(self, patient_id: str) -> PatientContext:
        """Load a PatientContext from the database for *patient_id*.

        If the patient row does not yet exist it is created on the fly
        (allowing a brand-new patient to query immediately — their context
        simply has empty defaults until documents are ingested).
        """
        orm_patient = self._repo.get_by_patient_id(patient_id)
        if orm_patient is None:
            orm_patient = self._repo.get_or_create(patient_id)
            self._db.flush()
        return self._repo.to_context(orm_patient)

    def add_documents(self, documents: list[str], patient_id: str) -> int:
        """Chunk and index documents for a patient via the DB-backed store."""
        return self.pipeline.add_documents(documents, patient_id=patient_id)

    def answer(
        self,
        query: str,
        patient_id: str,
        raw_documents: Optional[list[str]] = None,
    ) -> StructuredAIResponse:
        """Answer a medical question for *patient_id*, persisted to the DB.

        Steps:
          1. Load (or create) the patient record and build a PatientContext.
          2. Run the six-agent pipeline with the PgVectorStore as retriever.
          3. Persist the AI_Generation + citations to the database.
          4. Return the StructuredAIResponse to the API layer.
        """
        patient_context = self.build_patient_context(patient_id)
        logger.info("AskMedicalRecordOrchestrator answering for patient %s", patient_id)

        response = self.pipeline.run(
            query=query,
            patient=patient_context,
            raw_documents=raw_documents or [],
        )
        # Persist the generation + citations
        try:
            self._repo.save_generation(response, patient_id, query)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist AI generation: %s", exc)

        return response

    def close(self) -> None:
        if self._pipeline is not None:
            self._pipeline.close()
