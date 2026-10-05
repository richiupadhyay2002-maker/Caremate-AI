"""Patient context models for Caremate AI."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class MedicationEntry(BaseModel):
    """A single medication entry in the patient's record."""

    name: str
    dosage: str
    frequency: str
    started_date: Optional[date] = None
    notes: Optional[str] = None

    model_config = {"extra": "ignore"}


class AllergyEntry(BaseModel):
    """A single allergy entry."""

    substance: str
    reaction: str
    severity: str = Field(default="unknown")

    model_config = {"extra": "ignore"}


class PatientContext(BaseModel):
    """Full medical context for a patient — carries through the pipeline."""

    patient_id: str = Field(..., description="Unique patient identifier (PII-scoped)")
    name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    medical_history: list[str] = Field(default_factory=list, description="Past diagnoses / conditions")
    current_medications: list[MedicationEntry] = Field(default_factory=list)
    allergies: list[AllergyEntry] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list, description="e.g. ['low sodium', 'no dairy']")
    recent_weight: Optional[float] = None  # kg
    height: Optional[float] = None  # cm
    lab_results: dict[str, float] = Field(default_factory=dict, description="e.g. {'albumin': 3.2, 'glucose': 95}")
    notes: Optional[str] = None

    model_config = {"extra": "ignore"}

    @property
    def medication_names(self) -> list[str]:
        """Lower-cased list of current medication names for interaction checks."""
        return [m.name.lower().strip() for m in self.current_medications]
