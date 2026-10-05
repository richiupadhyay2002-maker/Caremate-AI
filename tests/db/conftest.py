"""Shared fixtures for Phase 2 database tests.

These fixtures provide a **real SQLite database** (file-based, fresh per
session) with all 17 tables created via ``init_db``.  The
:class:`~caremate.db.vector_store.PgVectorStore` is backed by this database,
so the patient-isolation invariants are tested against the actual persistence
layer — not the in-memory FAISS store.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from caremate.db.config import init_db
from caremate.db.session import get_engine
from caremate.db.vector_store import PgVectorStore
from caremate.providers.mock import MockEmbeddingProvider


@pytest.fixture(scope="session")
def _db_url(tmp_path_factory):
    """A file-based SQLite URL unique to this test session."""
    db_path = tmp_path_factory.mktemp("db") / "test_caremate.db"
    return f"sqlite:///{db_path}"


@pytest.fixture(scope="session")
def engine(_db_url):
    """A session-scoped engine + initialised DB schema."""
    # Clear lru_cache so get_engine picks up our test URL
    get_engine.cache_clear()
    from caremate.utils.config import get_settings
    get_settings.cache_clear()
    os.environ["CAREMATE_DATABASE_URL"] = str(_db_url)
    eng = init_db(db_url=str(_db_url), drop_all=True)
    return eng


@pytest.fixture()
def db_session(engine):
    """A transactional session for a single test (rolled back after)."""
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def pg_vector_store(db_session):
    """A PgVectorStore backed by the real test database."""
    return PgVectorStore(session=db_session, dim=384)


@pytest.fixture()
def db_embedding_provider():
    return MockEmbeddingProvider(dim=384)
