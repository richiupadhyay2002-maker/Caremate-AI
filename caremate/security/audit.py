"""Audit logging — structured, persistent audit trail.

Every write operation that touches patient data — AI generations, document
access, doctor review actions, and data-deletion events — is recorded in the
``AuditLog`` table.  Audit writes are **best-effort**: if the write itself
fails, the primary operation still succeeds, and the failure is logged at
WARNING level (with PHI already redacted by the :class:`PhiRedactionFilter`).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

from caremate.db.models_comm import AuditLog
from caremate.security.redaction import redact_phi
from caremate.utils.config import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)


class AuditLogger:
    """Write structured audit entries to the ``AuditLog`` table.

    All public methods are idempotent and never raise: if the database
    write fails, the error is caught and logged.
    """

    def __init__(self, db: Session):
        self._db = db

    # ------------------------------------------------------------------
    # Low-level primitive
    # ------------------------------------------------------------------
    def log(
        self,
        action: str,
        resource_type: str,
        resource_id: str = "",
        user=None,
        ip_address: str = "",
        user_agent: str = "",
        request_body: Optional[dict] = None,
    ) -> None:
        """Persist a single audit-log entry.

        Args:
            action: Short verb describing the action (e.g. ``"ai_generation_created"``).
            resource_type: The entity type (e.g. ``"ai_generation"``, ``"document"``).
            resource_id: String identifier of the specific resource.
            user: The authenticated ``User`` (provides ``actor_user_id``).
            ip_address: Client IP (from the FastAPI request, if available).
            user_agent: Client User-Agent string (if available).
            request_body: Structured payload for context (PHI must be pre-redacted
                          or minimal).
        """
        try:
            entry = AuditLog(
                actor_user_id=user.id if user else None,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_body=json.dumps(request_body) if request_body else "",
            )
            self._db.add(entry)
            self._db.flush()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to write audit log: %s", exc)

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------
    def log_ai_generation(
        self,
        patient_id: str,
        query: str,
        response_text: str,
        confidence: float,
        user=None,
        ip_address: str = "",
        user_agent: str = "",
    ) -> None:
        """Log that an AI generation was created for a patient."""
        # Store only a redacted subset — never the full response with PHI
        redacted_query = redact_phi(query)[:200]
        self.log(
            action="ai_generation_created",
            resource_type="ai_generation",
            resource_id=f"patient:{patient_id}",
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            request_body={
                "query_preview": redacted_query,
                "confidence": round(confidence, 4),
            },
        )

    def log_document_access(
        self,
        document_id: str,
        patient_id: str,
        user=None,
        ip_address: str = "",
        user_agent: str = "",
    ) -> None:
        """Log that a medical document was accessed."""
        self.log(
            action="document_accessed",
            resource_type="document",
            resource_id=document_id,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            request_body={"patient_id": patient_id},
        )

    def log_doctor_review(
        self,
        generation_id: int,
        patient_id: str,
        status: str,
        user=None,
        ip_address: str = "",
        user_agent: str = "",
    ) -> None:
        """Log a doctor's approve / edit / reject action on an AI generation."""
        self.log(
            action="doctor_review",
            resource_type="ai_generation",
            resource_id=str(generation_id),
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            request_body={
                "patient_id": patient_id,
                "new_status": status,
            },
        )

    def log_data_deletion(
        self,
        patient_id: str,
        deleted_tables: list[str],
        user=None,
        ip_address: str = "",
        user_agent: str = "",
    ) -> None:
        """Log a GDPR data-deletion event."""
        self.log(
            action="patient_data_deleted",
            resource_type="patient",
            resource_id=patient_id,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            request_body={"deleted_tables": deleted_tables},
        )


def get_audit_logger(db: Session) -> AuditLogger:
    """Convenience factory."""
    return AuditLogger(db)
