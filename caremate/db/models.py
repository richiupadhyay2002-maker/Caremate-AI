"""Re-export all SQLAlchemy ORM models and the Base.

Importing this module registers every mapped class on the shared ``Base``
metadata so that ``Base.metadata.create_all(engine)`` will create all tables.
"""

# Import order matters: core identity models first (User references Patient/Doctor
# via FK, but SQLAlchemy deferred-FK resolution handles forward refs), then the
# rest.  Importing all submodules attaches their classes to ``Base.metadata``.

from caremate.db.base import Base, Vector, hnsw_index  # noqa: F401
from caremate.db.models_core import Organization, User, UserRole  # noqa: F401
from caremate.db.models_patients import (  # noqa: F401
    Patient, Doctor, PatientDoctorRelationship,
)
from caremate.db.models_docs import (  # noqa: F401
    MedicalDocument, DocumentChunk, DocumentType,
)
from caremate.db.models_clinical import (  # noqa: F401
    MedicalEvent, LabResult, Medication, Appointment, Symptom,
)
from caremate.db.models_comm import (  # noqa: F401
    Conversation, Message, AI_Generation, Citation, AuditLog,
)

__all__ = [
    "Base",
    "Vector",
    "hnsw_index",
    "Organization",
    "User",
    "UserRole",
    "Patient",
    "Doctor",
    "PatientDoctorRelationship",
    "MedicalDocument",
    "DocumentChunk",
    "DocumentType",
    "MedicalEvent",
    "LabResult",
    "Medication",
    "Appointment",
    "Symptom",
    "Conversation",
    "Message",
    "AI_Generation",
    "Citation",
    "AuditLog",
]
