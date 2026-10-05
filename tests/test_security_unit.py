"""Comprehensive unit tests for caremate.security (audit + signed URLs).

Covers:
- AuditLogger: positive/negative/edge cases with an in-memory SQLite session
- Signed URLs: valid generation, verification, expiry, tampering, edge cases

These complement the existing security suite by focusing on the *unit*
behavior of the audit logger and signed-URL primitives.
"""

import json
import time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from caremate.db.base import Base
from caremate.db.models_comm import AuditLog
from caremate.security.audit import AuditLogger, get_audit_logger
from caremate.security.redaction import redact_phi
from caremate.security.signed_urls import generate_signed_url, verify_signed_url


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def audit(db_session):
    return AuditLogger(db_session)


# ---------------------------------------------------------------------------
# AuditLogger — positive
# ---------------------------------------------------------------------------

class TestAuditLoggerPositive:
    def test_log_persists_entry(self, audit, db_session):
        audit.log(action="test_action", resource_type="document", resource_id="doc-1")
        entry = db_session.query(AuditLog).one()
        assert entry.action == "test_action"
        assert entry.resource_type == "document"
        assert entry.resource_id == "doc-1"

    def test_log_with_user(self, audit, db_session):
        class FakeUser:
            id = 42

        audit.log(action="a", resource_type="r", user=FakeUser())
        entry = db_session.query(AuditLog).one()
        assert entry.actor_user_id == 42

    def test_log_without_user(self, audit, db_session):
        audit.log(action="a", resource_type="r")
        entry = db_session.query(AuditLog).one()
        assert entry.actor_user_id is None

    def test_request_body_serialized_to_json(self, audit, db_session):
        audit.log(action="a", resource_type="r", request_body={"k": "v"})
        entry = db_session.query(AuditLog).one()
        assert json.loads(entry.request_body) == {"k": "v"}

    def test_no_request_body_defaults_to_empty_string(self, audit, db_session):
        audit.log(action="a", resource_type="r")
        entry = db_session.query(AuditLog).one()
        assert entry.request_body == ""

    def test_ip_and_user_agent_recorded(self, audit, db_session):
        audit.log(action="a", resource_type="r",
                  ip_address="10.0.0.1", user_agent="test-agent/1.0")
        entry = db_session.query(AuditLog).one()
        assert entry.ip_address == "10.0.0.1"
        assert entry.user_agent == "test-agent/1.0"

    def test_log_ai_generation(self, audit, db_session):
        audit.log_ai_generation(
            patient_id="p1", query="what is my INR?",
            response_text="Your INR is 2.5", confidence=0.91,
        )
        entry = db_session.query(AuditLog).one()
        assert entry.action == "ai_generation_created"
        assert entry.resource_id == "patient:p1"
        body = json.loads(entry.request_body)
        # "INR" is a lab keyword, so it gets PHI-redacted in the stored preview
        assert body["query_preview"] == "what is my [REDACTED]?"
        assert body["confidence"] == 0.91

    def test_ai_generation_query_is_redacted_and_truncated(self, audit, db_session):
        long_query = ("warfarin 5mg " * 100)
        audit.log_ai_generation(
            patient_id="p1", query=long_query, response_text="x", confidence=0.5,
        )
        entry = db_session.query(AuditLog).one()
        body = json.loads(entry.request_body)
        assert "[REDACTED]" in body["query_preview"]
        assert len(body["query_preview"]) <= 200

    def test_log_document_access(self, audit, db_session):
        audit.log_document_access(document_id="doc-9", patient_id="p1")
        entry = db_session.query(AuditLog).one()
        assert entry.action == "document_accessed"
        assert entry.resource_id == "doc-9"
        assert json.loads(entry.request_body)["patient_id"] == "p1"

    def test_log_doctor_review(self, audit, db_session):
        audit.log_doctor_review(generation_id=7, patient_id="p1", status="approved")
        entry = db_session.query(AuditLog).one()
        assert entry.action == "doctor_review"
        assert entry.resource_id == "7"
        assert json.loads(entry.request_body)["new_status"] == "approved"

    def test_log_data_deletion(self, audit, db_session):
        audit.log_data_deletion(patient_id="p1", deleted_tables=["documents", "chunks"])
        entry = db_session.query(AuditLog).one()
        assert entry.action == "patient_data_deleted"
        assert entry.resource_id == "p1"
        assert "documents" in json.loads(entry.request_body)["deleted_tables"]

    def test_get_audit_logger_factory(self, db_session):
        logger = get_audit_logger(db_session)
        assert isinstance(logger, AuditLogger)


# ---------------------------------------------------------------------------
# AuditLogger — negative / edge
# ---------------------------------------------------------------------------

class TestAuditLoggerNegative:
    def test_db_failure_never_raises(self, audit, db_session, monkeypatch):
        def explode(*a, **k):
            raise RuntimeError("db is down")

        monkeypatch.setattr(db_session, "flush", explode)
        audit.log(action="a", resource_type="r")  # must not raise

    def test_multiple_entries_accumulate(self, audit, db_session):
        for i in range(3):
            audit.log(action=f"a{i}", resource_type="r", resource_id=str(i))
        entries = db_session.query(AuditLog).all()
        assert len(entries) == 3
        assert {e.action for e in entries} == {"a0", "a1", "a2"}

    def test_confidence_is_rounded_to_4_places(self, audit, db_session):
        audit.log_ai_generation(
            patient_id="p", query="q", response_text="r", confidence=0.1234567,
        )
        body = json.loads(db_session.query(AuditLog).one().request_body)
        assert body["confidence"] == round(0.1234567, 4)

    def test_empty_patient_deletion_tables(self, audit, db_session):
        audit.log_data_deletion(patient_id="p", deleted_tables=[])
        body = json.loads(db_session.query(AuditLog).one().request_body)
        assert body["deleted_tables"] == []


# ---------------------------------------------------------------------------
# Signed URLs
# ---------------------------------------------------------------------------

class TestSignedUrls:
    def test_generate_returns_expected_shape(self):
        url = generate_signed_url("doc-1", expires_in=3600)
        assert url.startswith("/download/doc-1?exp=")
        assert "&sig=" in url

    def test_verify_fresh_url(self):
        url = generate_signed_url("doc-1", expires_in=3600)
        params = dict(p.split("=", 1) for p in url.split("?")[1].split("&"))
        assert verify_signed_url("doc-1", int(params["exp"]), params["sig"]) is True

    def test_expired_url_fails(self):
        expired_ts = int(time.time()) - 10
        from caremate.security.signed_urls import _sign
        sig = _sign("doc-1", expired_ts)
        assert verify_signed_url("doc-1", expired_ts, sig) is False

    def test_tampered_document_id_fails(self):
        url = generate_signed_url("doc-1")
        params = dict(p.split("=", 1) for p in url.split("?")[1].split("&"))
        assert verify_signed_url("doc-OTHER", int(params["exp"]), params["sig"]) is False

    def test_tampered_signature_fails(self):
        url = generate_signed_url("doc-1")
        params = dict(p.split("=", 1) for p in url.split("?")[1].split("&"))
        bad_sig = "0" * len(params["sig"])
        assert verify_signed_url("doc-1", int(params["exp"]), bad_sig) is False

    def test_tampered_expiry_fails(self):
        url = generate_signed_url("doc-1", expires_in=600)
        params = dict(p.split("=", 1) for p in url.split("?")[1].split("&"))
        shifted = int(params["exp"]) + 1000
        assert verify_signed_url("doc-1", shifted, params["sig"]) is False

    def test_garbage_signature_fails(self):
        url = generate_signed_url("doc-1")
        params = dict(p.split("=", 1) for p in url.split("?")[1].split("&"))
        assert verify_signed_url("doc-1", int(params["exp"]), "not-a-signature") is False

    def test_empty_document_id(self):
        url = generate_signed_url("", expires_in=60)
        params = dict(p.split("=", 1) for p in url.split("?")[1].split("&"))
        assert verify_signed_url("", int(params["exp"]), params["sig"]) is True

    def test_unicode_document_id_roundtrip(self):
        url = generate_signed_url("décument-π", expires_in=60)
        params = dict(p.split("=", 1) for p in url.split("?")[1].split("&"))
        assert verify_signed_url("décument-π", int(params["exp"]), params["sig"]) is True

    def test_expiry_boundary_is_exclusive(self):
        """expires_at == now is treated as expired (uses <)."""
        from caremate.security.signed_urls import _sign
        now = int(time.time())
        sig = _sign("doc-1", now)
        time.sleep(1.1)  # ensure now > expires_at
        assert verify_signed_url("doc-1", now, sig) is False

    def test_redaction_of_phi_complement(self):
        """Quick sanity check that redaction interacts with stored payloads."""
        assert redact_phi("call 555-123-4567") == "call [REDACTED]"
