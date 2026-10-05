"""Database layer for Caremate AI — SQLAlchemy models, session, and PgVector store.

This package is the persistent home for patient records, medical documents,
document chunks (with pgvector embeddings), and pipeline audit data.
"""

from caremate.db.base import Base
from caremate.db.config import get_engine, init_db
from caremate.utils.config import get_settings as _db_settings
from caremate.db.session import get_db, get_session_factory
from caremate.db.vector_store import PgVectorStore

__all__ = ["Base", "get_engine", "init_db", "get_db", "get_session_factory", "PgVectorStore"]