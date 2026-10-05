"""Document agent — preprocesses raw documents and chunks them.

This is the first agent in the pipeline: Document → Retrieval → …
"""

from __future__ import annotations

from typing import Any

from caremate.agents.base import BaseAgent, PipelineData
from caremate.models.document import DocumentChunk, DocumentMetadata
from caremate.retrieval.chunker import SectionAwareChunker
from caremate.utils.config import get_logger

logger = get_logger(__name__)


class DocumentAgent(BaseAgent):
    """Preprocesses raw documents into section-aware chunks.

    Each chunk is tagged with the patient_id to enforce isolation
    downstream in the vector store and retriever.
    """

    def __init__(self, chunker: SectionAwareChunker | None = None):
        self._chunker = chunker or SectionAwareChunker()

    @property
    def name(self) -> str:
        return "DocumentAgent"

    def process(self, data: PipelineData) -> PipelineData:
        """Chunk all raw documents in the pipeline data."""
        data.trace(self.name, f"Processing {len(data.raw_documents)} documents")

        if not data.raw_documents:
            data.trace(self.name, "No raw documents to process")
            return data

        patient_id = data.patient.patient_id if data.patient else "unknown"

        for doc_text in data.raw_documents:
            doc_id = f"doc_{patient_id}_{abs(hash(doc_text)) % 100000}"
            chunks = self._chunker.chunk_document(
                text=doc_text,
                document_id=doc_id,
                patient_id=patient_id,
            )
            data.chunks.extend(chunks)
            data.document_metadata[doc_id] = {
                "patient_id": patient_id,
                "chunk_count": len(chunks),
                "source": "raw_input",
            }
            data.trace(self.name, f"Document '{doc_id}': {len(chunks)} chunks")

        logger.info("DocumentAgent: %d chunks from %d documents",
                     len(data.chunks), len(data.raw_documents))
        return data
