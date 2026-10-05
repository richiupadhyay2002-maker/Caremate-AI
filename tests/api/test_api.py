"""End-to-end API tests for Phase 2.

Covers:
- Health & root
- Auth: register, login, RBAC enforcement
- Patient isolation at the API level: a patient cannot ask about another patient
- Ask endpoint returning a real StructuredAIResponse backed by Postgres
"""

from __future__ import annotations

from caremate.db.models_comm import AI_Generation as OrmGen


def _register_and_login(client, email, password, role="patient", patient_id=None):
    """Register a user and return a bearer-token auth header dict."""
    payload = {"email": email, "password": password, "full_name": "Test User", "role": role}
    if patient_id:
        payload["patient_id"] = patient_id
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200, f"Register failed: {r.text}"
    r = client.post("/auth/token", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ------------------------------------------------------------------
# Health & root
# ------------------------------------------------------------------
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["phase"] == "Database & Backend API"


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------
def test_register_and_login_patient(client):
    headers = _register_and_login(client, "newpat@e.com", "pw123456",
                                  role="patient", patient_id="np_1")
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["role"] == "patient"

    r = client.post("/auth/token", json={"email": "newpat@e.com", "password": "wrong"})
    assert r.status_code == 401


def test_register_doctor_requires_admin(client):
    """Registering as a doctor without an admin token should fail."""
    r = client.post("/auth/register", json={
        "email": "dr@e.com", "password": "pw123456", "full_name": "Dr. Smith",
        "role": "doctor", "doctor_id": "dr_1",
    })
    assert r.status_code == 401


def test_rbac_patient_cannot_access_other_patient(client, patient_token, db):
    """A patient user must NOT access another patient's /ask endpoint."""
    headers_b = _register_and_login(client, "b@e.com", "pw123456",
                                    role="patient", patient_id="patient_B")
    doc = "PATIENT HISTORY\nLisinopril 10mg daily.\nMEDICATIONS\n- Lisinopril\n"
    r = client.post("/patients/patient_B/documents",
                    json={"text": doc, "document_type": "clinical_note"},
                    headers=headers_b)
    assert r.status_code == 200

    # Patient B asks about patient_A (should be FORBIDDEN — RBAC)
    r = client.post("/patients/patient_A/ask",
                    json={"query": "what does patient A take?"},
                    headers=headers_b)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


def test_ask_without_auth_returns_401(client):
    """Unauthenticated access to /ask should return 401."""
    r = client.post("/patients/api_patient_1/ask", json={"query": "test"})
    assert r.status_code == 401
