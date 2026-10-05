"""Clinical record models: events, labs, medications, appointments, symptoms."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON,
    String, Text, func,
)
from sqlalchemy.orm import relationship

from caremate.db.base import Base


class MedicalEvent(Base):
    __tablename__ = "medical_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), default="visit")
    title = Column(String(300), default="")
    description = Column(Text, default="")
    severity = Column(String(50), default="none")
    provider = Column(String(200), default="")
    event_date = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(JSON, default={}, name="metadata")
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    patient = relationship("Patient", back_populates="medical_events")


class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    test_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=True)
    unit = Column(String(50), default="")
    reference_low = Column(Float, nullable=True)
    reference_high = Column(Float, nullable=True)
    flag = Column(String(50), default="")
    performed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    patient = relationship("Patient", back_populates="lab_results_records")


class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    dosage = Column(String(100), default="")
    frequency = Column(String(100), default="")
    started_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    patient = relationship("Patient", back_populates="medications")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(300), default="")
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, default=30)
    status = Column(String(50), default="scheduled")
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")


class Symptom(Base):
    __tablename__ = "symptoms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    severity = Column(String(50), default="mild")
    onset = Column(String(50), default="sudden")
    duration = Column(String(100), default="")
    notes = Column(Text, default="")
    recorded_at = Column(DateTime(timezone=True), default=func.now())
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    patient = relationship("Patient", back_populates="symptoms")
