"""Retrieval agent — retrieves relevant chunks from the vector store.

Second agent in the pipeline: Document → Retrieval → …

Uses hybrid retrieval (BM25 + embedding similarity) with reranking,
and enforces strict patient isolation via the vector store.
"""

from __future__ import annotations

from typing import Optional

from caremate.agents.base import BaseAgent, PipelineData
from caremate.models.document import DocumentChunk
from caremate.retrieval.retriever import HybridRetriever
from caremate.utils.config import get_logger

logger = get_logger(__name__)


class RetrievalAgent(BaseAgent):
    """Retrieves relevant document chunks for the current query.

    Uses a HybridRetriever that combines keyword (BM25) and embedding
    similarity, with patient isolation enforced by the vector store.
    """

    def __init__(self, retriever: HybridRetriever):
        self._retriever = retriever

    @property
    def name(self) -> str:
        return "RetrievalAgent"

    def process(self, data: PipelineData) -> PipelineData:
        """Retrieve the top-k most relevant chunks for the query."""
        if not data.patient:
            data.trace(self.name, "No patient context — skipping retrieval")
            return data

        patient_id = data.patient.patient_id

        # If we have chunks from DocumentAgent, use the retriever's direct method
        if data.chunks:
            results = self._retriever.retrieve_with_context(
                query=data.query,
                patient_id=patient_id,
                context_chunks=data.chunks,
            )
        else:
            # Otherwise, retrieve from the vector store
            results = self._retriever.retrieve(
                query=data.query,
                patient_id=patient_id,
            )

        data.retrieved_chunks = results
        data.trace(self.name, f"Retrieved {len(results)} chunks for patient {patient_id}")
        logger.info("RetrievalAgent: %d chunks retrieved", len(results))
        return data
