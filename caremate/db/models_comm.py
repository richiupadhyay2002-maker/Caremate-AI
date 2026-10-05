"""Conversation, message, AI-generation, citation, and audit-log models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func,
)
from sqlalchemy.orm import relationship

from caremate.db.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(128), nullable=False, unique=True, index=True)
    patient_id = Column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(300), default="New Conversation")
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(),
                        server_default=func.now(), onupdate=func.now())

    patient = relationship("Patient", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)  # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


class AI_Generation(Base):
    __tablename__ = "ai_generations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    query = Column(Text, nullable=False)
    response_text = Column(Text, default="")
    confidence = Column(Float, default=0.0)
    safety_flags = Column(JSON, default=[])
    full_response_json = Column(JSON, default={})
    metadata_json = Column(JSON, default={}, name="metadata")
    # --- Doctor review workflow fields ---
    status = Column(String(20), default="pending", nullable=False,
                    doc="Review status: pending, approved, rejected, edited")
    doctor_notes = Column(Text, default="", nullable=False,
                          doc="Doctor's notes from review")
    reviewed_by = Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
                         doc="User ID of the reviewing doctor")
    reviewed_at = Column(DateTime(timezone=True), nullable=True,
                         doc="When the generation was reviewed")
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    patient = relationship("Patient", back_populates="ai_generations")
    citations = relationship("Citation", back_populates="ai_generation", cascade="all, delete-orphan")
    reviewer = relationship("User", primaryjoin="User.id == AI_Generation.reviewed_by")


class Citation(Base):
    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ai_generation_id = Column(ForeignKey("ai_generations.id", ondelete="CASCADE"), nullable=True)
    chunk_id = Column(ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    patient_id = Column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    source_document = Column(String(128), default="")
    section = Column(String(100), default="unknown")
    chunk_ref = Column(String(128), default="")
    page_number = Column(Integer, nullable=True, doc="Page number of the cited source")
    relevance_score = Column(Float, default=0.0)
    text_snippet = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    ai_generation = relationship("AI_Generation", back_populates="citations")
    chunk = relationship("DocumentChunk", back_populates="citations")
    patient = relationship("Patient", back_populates="citations")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_user_id = Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), default="")
    resource_id = Column(String(128), default="")
    ip_address = Column(String(64), default="")
    user_agent = Column(String(500), default="")
    request_body = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    actor = relationship("User", back_populates="audit_logs")
