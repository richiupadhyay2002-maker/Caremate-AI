"""Tests for citation verification — every AI output must be traceable to sources."""

import pytest

from caremate.agents.citation_agent import CitationAgent
from caremate.agents.base import PipelineData
from caremate.models.document import DocumentChunk
from caremate.models.response import Citation


@pytest.fixture
def chunks_with_content(mock_embedding_provider):
    """Chunks with realistic medical content for citation testing."""
    emb = mock_embedding_provider
    return [
        DocumentChunk(
            chunk_id="c1", document_id="doc_1", patient_id="pat_1",
            section_label="medications",
            content="The patient is on lisinopril 10mg daily for hypertension.",
            embedding=emb.embed("lisinopril hypertension medications")),
        DocumentChunk(
            chunk_id="c2", document_id="doc_1", patient_id="pat_1",
            section_label="dietary_instructions",
            content="Limit sodium to less than 2000 mg per day. Avoid cranberry juice.",
            embedding=emb.embed("sodium restriction dietary instructions")),
        DocumentChunk(
            chunk_id="c3", document_id="doc_2", patient_id="pat_1",
            section_label="nutritional_assessment",
            content="Malnutrition risk is elevated. Recommend high-protein diet.",
            embedding=emb.embed("malnutrition protein diet")),
    ]


def test_citations_traceable_to_sources(chunks_with_content):
    """Every citation must reference a real document and chunk."""
    agent = CitationAgent(top_k=5)
    data = PipelineData(query="What medications is the patient on?", patient=None)
    data.chunks = chunks_with_content
    data.retrieved_chunks = [(c, 0.9) for c in chunks_with_content]
    data.summary = "The patient is on lisinopril for hypertension."

    result = agent.process(data)
    assert len(result.verified_citations) > 0
    for citation in result.verified_citations:
        assert isinstance(citation, Citation)
        assert citation.source_document in ("doc_1", "doc_2")
        assert citation.chunk_id in ("c1", "c2", "c3")
        assert citation.text_snippet
        assert 0.0 <= citation.relevance_score <= 1.0


def test_no_citations_when_no_retrieval():
    """Empty retrieval produces no citations."""
    agent = CitationAgent()
    data = PipelineData(query="test question", patient=None)
    result = agent.process(data)
    assert len(result.verified_citations) == 0


def test_citations_contain_section_labels(chunks_with_content):
    """Citations include the section label from the source chunk."""
    agent = CitationAgent(top_k=5)
    data = PipelineData(query="What are the dietary instructions?", patient=None)
    data.chunks = chunks_with_content
    data.retrieved_chunks = [(c, 0.85) for c in chunks_with_content]
    data.summary = "The patient should limit sodium and avoid cranberry juice."

    result = agent.process(data)
    assert len(result.verified_citations) > 0
    sections = [c.section for c in result.verified_citations]
    assert "dietary_instructions" in sections or "medications" in sections


def test_citations_deduplicated(chunks_with_content):
    """Duplicate chunk references are deduplicated."""
    agent = CitationAgent(top_k=5)
    data = PipelineData(query="medications diet sodium", patient=None)
    data.chunks = chunks_with_content
    # Pass same chunks twice
    data.retrieved_chunks = [(c, 0.9) for c in chunks_with_content] + \
                            [(c, 0.9) for c in chunks_with_content]
    data.summary = "The patient is on lisinopril and should limit sodium."

    result = agent.process(data)
    chunk_ids = [c.chunk_id for c in result.verified_citations]
    assert len(chunk_ids) == len(set(chunk_ids))  # no duplicates
