"""NutritionQAOrchestrator — DB-backed nutrition Q&A.

Wraps the existing :class:`~caremate.nutrition.qa.NutritionQA` and routes
it through the database-backed :class:`AskMedicalRecordOrchestrator` so
the ``/patients/{id}/ask/nutrition`` endpoint uses real persistence.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from caremate.db.vector_store import PgVectorStore
from caremate.models.response import StructuredAIResponse
from caremate.nutrition.qa import NutritionQA
from caremate.orchestration.ask import AskMedicalRecordOrchestrator
from caremate.providers.base import EmbeddingProvider, LLMProvider
from caremate.providers.mock import MockLLMProvider
from caremate.utils.config import get_settings
from caremate.utils.config import get_logger

logger = get_logger(__name__)

# Re-export for convenience
__all__ = ["NutritionQAOrchestrator", "NutritionQA"]


class NutritionQAOrchestrator(AskMedicalRecordOrchestrator):
    """DB-backed nutrition Q&A, extending the medical-record orchestrator.

    Builds a :class:`NutritionQA` instance backed by the same PgVectorStore
    and patient context loaded from the database.
    """

    def __init__(
        self,
        db_session: Session,
        llm: Optional[LLMProvider] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        super().__init__(db_session, llm=llm, embedding_provider=embedding_provider)
        self._qa: Optional[NutritionQA] = None

    @property
    def qa(self) -> NutritionQA:
        """Lazily construct the NutritionQA with a DB-backed pipeline."""
        if self._qa is None:
            settings = get_settings()
            llm = MockLLMProvider() if settings.is_mock_mode else None
            self._qa = NutritionQA(self.pipeline)
        return self._qa

    def answer(
        self,
        query: str,
        patient_id: str,
        raw_documents: Optional[list[str]] = None,
    ) -> StructuredAIResponse:
        """Answer a nutrition question using DB-backed patient context."""
        patient_context = self.build_patient_context(patient_id)
        logger.info("NutritionQAOrchestrator answering for patient %s", patient_id)

        response = self.qa.answer(
            query=query,
            patient=patient_context,
            raw_documents=raw_documents or [],
        )
        try:
            self._repo.save_generation(response, patient_id, query)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist AI generation: %s", exc)
        return response

    def close(self) -> None:
        super().close()
