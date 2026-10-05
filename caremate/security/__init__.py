"""Security & privacy hardening for Caremate AI.

Submodules:
    - :mod:`redaction`       — PII/PHI detection and log redaction
    - :mod:`audit`           — structured audit-log writer (AuditLog model)
    - :mod:`authorization`   — RBAC + patient-ownership FastAPI dependencies
    - :mod:`signed_urls`     — time-limited signed URLs for document access
    - :mod:`retention`       — GDPR data deletion / export / retention policy

Only :mod:`redaction` is eagerly imported to avoid circular-import chains
(config -> security -> db -> config).  The remaining submodules are loaded
lazily via :func:`__getattr__`.
"""

from caremate.security.redaction import PhiRedactionFilter, redact_phi

__all__ = [
    "AuditLogger",
    "PhiRedactionFilter",
    "redact_phi",
    "generate_signed_url",
    "verify_signed_url",
    "get_client_info",
    "require_own_patient",
    "require_doctor_patient",
    "require_self_or_admin",
    "delete_patient_data",
    "export_patient_data",
    "apply_retention_policy",
]


def __getattr__(name: str):
    """Lazy-import submodules that have heavier dependency chains."""
    if name in ("AuditLogger", "get_audit_logger"):
        from caremate.security.audit import AuditLogger, get_audit_logger
        if name == "AuditLogger":
            return AuditLogger
        return get_audit_logger
    if name in ("generate_signed_url", "verify_signed_url"):
        from caremate.security.signed_urls import generate_signed_url, verify_signed_url
        if name == "generate_signed_url":
            return generate_signed_url
        return verify_signed_url
    if name in ("get_client_info", "require_own_patient", "require_doctor_patient", "require_self_or_admin"):
        from caremate.security.authorization import (
            get_client_info,
            require_doctor_patient,
            require_own_patient,
            require_self_or_admin,
        )
        return {
            "get_client_info": get_client_info,
            "require_own_patient": require_own_patient,
            "require_doctor_patient": require_doctor_patient,
            "require_self_or_admin": require_self_or_admin,
        }[name]
    if name in ("delete_patient_data", "export_patient_data", "apply_retention_policy"):
        from caremate.security.retention import (
            apply_retention_policy,
            delete_patient_data,
            export_patient_data,
        )
        return {
            "delete_patient_data": delete_patient_data,
            "export_patient_data": export_patient_data,
            "apply_retention_policy": apply_retention_policy,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

