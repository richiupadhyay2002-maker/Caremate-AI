"""Seed script for Caremate AI demo accounts and sample data."""

from __future__ import annotations

from caremate.api.security import hash_password
from caremate.db.models_clinical import LabResult, Medication
from caremate.db.models_core import Organization, User, UserRole
from caremate.db.models_docs import MedicalDocument
from caremate.db.models_patients import Doctor, Patient, PatientDoctorRelationship
from caremate.db.session import get_session_factory
from caremate.utils.config import get_logger

logger = get_logger(__name__)

DEMO_ADMIN_EMAIL = "admin@caremate.ai"
DEMO_ADMIN_PASSWORD = "adminpass"
DEMO_ADMIN_ID = "A0001"

DEMO_PATIENT_EMAIL = "patient@caremate.ai"
DEMO_PATIENT_PASSWORD = "patient123"
DEMO_PATIENT_ID = "P0001"

DEMO_DOCTOR_EMAIL = "doctor@caremate.ai"
DEMO_DOCTOR_PASSWORD = "doctor123"
DEMO_DOCTOR_ID = "D0001"

DEMO_ORG = "Caremate Demo Clinic"

SAMPLE_CLINICAL_NOTE = """CHIEF COMPLAINT
Persistent fatigue and shortness of breath on exertion for 3 months.

PATIENT HISTORY
65-year-old male with a history of hypertension, type 2 diabetes, and
dyslipidemia. Currently on lisinopril, metformin, and atorvastatin.

MEDICATIONS
- Lisinopril 10mg daily (ACE inhibitor)
- Metformin 500mg twice daily
- Atorvastatin 20mg nightly

LABORATORY RESULTS
- HbA1c: 7.2% (target <7.0%)
- LDL Cholesterol: 110 mg/dL
- Creatinine: 1.1 mg/dL
- Albumin: 3.8 g/dL

ASSESSMENT
Type 2 diabetes with suboptimal glycemic control. Hypertension well-controlled
on lisinopril. Consider medication adjustment.

PLAN
1. Increase metformin to 1000mg twice daily
2. Recheck HbA1c in 3 months
3. Continue current medications
4. Dietary counseling for diabetes management
"""


def _get_org(db):
    org = db.query(Organization).filter(Organization.name == DEMO_ORG).first()
    if org is None:
        org = Organization(name=DEMO_ORG)
        db.add(org)
        db.flush()
        logger.info("Created demo organization: %s", DEMO_ORG)
    return org


def seed_demo() -> None:
    """Create demo accounts and sample data if they do not already exist."""
    factory = get_session_factory()
    db = factory()
    try:
        org = _get_org(db)

        # --- Doctor ---
        doctor_user = db.query(User).filter(User.email == DEMO_DOCTOR_EMAIL).first()
        if doctor_user is None:
            doctor_user = User(
                email=DEMO_DOCTOR_EMAIL,
                hashed_password=hash_password(DEMO_DOCTOR_PASSWORD),
                full_name="Dr. Sarah Chen",
                role=UserRole.DOCTOR,
                organization_id=org.id,
            )
            db.add(doctor_user)
            db.flush()
            logger.info("Created demo doctor user: %s", DEMO_DOCTOR_EMAIL)

        admin_user = db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).first()
        if admin_user is None:
            admin_user = User(
                email=DEMO_ADMIN_EMAIL,
                hashed_password=hash_password(DEMO_ADMIN_PASSWORD),
                full_name="Admin User",
                role=UserRole.ADMIN,
                organization_id=org.id,
            )
            db.add(admin_user)
            db.flush()
            logger.info("Created demo admin user: %s", DEMO_ADMIN_EMAIL)

        doctor = db.query(Doctor).filter(Doctor.doctor_id == DEMO_DOCTOR_ID).first()
        if doctor is None:
            doctor = Doctor(
                doctor_id=DEMO_DOCTOR_ID,
                full_name="Dr. Sarah Chen",
                specialty="Endocrinology",
                organization_id=org.id,
            )
            db.add(doctor)
            db.flush()
            logger.info("Created demo doctor: %s", DEMO_DOCTOR_ID)

        if doctor_user.doctor_id != doctor.id:
            doctor_user.doctor_id = doctor.id
            db.add(doctor_user)
            db.flush()

        # --- Patient ---
        patient_user = db.query(User).filter(User.email == DEMO_PATIENT_EMAIL).first()
        if patient_user is None:
            patient = db.query(Patient).filter(Patient.patient_id == DEMO_PATIENT_ID).first()
            if patient is None:
                patient = Patient(
                    patient_id=DEMO_PATIENT_ID,
                    full_name="Robert Johnson",
                    age=65,
                    sex="male",
                    medical_history=["hypertension", "type 2 diabetes", "dyslipidemia"],
                    allergies=[],
                    dietary_restrictions=["low sodium", "limit vitamin k", "monitor carbs"],
                    notes="Patient reports occasional fatigue and shortness of breath on exertion.",
                )
                db.add(patient)
                db.flush()
                logger.info("Created demo patient: %s", DEMO_PATIENT_ID)

            patient_user = User(
                email=DEMO_PATIENT_EMAIL,
                hashed_password=hash_password(DEMO_PATIENT_PASSWORD),
                full_name="Robert Johnson",
                role=UserRole.PATIENT,
                organization_id=org.id,
                patient_id=patient.id,
            )
            db.add(patient_user)
            db.flush()
            logger.info("Created demo patient user: %s", DEMO_PATIENT_EMAIL)

        # --- Relationship ---
        patient = db.query(Patient).filter(Patient.patient_id == DEMO_PATIENT_ID).first()
        rel = (
            db.query(PatientDoctorRelationship)
            .filter_by(doctor_id=doctor.id, patient_id=patient_user.patient_id)
            .first()
        )
        if rel is None:
            rel = PatientDoctorRelationship(
                patient_id=patient_user.patient_id,
                doctor_id=doctor.id,
                relationship_type="primary",
            )
            db.add(rel)
            db.flush()
            logger.info("Linked patient %s to doctor %s", DEMO_PATIENT_ID, DEMO_DOCTOR_ID)

        # --- Medications ---
        if patient and not db.query(Medication).filter(Medication.patient_id == patient.id).all():
            db.add_all([
                Medication(patient_id=patient.id, name="Lisinopril", dosage="10mg", frequency="daily"),
                Medication(patient_id=patient.id, name="Metformin", dosage="500mg", frequency="twice daily"),
                Medication(patient_id=patient.id, name="Atorvastatin", dosage="20mg", frequency="nightly"),
            ])
            logger.info("Seeded sample medications")

        # --- Lab Results ---
        if patient and not db.query(LabResult).filter(LabResult.patient_id == patient.id).all():
            db.add_all([
                LabResult(patient_id=patient.id, test_name="HbA1c", value=7.2, unit="%",
                          reference_low=4.0, reference_high=6.0, flag="high"),
                LabResult(patient_id=patient.id, test_name="LDL Cholesterol", value=110, unit="mg/dL",
                          reference_low=0, reference_high=100, flag="high"),
                LabResult(patient_id=patient.id, test_name="Creatinine", value=1.1, unit="mg/dL",
                          reference_low=0.6, reference_high=1.2, flag="normal"),
                LabResult(patient_id=patient.id, test_name="Albumin", value=3.8, unit="g/dL",
                          reference_low=3.5, reference_high=5.0, flag="normal"),
            ])
            logger.info("Seeded sample lab results")

        # --- Document ---
        if patient and not db.query(MedicalDocument).filter(MedicalDocument.patient_id == patient.id).all():
            db.add(MedicalDocument(
                document_id=f"doc_{DEMO_PATIENT_ID}_seed",
                patient_id=patient.id,
                title="Clinical Note - Initial Consultation",
                document_type="clinical_note",
                source="seed",
                raw_text=SAMPLE_CLINICAL_NOTE,
            ))
            db.flush()
            logger.info("Seeded sample clinical note document")

        db.commit()
        logger.info("Demo seeding complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()