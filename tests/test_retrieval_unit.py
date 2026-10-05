"""Comprehensive unit tests for caremate.retrieval (embeddings + vector store).

Covers:
- EmbeddingManager: caching, batch behavior, LRU trimming, delegation
- PatientIsolatedVectorStore: isolation, add/search validation, edge cases

These complement the existing isolation tests with focused unit coverage.
"""

import pytest

from caremate.models.document import DocumentChunk
from caremate.providers.mock import MockEmbeddingProvider
from caremate.retrieval.embeddings import EmbeddingManager
from caremate.retrieval.vector_store import PatientIsolatedVectorStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class CountingProvider(MockEmbeddingProvider):
    """Mock provider that counts how many times it actually embeds."""

    def __init__(self, dim=32):
        super().__init__(dim=dim)
        self.embed_calls = 0
        self.batch_calls = 0

    def embed(self, text):
        self.embed_calls += 1
        return super().embed(text)

    def embed_batch(self, texts):
        self.batch_calls += 1
        return super().embed_batch(texts)


@pytest.fixture
def provider():
    return CountingProvider(dim=32)


@pytest.fixture
def manager(provider):
    return EmbeddingManager(provider)


def make_chunk(patient_id="p1", embedding=None, content="some clinical text", dim=4):
    emb = embedding if embedding is not None else [1.0] + [0.0] * (dim - 1)
    return DocumentChunk(
        chunk_id=f"{patient_id}_c{hash(content) & 0xFFFF}",
        document_id="doc1",
        patient_id=patient_id,
        content=content,
        embedding=emb,
    )


# ---------------------------------------------------------------------------
# EmbeddingManager — positive
# ---------------------------------------------------------------------------

class TestEmbeddingManagerPositive:
    def test_embed_returns_vector(self, manager):
        vec = manager.embed("hello")
        assert len(vec) == 32

    def test_provider_delegation(self, manager, provider):
        manager.embed("hello")
        assert provider.embed_calls == 1

    def test_cached_second_call_skips_provider(self, manager, provider):
        manager.embed("hello")
        manager.embed("hello")
        assert provider.embed_calls == 1

    def test_different_texts_each_embedded(self, manager, provider):
        manager.embed("a")
        manager.embed("b")
        assert provider.embed_calls == 2

    def test_whitespace_variants_share_cache(self, manager, provider):
        manager.embed("hello")
        manager.embed("  hello  ")
        assert provider.embed_calls == 1

    def test_batch_all_uncached(self, manager, provider):
        vecs = manager.embed_batch(["a", "b", "c"])
        assert len(vecs) == 3
        assert provider.batch_calls == 1
        assert provider.embed_calls == 0  # batch path used

    def test_batch_partial_cache_hit(self, manager, provider):
        manager.embed("a")
        vecs = manager.embed_batch(["a", "b"])
        assert vecs[0] == manager.embed("a")
        assert vecs[1] == manager.embed("b")

    def test_batch_fully_cached_no_provider_call(self, manager, provider):
        manager.embed_batch(["a", "b"])
        calls_before = provider.batch_calls
        manager.embed_batch(["a", "b"])
        assert provider.batch_calls == calls_before

    def test_properties(self, manager, provider):
        assert manager.provider is provider
        assert manager.name == "mock"
        assert manager.dimension == 32

    def test_close_delegates(self, provider):
        class Closing(CountingProvider):
            closed = False

            def close(self):
                self.closed = True

        p = Closing()
        m = EmbeddingManager(p)
        m.close()
        assert p.closed is True


# ---------------------------------------------------------------------------
# EmbeddingManager — edge cases
# ---------------------------------------------------------------------------

class TestEmbeddingManagerEdgeCases:
    def test_cache_key_truncated_at_500_chars(self, manager, provider):
        long_text = "x" * 1000
        manager.embed(long_text)
        manager.embed("x" * 500 + "different tail")
        # Both share the same truncated cache key
        assert provider.embed_calls == 1

    def test_cache_trim_evicts_oldest(self, provider):
        manager = EmbeddingManager(provider)
        manager._max_cache_size = 2
        manager.embed("a")
        manager.embed("b")
        manager.embed("c")  # 'a' evicted
        manager.embed("a")  # must re-embed
        assert provider.embed_calls == 4

    def test_empty_text(self, manager, provider):
        vec = manager.embed("")
        assert len(vec) == 32
        assert provider.embed_calls == 1

    def test_batch_with_empty_list(self, manager, provider):
        assert manager.embed_batch([]) == []
        assert provider.batch_calls == 0


# ---------------------------------------------------------------------------
# PatientIsolatedVectorStore — positive
# ---------------------------------------------------------------------------

class TestVectorStorePositive:
    def test_add_and_search_returns_own_chunk(self):
        store = PatientIsolatedVectorStore(dim=4)
        chunk = make_chunk("p1", embedding=[1.0, 0.0, 0.0, 0.0])
        store.add_chunk(chunk)
        results = store.search([1.0, 0.0, 0.0, 0.0], patient_id="p1")
        assert len(results) == 1
        assert results[0][0].patient_id == "p1"
        assert results[0][1] > 0.9

    def test_isolation_between_patients(self):
        store = PatientIsolatedVectorStore(dim=4)
        store.add_chunk(make_chunk("p1", embedding=[1.0, 0.0, 0.0, 0.0]))
        assert store.search([1.0, 0.0, 0.0, 0.0], patient_id="p2") == []

    def test_add_chunks_batch(self):
        store = PatientIsolatedVectorStore(dim=4)
        ids = store.add_chunks([
            make_chunk("p1", embedding=[1.0, 0, 0, 0]),
            make_chunk("p2", embedding=[0, 1.0, 0, 0]),
        ])
        assert ids == [0, 1]
        assert store.total_chunks == 2
        assert set(store.patients) == {"p1", "p2"}

    def test_search_respects_k(self):
        store = PatientIsolatedVectorStore(dim=2)
        for i in range(5):
            store.add_chunk(make_chunk("p1", embedding=[1.0, 0.0], content=f"v{i}"))
        results = store.search([1.0, 0.0], patient_id="p1", k=2)
        assert len(results) == 2

    def test_results_sorted_by_score_desc(self):
        store = PatientIsolatedVectorStore(dim=2)
        store.add_chunk(make_chunk("p1", embedding=[1.0, 0.0], content="close"))
        store.add_chunk(make_chunk("p1", embedding=[0.0, 1.0], content="far"))
        results = store.search([1.0, 0.0], patient_id="p1")
        assert results[0][0].content == "close"
        assert results[0][1] >= results[1][1]

    def test_search_by_text(self):
        store = PatientIsolatedVectorStore(dim=32)
        provider = MockEmbeddingProvider(dim=32)
        text = "patient reports mild headache"
        chunk = make_chunk("p1", embedding=provider.embed(text), content=text)
        store.add_chunk(chunk)
        results = store.search_by_text(text, patient_id="p1", embedding_provider=provider)
        assert len(results) == 1
        assert results[0][0].content == text

    def test_get_patient_chunks(self):
        store = PatientIsolatedVectorStore(dim=4)
        store.add_chunk(make_chunk("p1"))
        store.add_chunk(make_chunk("p1", content="second"))
        store.add_chunk(make_chunk("p2"))
        assert len(store.get_patient_chunks("p1")) == 2
        assert len(store.get_patient_chunks("p2")) == 1

    def test_has_patient(self):
        store = PatientIsolatedVectorStore(dim=4)
        assert store.has_patient("p1") is False
        store.add_chunk(make_chunk("p1"))
        assert store.has_patient("p1") is True
        assert store.has_patient("p99") is False

    def test_remove_patient(self):
        store = PatientIsolatedVectorStore(dim=4)
        store.add_chunk(make_chunk("p1"))
        store.add_chunk(make_chunk("p2"))
        count = store.remove_patient("p1")
        assert count == 1
        assert store.has_patient("p1") is False
        assert store.total_chunks == 1

    def test_remove_unknown_patient_returns_zero(self):
        store = PatientIsolatedVectorStore(dim=4)
        assert store.remove_patient("ghost") == 0

    def test_clear(self):
        store = PatientIsolatedVectorStore(dim=4)
        store.add_chunk(make_chunk("p1"))
        store.clear()
        assert store.total_chunks == 0
        assert store.patients == []
        assert store.has_patient("p1") is False

    def test_dimension_property(self):
        assert PatientIsolatedVectorStore(dim=7).dimension == 7


# ---------------------------------------------------------------------------
# PatientIsolatedVectorStore — negative / edge
# ---------------------------------------------------------------------------

class TestVectorStoreNegative:
    def test_missing_patient_id_raises(self):
        store = PatientIsolatedVectorStore(dim=4)
        chunk = make_chunk("p1")
        chunk.patient_id = ""
        with pytest.raises(ValueError, match="patient_id"):
            store.add_chunk(chunk)

    def test_missing_embedding_raises(self):
        store = PatientIsolatedVectorStore(dim=4)
        chunk = DocumentChunk(
            chunk_id="c1", document_id="d1", patient_id="p1",
            content="text", embedding=None,
        )
        with pytest.raises(ValueError, match="embedding"):
            store.add_chunk(chunk)

    def test_search_empty_store_returns_empty(self):
        store = PatientIsolatedVectorStore(dim=4)
        assert store.search([1.0, 0.0, 0.0, 0.0], patient_id="p1") == []

    def test_search_zero_vector_does_not_crash(self):
        store = PatientIsolatedVectorStore(dim=4)
        store.add_chunk(make_chunk("p1", embedding=[1.0, 0, 0, 0]))
        results = store.search([0.0, 0.0, 0.0, 0.0], patient_id="p1")
        # FAISS handles zero vectors gracefully (scores 0), no crash
        assert isinstance(results, list)

    def test_get_patient_chunks_unknown_patient(self):
        store = PatientIsolatedVectorStore(dim=4)
        assert store.get_patient_chunks("nobody") == []

    def test_search_k_zero(self):
        store = PatientIsolatedVectorStore(dim=4)
        store.add_chunk(make_chunk("p1"))
        assert store.search([1.0, 0, 0, 0], patient_id="p1", k=0) == []
