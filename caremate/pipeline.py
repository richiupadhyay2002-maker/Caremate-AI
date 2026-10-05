"""Six-agent deterministic pipeline orchestrator.

Runs agents in sequence:
  Document → Retrieval → Summarization → Citation → Safety → Response
"""

from __future__ import annotations

from typing import Optional

from caremate.agents.base import PipelineData
from caremate.agents.document_agent import DocumentAgent
from caremate.agents.retrieval_agent import RetrievalAgent
from caremate.agents.summarization_agent import SummarizationAgent
from caremate.agents.citation_agent import CitationAgent
from caremate.agents.safety_agent import SafetyAgent
from caremate.agents.response_agent import ResponseAgent
from caremate.models.patient import PatientContext
from caremate.models.response import StructuredAIResponse
from caremate.providers.base import LLMProvider, EmbeddingProvider
from caremate.providers.mock import MockLLMProvider, MockEmbeddingProvider
from caremate.providers.factory import LLMFactory
from caremate.retrieval.chunker import SectionAwareChunker
from caremate.retrieval.vector_store import PatientIsolatedVectorStore
from caremate.retrieval.retriever import HybridRetriever
from caremate.retrieval.embeddings import EmbeddingManager
from caremate.guardrails.prompt_injection import PromptInjectionDetector
from caremate.guardrails.red_flag_symptoms import RedFlagDetector
from caremate.guardrails.drug_food_interactions import DrugFoodInteractionChecker
from caremate.utils.config import get_settings, get_logger

logger = get_logger(__name__)


class CarematePipeline:
    """Orchestrates the six-agent pipeline end-to-end."""

    def __init__(
        self,
        llm: LLMProvider | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        chunker: SectionAwareChunker | None = None,
        vector_store: PatientIsolatedVectorStore | None = None,
        use_mock: bool = False,
    ):
        settings = get_settings()

        if use_mock or settings.is_mock_mode:
            self._llm = llm or MockLLMProvider()
            self._embedding_provider = embedding_provider or MockEmbeddingProvider(dim=settings.vector_dim)
        else:
            self._llm = llm or LLMFactory.create_llm()
            self._embedding_provider = embedding_provider or LLMFactory.create_embedding_provider()

        self._chunker = chunker or SectionAwareChunker()
        self._vector_store = vector_store or PatientIsolatedVectorStore(dim=settings.vector_dim)
        self._embedding_manager = EmbeddingManager(self._embedding_provider)
        self._top_k = settings.top_k

        self._retriever = HybridRetriever(
            embedding_provider=self._embedding_provider,
            vector_store=self._vector_store,
            top_k=self._top_k,
        )

        self._document_agent = DocumentAgent(chunker=self._chunker)
        self._retrieval_agent = RetrievalAgent(retriever=self._retriever)
        self._summarization_agent = SummarizationAgent(llm=self._llm)
        self._citation_agent = CitationAgent(top_k=self._top_k)
        self._safety_agent = SafetyAgent(
            injection_detector=PromptInjectionDetector(embedding_provider=self._embedding_provider),
            red_flag_detector=RedFlagDetector(),
            interaction_checker=DrugFoodInteractionChecker(),
        )
        self._response_agent = ResponseAgent()

    @property
    def llm(self) -> LLMProvider:
        return self._llm

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        return self._embedding_provider

    @property
    def vector_store(self) -> PatientIsolatedVectorStore:
        return self._vector_store

    @property
    def retriever(self) -> HybridRetriever:
        return self._retriever

    def add_documents(self, documents: list[str], patient_id: str,
                      title: str = "clinical_note") -> int:
        """Chunk and index documents for a specific patient."""
        total_chunks = 0
        all_chunks: list = []
        for doc_text in documents:
            doc_id = f"doc_{patient_id}_{abs(hash(doc_text)) % 100000}"
            chunks = self._chunker.chunk_document(
                text=doc_text, document_id=doc_id, patient_id=patient_id)
            for chunk in chunks:
                chunk.embedding = self._embedding_provider.embed(chunk.content)
                self._vector_store.add_chunk(chunk)
            all_chunks.extend(chunks)
            total_chunks += len(chunks)

        if all_chunks:
            self._retriever.build_index(all_chunks)
        logger.info("Indexed %d chunks for patient %s", total_chunks, patient_id)
        return total_chunks

    def run(self, query: str, patient: PatientContext,
            raw_documents: list[str] | None = None) -> StructuredAIResponse:
        """Run the full six-agent pipeline."""
        data = PipelineData(
            query=query, patient=patient, raw_documents=raw_documents or [])
        logger.info("Pipeline started: query='%s...', patient=%s", query[:50], patient.patient_id)

        data = self._document_agent.process(data)
        data = self._retrieval_agent.process(data)
        data = self._summarization_agent.process(data)
        data = self._citation_agent.process(data)
        data = self._safety_agent.process(data)

        if data.safety_result and data.safety_result.short_circuit:
            logger.warning("Pipeline short-circuited by SafetyAgent")
            data = self._response_agent.process(data)
            return data.response  # type: ignore[return-value]

        data = self._response_agent.process(data)
        logger.info("Pipeline complete")
        return data.response  # type: ignore[return-value]

    def close(self) -> None:
        """Release provider resources."""
        self._llm.close()
        self._embedding_provider.close()
        LLMFactory.clear_cache()

