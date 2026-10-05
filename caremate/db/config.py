"""Database configuration — engine creation, URL parsing, and pgvector setup.

The database URL is read from the ``CAREMMATE_DATABASE_URL`` environment
variable (with ``postgresql+psycopg://...``) or a SQLite fallback for local
development/testing.
"""

from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from caremate.db.base import Base
# Importing the models package registers every ORM class on Base.metadata
# before create_all() is called — otherwise FK targets are unknown.
from caremate.db import models as _models  # noqa: F401  (registers all tables)
from caremate.utils.config import get_logger

logger = get_logger(__name__)

# ------------------------------------------------------------------
# Database URL
# ------------------------------------------------------------------
def _get_database_url() -> str:
    """Return the SQLAlchemy database URL.

    Priority:
      1. ``CAREMMATE_DATABASE_URL`` env var (explicit).
      2. ``DATABASE_URL`` env var (common convention).
      3. SQLite file at ``./caremate.db`` (zero-config dev/test).
    """
    url = os.environ.get("CAREMMATE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if url:
        return url.strip()
    # SQLite fallback — works for tests without any external service
    return "sqlite:///caremate.db"


def _is_postgres(url: str) -> bool:
    return url.startswith(("postgresql://", "postgresql+psycopg://", "postgresql+asyncpg://"))


@lru_cache(maxsize=1)
def get_engine(db_url: str | None = None) -> Engine:
    """Create (and cache) a SQLAlchemy engine for the given URL.

    For SQLite we use ``NullPool`` so that file-based test databases are
    isolated per-connection — important for parallel test execution.
    """
    url = db_url or _get_database_url()
    is_sqlite = url.startswith("sqlite")

    connect_args: dict = {}
    poolclass = NullPool if is_sqlite else None

    if is_sqlite:
        connect_args["check_same_thread"] = False

    engine = create_engine(
        url,
        echo=False,
        poolclass=poolclass,
        connect_args=connect_args,
        future=True,
    )

    # Ensure pgvector extension exists on PostgreSQL
    if _is_postgres(url):
        @event.listens_for(engine, "connect")
        def _enable_pgvector(conn, _record):  # type: ignore[no-redef]
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    logger.info("Database engine created for %s", "postgresql" if _is_postgres(url) else "sqlite")
    return engine


def init_db(db_url: str | None = None, drop_all: bool = False) -> Engine:
    """Create all tables (and indexes) in the database.

    Args:
        db_url: Optional override of the database URL.
        drop_all: If True, drop existing tables first (use in tests).
    """
    engine = get_engine(db_url)
    if drop_all:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    if _is_postgres(db_url or _get_database_url()):
        # Create HNSW indexes for vector columns (Postgres-specific)
        _create_pgvector_indexes(engine)

    logger.info("Database initialised (drop_all=%s)", drop_all)
    return engine


def _create_pgvector_indexes(engine: Engine) -> None:
    """Create HNSW indexes on vector columns (Postgres-only)."""
    indexes = [
        ("document_chunks", "embedding"),
    ]
    with engine.begin() as conn:
        for table, column in indexes:
            try:
                conn.execute(text(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_{column}_hnsw "
                    f"ON {table} USING hnsw ({column} vector_l2_ops) "
                    f"WITH (m=16, ef=100);"
                ))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not create HNSW index on %s.%s: %s", table, column, exc)