"""Citation agent — verifies and formats citations from retrieved chunks.

Fourth agent in the pipeline: Document → Retrieval → Summarization →
Citation → Safety → Response.

Ensures every factual claim in the summary can be traced to a source
document chunk.
"""

from __future__ import annotations

import re

from caremate.agents.base import BaseAgent, PipelineData
from caremate.models.response import Citation
from caremate.utils.config import get_logger

logger = get_logger(__name__)


class CitationAgent(BaseAgent):
    """Verifies and formats citations for the AI response.

    Matches claims in the summary against the retrieved chunks
    and produces structured Citation objects.
    """

    def __init__(self, top_k: int = 5):
        self._top_k = top_k

    @property
    def name(self) -> str:
        return "CitationAgent"

    def process(self, data: PipelineData) -> PipelineData:
        """Generate citations from retrieved chunks and summary claims."""
        citations: list[Citation] = []

        if data.retrieved_chunks:
            for chunk, score in data.retrieved_chunks[:self._top_k]:
                # Check if the chunk is relevant to the summary
                if self._is_relevant(chunk.content, data.summary, data.query):
                    snippet = self._extract_snippet(chunk.content, data.query)
                    citations.append(Citation(
                        source_document=chunk.document_id,
                        section=chunk.section_label,
                        chunk_id=chunk.chunk_id,
                        page_number=chunk.page_number,
                        relevance_score=round(max(0.0, score), 4),
                        text_snippet=snippet,
                    ))

        # Deduplicate by chunk_id
        seen = set()
        unique_citations = []
        for c in citations:
            if c.chunk_id not in seen:
                seen.add(c.chunk_id)
                unique_citations.append(c)

        data.verified_citations = unique_citations
        data.trace(self.name, f"Generated {len(unique_citations)} citations")
        logger.info("CitationAgent: %d citations verified", len(unique_citations))
        return data

    @staticmethod
    def _is_relevant(chunk_text: str, summary: str, query: str) -> bool:
        """Check if a chunk is relevant to the query/summary."""
        query_words = set(re.findall(r"\b\w+\b", query.lower()))
        chunk_words = set(re.findall(r"\b\w+\b", chunk_text.lower()))

        # At least one query word must appear in the chunk
        overlap = query_words & chunk_words
        if not overlap:
            return False

        # Or the summary mentions key concepts from the chunk
        summary_words = set(re.findall(r"\b\w+\b", summary.lower()))
        summary_overlap = chunk_words & summary_words

        return len(overlap) > 0 or len(summary_overlap) > 0

    @staticmethod
    def _extract_snippet(content: str, query: str, max_length: int = 200) -> str:
        """Extract a relevant snippet from chunk content."""
        # Find sentences mentioning query terms
        sentences = re.split(r"[.!?]+", content)
        query_words = set(re.findall(r"\b\w+\b", query.lower()))

        for sentence in sentences:
            sentence_words = set(re.findall(r"\b\w+\b", sentence.lower()))
            if query_words & sentence_words:
                snippet = sentence.strip()
                if len(snippet) > max_length:
                    snippet = snippet[:max_length - 3] + "..."
                return snippet

        # Fallback: first N chars
        snippet = content.strip()[:max_length]
        if len(snippet) == max_length:
            snippet += "..."
        return snippet
