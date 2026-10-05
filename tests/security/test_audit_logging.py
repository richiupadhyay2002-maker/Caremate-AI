"""Tests for the AuditLogger class and audit-log persistence."""

from __future__ import annotations

import json

from caremate.db.models_comm import AuditLog
from caremate.db.models_core import User
from caremate.security.audit import AuditLogger, get_audit_logger


class TestAuditLogger:
    """Tests for database audit-log persistence."""

    def test_log_basic_action(self, db):
        """log() creates an AuditLog row with all fields populated."""
        user = db.query(User).first()
        # Create a test user if none exists
        if user is None:
            from caremate.api.security import hash_password
            user = User(email="audit@test.com", hashed_password=hash_password("pass"), role="patient")
            db.add(user)
            db.commit()

        logger = AuditLogger(db)
        logger.log(
            action="test_action",
            resource_type="test_resource",
            resource_id="res_123",
            user=user,
            ip_address="10.0.0.1",
            user_agent="TestAgent/1.0",
            request_body={"key": "value"},
        )

        entry = db.query(AuditLog).filter(AuditLog.action == "test_action").first()
        assert entry is not None
        assert entry.resource_type == "test_resource"
        assert entry.resource_id == "res_123"
        assert entry.actor_user_id == user.id
        assert entry.ip_address == "10.0.0.1"
        assert entry.user_agent == "TestAgent/1.0"
        assert json.loads(entry.request_body) == {"key": "value"}

    def test_log_ai_generation(self, db):
        """log_ai_generation stores a redacted query preview and confidence."""
        user = db.query(User).first()
        if user is None:
            from caremate.api.security import hash_password
            user = User(email="audit2@test.com", hashed_password=hash_password("pass"), role="patient")
            db.add(user)
            db.commit()

        logger = AuditLogger(db)
        logger.log_ai_generation(
            patient_id="patient_A",
            query="What is my diagnosis?",
            response_text="You have diabetes. SSN 123-45-6789",
            confidence=0.95,
            user=user,
        )

        entry = db.query(AuditLog).filter(AuditLog.action == "ai_generation_created").first()
        assert entry is not None
        assert entry.resource_type == "ai_generation"
        assert "patient:patient_A" == entry.resource_id
        body = json.loads(entry.request_body)
        assert "query_preview" in body
        assert body["confidence"] == 0.95
        # The response text should NOT be in the audit log (PHI safety)
        assert "123-45-6789" not in json.dumps(body)

    def test_log_document_access(self, db):
        """log_document_access records document-id + patient-id."""
        logger = AuditLogger(db)
        logger.log_document_access(
            document_id="doc_xyz",
            patient_id="patient_A",
        )

        entry = db.query(AuditLog).filter(AuditLog.action == "document_accessed").first()
        assert entry is not None
        assert entry.resource_type == "document"
        assert entry.resource_id == "doc_xyz"
        assert json.loads(entry.request_body) == {"patient_id": "patient_A"}

    def test_log_doctor_review(self, db):
        """log_doctor_review records the review action."""
        logger = AuditLogger(db)
        logger.log_doctor_review(
            generation_id=42,
            patient_id="patient_A",
            status="approved",
        )

        entry = db.query(AuditLog).filter(AuditLog.action == "doctor_review").first()
        assert entry is not None
        assert entry.resource_type == "ai_generation"
        assert entry.resource_id == "42"
        body = json.loads(entry.request_body)
        assert body["new_status"] == "approved"
        assert body["patient_id"] == "patient_A"

    def test_log_data_deletion(self, db):
        """log_data_deletion records which tables were deleted from."""
        logger = AuditLogger(db)
        logger.log_data_deletion(
            patient_id="patient_X",
            deleted_tables=["ai_generations", "documents"],
        )

        entry = db.query(AuditLog).filter(AuditLog.action == "patient_data_deleted").first()
        assert entry is not None
        assert entry.resource_type == "patient"
        assert entry.resource_id == "patient_X"
        body = json.loads(entry.request_body)
        assert "ai_generations" in body["deleted_tables"]

    def test_log_without_user(self, db):
        """log() works with user=None (anonymous actor)."""
        logger = AuditLogger(db)
        logger.log(
            action="anonymous_action",
            resource_type="test",
        )

        entry = db.query(AuditLog).filter(AuditLog.action == "anonymous_action").first()
        assert entry is not None
        assert entry.actor_user_id is None

    def test_get_audit_logger_factory(self, db):
        """get_audit_logger returns an AuditLogger instance."""
        al = get_audit_logger(db)
        assert isinstance(al, AuditLogger)
        assert al._db is db

    def test_log_failure_is_caught(self, db):
        """If the DB write fails, log() catches the exception and doesn't raise."""
        class BadSession:
            def add(self, *a, **kw):
                raise RuntimeError("DB down")
            def flush(self):
                raise RuntimeError("DB down")

        logger = AuditLogger(BadSession())
        # Should not raise
        logger.log(action="fail_test", resource_type="test")
