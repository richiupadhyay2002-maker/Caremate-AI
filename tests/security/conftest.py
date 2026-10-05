"""Shared fixtures for Phase 5 security & privacy tests."""

from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from caremate.api.main import app
from caremate.db.config import init_db, get_engine
from caremate.db.session import get_session_factory
from caremate.utils.config import get_settings

# Use a dedicated test DB so we don't clobber real data
_TEST_DB = "sqlite:///caremate_test_security.db"
os.environ["CAREMMATE_DATABASE_URL"] = _TEST_DB
get_engine.cache_clear()
get_settings.cache_clear()
init_db(db_url=_TEST_DB, drop_all=True)

from caremate.db.models_patients import Patient as OrmPatient, Doctor as OrmDoctor, PatientDoctorRelationship  # noqa: E402
from caremate.db.models_core import User, Organization  # noqa: E402
from caremate.db.models_docs import MedicalDocument, DocumentChunk  # noqa: E402
from caremate.db.models_comm import AI_Generation, Citation, AuditLog  # noqa: E402
from caremate.db.models_clinical import LabResult, Medication  # noqa: E402
from caremate.api.security import hash_password  # noqa: E402

_all_tables = [
    DocumentChunk, MedicalDocument, AI_Generation, Citation,
    AuditLog, LabResult, Medication, OrmDoctor, PatientDoctorRelationship,
    OrmPatient, User, Organization,
]


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


@pytest.fixture(autouse=True)
def _cleanup(db):
    """Delete all rows between tests so each test starts clean."""
    yield
    for table in _all_tables:
        try:
            db.execute(delete(table))
        except Exception:
            pass
    db.commit()


def _make_user(db, email, password, role="patient", patient_id=None, doctor_id=None):
    """Create a User row and return it (or get existing)."""
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return existing
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name="Test User",
        role=role,
        patient_id=patient_id,
        doctor_id=doctor_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_patient(db, patient_id, full_name="Test Patient"):
    """Create a Patient row and return it (or get existing)."""
    existing = db.query(OrmPatient).filter(OrmPatient.patient_id == patient_id).first()
    if existing:
        return existing
    patient = OrmPatient(
        patient_id=patient_id,
        full_name=full_name,
        age=65,
        sex="male",
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def _login(client, email, password):
    """Log in and return a bearer-token auth header dict."""
    r = client.post("/auth/token", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin_user(db):
    """Create an admin user in the DB."""
    return _make_user(db, "admin@sec.test", "adminpass", role="admin")


@pytest.fixture
def admin_token(client, db):
    """Auth header for an admin user."""
    _make_user(db, "admin@sec.test", "adminpass", role="admin")
    return _login(client, "admin@sec.test", "adminpass")


@pytest.fixture
def patient_user_a(db):
    """Create a patient user for patient_A."""
    patient = _make_patient(db, "patient_A", "Patient A")
    return _make_user(db, "patient_a@sec.test", "pass123", role="patient",
                      patient_id=patient.id)


@pytest.fixture
def patient_token_a(client, db):
    """Auth header for patient_A's user."""
    patient = _make_patient(db, "patient_A", "Patient A")
    _make_user(db, "patient_a@sec.test", "pass123", role="patient",
               patient_id=patient.id)
    return _login(client, "patient_a@sec.test", "pass123")


@pytest.fixture
def patient_token_b(client, db):
    """Auth header for patient_B's user."""
    patient = _make_patient(db, "patient_B", "Patient B")
    _make_user(db, "patient_b@sec.test", "pass456", role="patient",
               patient_id=patient.id)
    return _login(client, "patient_b@sec.test", "pass456")


@pytest.fixture
def doctor_user(db):
    """Create a doctor user assigned to patient_A."""
    from caremate.db.models_patients import Doctor, PatientDoctorRelationship
    patient = _make_patient(db, "patient_A", "Patient A")
    existing_doc = db.query(Doctor).filter(Doctor.doctor_id == "dr_001").first()
    if existing_doc:
        doctor = existing_doc
    else:
        doctor = Doctor(doctor_id="dr_001", full_name="Dr. Smith")
        db.add(doctor)
        db.commit()
    user = _make_user(db, "doctor@sec.test", "docpass", role="doctor",
                      doctor_id=doctor.id)
    rel = db.query(PatientDoctorRelationship).filter_by(
        patient_id=patient.id, doctor_id=doctor.id
    ).first()
    if rel is None:
        rel = PatientDoctorRelationship(patient_id=patient.id, doctor_id=doctor.id)
        db.add(rel)
        db.commit()
    return user


@pytest.fixture
def doctor_token(client, db):
    """Auth header for a doctor user (not assigned to patient_B)."""
    from caremate.db.models_patients import Doctor, PatientDoctorRelationship
    patient_a = _make_patient(db, "patient_A", "Patient A")
    existing_doc = db.query(Doctor).filter(Doctor.doctor_id == "dr_001").first()
    if existing_doc:
        doctor = existing_doc
    else:
        doctor = Doctor(doctor_id="dr_001", full_name="Dr. Smith")
        db.add(doctor)
        db.commit()
    user = _make_user(db, "doctor@sec.test", "docpass", role="doctor",
                      doctor_id=doctor.id)
    rel = db.query(PatientDoctorRelationship).filter_by(
        patient_id=patient_a.id, doctor_id=doctor.id
    ).first()
    if rel is None:
        rel = PatientDoctorRelationship(patient_id=patient_a.id, doctor_id=doctor.id)
        db.add(rel)
        db.commit()
    return _login(client, "doctor@sec.test", "docpass")
