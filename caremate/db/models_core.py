"""Core identity models: organizations, users, patients, doctors."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, JSON,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from caremate.db.base import Base


class UserRole(str, enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    address = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    patients = relationship("Patient", back_populates="organization", cascade="all, delete-orphan")
    doctors = relationship("Doctor", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), default="")
    role = Column(Enum(UserRole, name="user_role"), nullable=False, default=UserRole.PATIENT)
    is_active = Column(Boolean, default=True, nullable=False)
    organization_id = Column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(),
                        server_default=func.now(), onupdate=func.now())

    patient_id = Column(ForeignKey("patients.id", ondelete="SET NULL"), nullable=True)
    doctor_id = Column(ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True)

    organization = relationship("Organization", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="actor", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)
