"""Patient, Doctor, and patient-doctor relationship models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from caremate.db.base import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(64), nullable=False, unique=True, index=True)
    organization_id = Column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    full_name = Column(String(200), default="")
    age = Column(Integer, nullable=True)
    sex = Column(String(20), nullable=True)
    medical_history = Column(JSON, default=[])
    allergies = Column(JSON, default=[])
    dietary_restrictions = Column(JSON, default=[])
    recent_weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    lab_results = Column(JSON, default={})
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(),
                        server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="patients")
    documents = relationship("MedicalDocument", back_populates="patient", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="patient", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="patient", cascade="all, delete-orphan")
    lab_results_records = relationship("LabResult", back_populates="patient", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    symptoms = relationship("Symptom", back_populates="patient", cascade="all, delete-orphan")
    medical_events = relationship("MedicalEvent", back_populates="patient", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="patient", cascade="all, delete-orphan")
    ai_generations = relationship("AI_Generation", back_populates="patient", cascade="all, delete-orphan")
    citations = relationship("Citation", back_populates="patient", cascade="all, delete-orphan")
    doctor_rels = relationship("PatientDoctorRelationship", back_populates="patient",
                               cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("patient_id", name="uq_patients_patient_id"),)


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id = Column(String(64), nullable=False, unique=True, index=True)
    organization_id = Column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    full_name = Column(String(200), nullable=False)
    specialty = Column(String(100), default="")
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    organization = relationship("Organization", back_populates="doctors")
    patient_rels = relationship("PatientDoctorRelationship", back_populates="doctor",
                                cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor", cascade="all, delete-orphan")


class PatientDoctorRelationship(Base):
    __tablename__ = "patient_doctor_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(50), default="primary")
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    patient = relationship("Patient", back_populates="doctor_rels")
    doctor = relationship("Doctor", back_populates="patient_rels")

    __table_args__ = (UniqueConstraint("patient_id", "doctor_id", name="uq_patient_doctor"),)
