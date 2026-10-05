"""Declarative base and the polymorphic ``Vector`` column type.

The ``Vector`` type uses real ``pgvector`` storage on PostgreSQL and falls back
to a ``JSON`` column (list of floats) on SQLite.  This lets the *same* models
and the *same* test-suite run against a lightweight SQLite database in CI and
a production PostgreSQL + pgvector instance in deployment without any code
changes.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Index
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    """Declarative base for all Caremate ORM models."""

    # Every concrete model sets __tablename__; nothing needed here.


# ------------------------------------------------------------------
# Vector column type — pgvector on Postgres, JSON on SQLite
# ------------------------------------------------------------------
try:  # pragma: no cover - exercised only against Postgres
    from pgvector.sqlalchemy import Vector as _PGVector  # type: ignore

    _HAS_PGVECTOR = True
except Exception:  # pragma: no cover - fallback when pgvector not installed
    _HAS_PGVECTOR = False


class Vector(TypeDecorator):  # NOTE: TypeDecorator, NOT a mapped model
    """A vector column type that transparently supports both Postgres and SQLite.

    On PostgreSQL this maps to ``pgvector``'s native ``vector(dim)`` type with
    an HNSW index available.  On SQLite (used by the test-suite) it stores the
    embedding as a JSON list of floats so queries remain executable.

    Usage::

        embedding = Column(Vector(384), nullable=False)
    """

    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 384, **kwargs: Any):
        super().__init__(**kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect.name == "postgresql" and _HAS_PGVECTOR:
            return dialect.type_descriptor(_PGVector(self.dim))
        return dialect.type_descriptor(JSON())

    def copy(self, *args: Any, **kwargs: Any):  # type: ignore[override]
        return Vector(self.dim)


# Index helper used by models that own a vector column.
def hnsw_index(table_name: str, column: str, m: int = 16, ef: int = 100) -> Index:
    """Return an HNSW index spec (Postgres-only at DDL time; ignored on SQLite)."""
    return Index(
        f"idx_{table_name}_{column}_hnsw",
        name=f"idx_{table_name}_{column}_hnsw",
        postgresql_using="hnsw",
        postgresql_where=None,
        m=m,
        ef=ef,
    )