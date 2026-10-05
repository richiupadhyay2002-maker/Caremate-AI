"""Shared fixtures for Phase 2 API integration tests.

Uses a single file-based SQLite database (``caremate_test_api.db``) that is
initialised once at import time.  Between tests, all rows are deleted so each
test starts with a clean slate while preserving the schema.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from caremate.api.main import app
# Clear any cached engine so we use our test database
from caremate.db.config import init_db, get_engine
from caremate.utils.config import get_settings

# Use a dedicated test DB file to avoid clobbering dev data
_TEST_DB = "sqlite:///caremate_test_api.db"
os.environ["CAREMATE_DATABASE_URL"] = _TEST_DB
get_engine.cache_clear()
get_settings.cache_clear()
init_db(db_url=_TEST_DB, drop_all=True)

from caremate.db.models_patients import Patient as OrmPatient  # noqa: E402
from caremate.db.models_core import User, Organization  # noqa: E402
from caremate.db.models_docs import MedicalDocument, DocumentChunk  # noqa: E402
from caremate.db.models_comm import AI_Generation, Citation  # noqa: E402
from caremate.db.session import get_session_factory  # noqa: E402

_tables = [DocumentChunk, MedicalDocument, AI_Generation, Citation,
           OrmPatient, User, Organization]


@pytest.fixture
def client():
    """A TestClient that triggers lifespan (DB init) events."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    """Yield a DB session for direct assertions / setup."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def _register_and_login(client, email, password, role="patient",
                        patient_id=None):
    """Register a user and return a bearer-token auth header dict."""
    payload = {"email": email, "password": password,
               "full_name": "Test User", "role": role}
    if patient_id:
        payload["patient_id"] = patient_id
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200, f"Register failed: {r.text}"
    r = client.post("/auth/token", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def patient_token(client):
    """Auth header for a patient user with patient_id 'api_patient_1'."""
    return _register_and_login(client, "patient_api@e.com", "secret123",
                               role="patient", patient_id="api_patient_1")


@pytest.fixture
def admin_token(client, db):
    """Auth header for an admin user."""
    from caremate.api.security import hash_password
    admin = User(email="admin@e.com", hashed_password=hash_password("adminpass"),
                 full_name="Admin", role="admin")
    db.add(admin)
    db.commit()
    r = client.post("/auth/token", json={"email": "admin@e.com", "password": "adminpass"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _cleanup(db):
    """Delete all rows between tests so each test starts clean."""
    yield
    for table in _tables:
        db.execute(delete(table))
    db.commit()
