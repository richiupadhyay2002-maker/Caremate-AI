"""Tests for patient isolation in the vector store and retriever."""

import pytest

from caremate.models.document import DocumentChunk
from caremate.providers.mock import MockEmbeddingProvider


def test_no_cross_patient_leakage(vector_store, mock_embedding_provider):
    """Chunks from patient A must never appear in patient B's search results."""
    emb = mock_embedding_provider

    # Add chunks for patient A
    chunk_a = DocumentChunk(
        chunk_id="chunk_a_1",
        document_id="doc_a",
        patient_id="patient_A",
        section_label="medications",
        content="The patient is on lisinopril and warfarin.",
        embedding=emb.embed("lisinopril warfarin medication"),
    )
    vector_store.add_chunk(chunk_a)

    # Add chunks for patient B
    chunk_b = DocumentChunk(
        chunk_id="chunk_b_1",
        document_id="doc_b",
        patient_id="patient_B",
        section_label="medications",
        content="The patient is on metformin and atorvastatin.",
        embedding=emb.embed("metformin atorvastatin medication"),
    )
    vector_store.add_chunk(chunk_b)

    # Search for patient A — should only get patient A's chunks
    results_a = vector_store.search(emb.embed("lisinopril warfarin"), patient_id="patient_A")
    assert len(results_a) > 0
    for chunk, _ in results_a:
        assert chunk.patient_id == "patient_A"

    # Search for patient B — should only get patient B's chunks
    results_b = vector_store.search(emb.embed("metformin atorvastatin"), patient_id="patient_B")
    assert len(results_b) > 0
    for chunk, _ in results_b:
        assert chunk.patient_id == "patient_B"

    # Patient A's search must NOT contain patient B's chunks
    chunk_ids_a = [c.chunk_id for c, _ in results_a]
    assert "chunk_b_1" not in chunk_ids_a


def test_patient_specific_search_returns_only_own_chunks(vector_store, mock_embedding_provider):
    """Searching with a patient_id returns only that patient's chunks."""
    emb = mock_embedding_provider

    for i in range(5):
        chunk = DocumentChunk(
            chunk_id=f"a_{i}",
            document_id="doc_a",
            patient_id="patient_A",
            section_label="dietary",
            content=f"Dietary instruction {i} about sodium restriction.",
            embedding=emb.embed(f"sodium dietary instruction {i}"),
        )
        vector_store.add_chunk(chunk)

    for i in range(3):
        chunk = DocumentChunk(
            chunk_id=f"b_{i}",
            document_id="doc_b",
            patient_id="patient_B",
            section_label="dietary",
            content=f"Dietary instruction {i} about sugar restriction.",
            embedding=emb.embed(f"sugar dietary instruction {i}"),
        )
        vector_store.add_chunk(chunk)

    results = vector_store.search(emb.embed("sodium"), patient_id="patient_A", k=10)
    assert len(results) == 5
    assert all(c.patient_id == "patient_A" for c, _ in results)


def test_empty_patient_returns_empty(vector_store):
    """Searching for a patient with no chunks returns an empty list."""
    emb = MockEmbeddingProvider(dim=384)
    results = vector_store.search(emb.embed("test query"), patient_id="nonexistent")
    assert results == []


def test_add_chunk_requires_patient_id(vector_store, mock_embedding_provider):
    """Adding a chunk without a patient_id should raise an error."""
    chunk = DocumentChunk(
        chunk_id="no_patient",
        document_id="doc_x",
        patient_id="",  # empty — should fail
        section_label="note",
        content="Some content",
        embedding=mock_embedding_provider.embed("Some content"),
    )
    with pytest.raises(ValueError, match="patient_id"):
        vector_store.add_chunk(chunk)


def test_remove_patient_clears_data(vector_store, mock_embedding_provider):
    """Removing a patient's data makes their chunks inaccessible."""
    emb = mock_embedding_provider
    chunk = DocumentChunk(
        chunk_id="a1", document_id="doc_a", patient_id="patient_A",
        section_label="note", content="content A",
        embedding=emb.embed("content A"))
    vector_store.add_chunk(chunk)

    assert vector_store.has_patient("patient_A")
    removed = vector_store.remove_patient("patient_A")
    assert removed == 1
    assert not vector_store.has_patient("patient_A")
    assert vector_store.get_patient_chunks("patient_A") == []
