"""Patient-isolation tests against the real PostgreSQL/SQLite database.

These are the *Phase 2* counterparts of ``tests/test_patient_isolation.py``.
Instead of an in-memory FAISS store, they exercise the
:class:`~caremate.db.vector_store.PgVectorStore` backed by a real SQLite
database, ensuring that the SQL-level ``WHERE patient_id = ?`` isolation
holds at the persistence layer.
"""

import pytest

from caremate.db.models_patients import Patient as OrmPatient
from caremate.db.models_docs import DocumentChunk as OrmChunk


# ------------------------------------------------------------------
# Helper: persist a patient + chunks directly through the ORM
# ------------------------------------------------------------------
def _add_patient(session, patient_id: str) -> OrmPatient:
    orm = OrmPatient(patient_id=patient_id, full_name=f"Patient {patient_id}")
    session.add(orm)
    session.flush()
    return orm


def _add_chunk(session, patient_orm: OrmPatient, chunk_id: str,
               content: str, embedding: list[float]):
    chunk = OrmChunk(
        chunk_id=chunk_id,
        patient_id=patient_orm.id,
        document_id=1,  # placeholder doc FK id
        section_label="medications",
        content=content,
        token_count=len(content.split()),
        embedding=embedding,
        metadata_json={},
    )
    session.add(chunk)
    session.flush()
    return chunk


def test_no_cross_patient_leakage_db(pg_vector_store, db_session, db_embedding_provider):
    """Chunks from patient A must never appear in patient B's search results."""
    emb = db_embedding_provider

    pat_a = _add_patient(db_session, "patient_A")
    pat_b = _add_patient(db_session, "patient_B")

    _add_chunk(db_session, pat_a, "chunk_a_1",
               "The patient is on lisinopril and warfarin.",
               emb.embed("lisinopril warfarin medication"))
    _add_chunk(db_session, pat_b, "chunk_b_1",
               "The patient is on metformin and atorvastatin.",
               emb.embed("metformin atorvastatin medication"))
    db_session.commit()

    results_a = pg_vector_store.search(emb.embed("lisinopril warfarin"), patient_id="patient_A")
    assert len(results_a) > 0
    for chunk, _ in results_a:
        assert chunk.patient_id == "patient_A"

    results_b = pg_vector_store.search(emb.embed("metformin atorvastatin"), patient_id="patient_B")
    assert len(results_b) > 0
    for chunk, _ in results_b:
        assert chunk.patient_id == "patient_B"

    # Patient A's search must NOT contain patient B's chunks
    chunk_ids_a = [c.chunk_id for c, _ in results_a]
    assert "chunk_b_1" not in chunk_ids_a


def test_patient_specific_search_returns_only_own_chunks_db(pg_vector_store, db_session, db_embedding_provider):
    """Searching with a patient_id returns only that patient's chunks."""
    emb = db_embedding_provider

    pat_a = _add_patient(db_session, "patient_A")
    pat_b = _add_patient(db_session, "patient_B")

    for i in range(5):
        _add_chunk(db_session, pat_a, f"a_{i}",
                   f"Dietary instruction {i} about sodium restriction.",
                   emb.embed(f"sodium dietary instruction {i}"))
    for i in range(3):
        _add_chunk(db_session, pat_b, f"b_{i}",
                   f"Dietary instruction {i} about sugar restriction.",
                   emb.embed(f"sugar dietary instruction {i}"))
    db_session.commit()

    results = pg_vector_store.search(emb.embed("sodium"), patient_id="patient_A", k=10)
    assert len(results) == 5
    assert all(c.patient_id == "patient_A" for c, _ in results)


def test_empty_patient_returns_empty_db(pg_vector_store, db_embedding_provider):
    """Searching for a patient with no chunks returns an empty list."""
    emb = db_embedding_provider
    results = pg_vector_store.search(emb.embed("test query"), patient_id="nonexistent")
    assert results == []


def test_add_chunk_requires_patient_id_db(pg_vector_store, db_embedding_provider):
    """Adding a chunk without a patient_id should raise an error."""
    from caremate.models.document import DocumentChunk
    chunk = DocumentChunk(
        chunk_id="no_patient", document_id="doc_x", patient_id="",
        section_label="note", content="Some content",
        embedding=db_embedding_provider.embed("Some content"),
    )
    with pytest.raises(ValueError, match="patient_id"):
        pg_vector_store.add_chunk(chunk)


def test_remove_patient_clears_data_db(pg_vector_store, db_session, db_embedding_provider):
    """Removing a patient's data makes their chunks inaccessible."""
    emb = db_embedding_provider
    pat = _add_patient(db_session, "patient_X")
    _add_chunk(db_session, pat, "x1", "content X", emb.embed("content X"))
    db_session.commit()

    assert pg_vector_store.has_patient("patient_X")
    removed = pg_vector_store.remove_patient("patient_X")
    assert removed == 1
    assert not pg_vector_store.has_patient("patient_X")
    assert pg_vector_store.get_patient_chunks("patient_X") == []


def test_patient_data_survives_across_queries_db(pg_vector_store, db_session, db_embedding_provider):
    """Data persisted in one session is visible in subsequent queries."""
    emb = db_embedding_provider
    pat = _add_patient(db_session, "patient_persist")
    _add_chunk(db_session, pat, "persist_1",
               "The patient takes aspirin daily.",
               emb.embed("aspirin daily medication"))
    db_session.commit()

    # New store instance sharing the same DB file (session-scoped engine)
    results = pg_vector_store.search(emb.embed("aspirin"), patient_id="patient_persist")
    assert len(results) == 1
    assert "aspirin" in results[0][0].content
