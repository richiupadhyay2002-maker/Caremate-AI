"""Session management — session factory and FastAPI dependency."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session, sessionmaker

from caremate.db.config import get_engine
from caremate.utils.config import get_logger

logger = get_logger(__name__)


def get_session_factory():
    """Return a ``sessionmaker`` bound to the configured engine.

    ``expire_on_commit=False`` keeps ORM objects usable after commit, which
    the API layer relies on when returning model instances as response models.
    """
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager yielding a transactional session.

    Usage::

        from caremate.db.session import session_scope
        with session_scope() as session:
            session.add(obj)
            # commit happens on exit, rollback on exception
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session.

    Registered as ``Depends(get_db)`` in route handlers.  The session is
    committed on success and rolled back on error, then closed automatically.
    """
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()