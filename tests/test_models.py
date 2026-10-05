"""Comprehensive unit tests for caremate.models (patient, response, document).

Covers:
- Positive cases (valid construction, defaults, computed properties)
- Negative cases (invalid values, bad types)
- Edge cases (extra-field ignoring, optional fields, boundary values)
"""

import pytest
from datetime import date, datetime
from pydantic import ValidationError

from caremate.models.patient import PatientContext, MedicationEntry, AllergyEntry
from caremate.models.response import (
    Citation,
    SafetyCheckResult,
    SafetyFlag,
    StructuredAIResponse,
)
from caremate.models.document import DocumentChunk, DocumentMetadata


# ---------------------------------------------------------------------------
# MedicationEntry
# ---------------------------------------------------------------------------

class TestMedicationEntry:
    def test_valid_entry(self):
        med = MedicationEntry(name="Metformin", dosage="500mg", frequency="twice daily")
        assert med.name == "Metformin"
        assert med.started_date is None
        assert med.notes is None

    def test_with_optional_fields(self):
        med = MedicationEntry(
            name="Aspirin", dosage="81mg", frequency="daily",
            started_date=date(2024, 1, 15), notes="with food",
        )
        assert med.started_date == date(2024, 1, 15)

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            MedicationEntry(name="Aspirin")  # dosage, frequency missing

    def test_extra_fields_ignored(self):
        med = MedicationEntry(
            name="A", dosage="1", frequency="d", some_random_field="x",
        )
        assert not hasattr(med, "some_random_field")

    def test_invalid_date_type_raises(self):
        with pytest.raises(ValidationError):
            MedicationEntry(name="A", dosage="1", frequency="d", started_date="not-a-date")


# ---------------------------------------------------------------------------
# AllergyEntry
# ---------------------------------------------------------------------------

class TestAllergyEntry:
    def test_valid_entry_with_default_severity(self):
        allergy = AllergyEntry(substance="Penicillin", reaction="rash")
        assert allergy.severity == "unknown"

    def test_explicit_severity(self):
        allergy = AllergyEntry(substance="Peanuts", reaction="anaphylaxis", severity="severe")
        assert allergy.severity == "severe"

    def test_missing_reaction_raises(self):
        with pytest.raises(ValidationError):
            AllergyEntry(substance="Latex")

    def test_extra_fields_ignored(self):
        allergy = AllergyEntry(substance="S", reaction="R", bogus=1)
        assert not hasattr(allergy, "bogus")


# ---------------------------------------------------------------------------
# PatientContext
# ---------------------------------------------------------------------------

class TestPatientContext:
    def test_minimal_valid_context(self):
        ctx = PatientContext(patient_id="patient-123")
        assert ctx.patient_id == "patient-123"
        assert ctx.name is None
        assert ctx.medical_history == []
        assert ctx.current_medications == []
        assert ctx.allergies == []
        assert ctx.dietary_restrictions == []
        assert ctx.lab_results == {}

    def test_patient_id_required(self):
        with pytest.raises(ValidationError):
            PatientContext()

    def test_nested_medication_models(self):
        ctx = PatientContext(
            patient_id="p1",
            current_medications=[
                {"name": "Warfarin", "dosage": "5mg", "frequency": "daily"},
            ],
        )
        assert ctx.current_medications[0].name == "Warfarin"
        assert isinstance(ctx.current_medications[0], MedicationEntry)

    def test_medication_names_lowercase(self):
        ctx = PatientContext(
            patient_id="p1",
            current_medications=[
                MedicationEntry(name="  Warfarin ", dosage="5mg", frequency="daily"),
                MedicationEntry(name="METFORMIN", dosage="500mg", frequency="BID"),
            ],
        )
        assert ctx.medication_names == ["warfarin", "metformin"]

    def test_medication_names_empty_when_no_meds(self):
        assert PatientContext(patient_id="p1").medication_names == []

    def test_lab_results_dict_of_floats(self):
        ctx = PatientContext(patient_id="p1", lab_results={"albumin": 3.2, "glucose": 95})
        assert ctx.lab_results["glucose"] == 95

    def test_invalid_lab_results_raise(self):
        with pytest.raises(ValidationError):
            PatientContext(patient_id="p1", lab_results={"albumin": "not-a-number"})

    def test_extra_fields_ignored(self):
        ctx = PatientContext(patient_id="p1", ssn="123-45-6789")
        assert not hasattr(ctx, "ssn")

    @pytest.mark.parametrize("field", ["age", "recent_weight", "height"])
    def test_numeric_optionals_accept_none(self, field):
        ctx = PatientContext(patient_id="p1", **{field: None})
        assert getattr(ctx, field) is None


# ---------------------------------------------------------------------------
# Citation
# ---------------------------------------------------------------------------

class TestCitation:
    def _valid(self, **overrides):
        base = dict(
            source_document="doc-1",
            chunk_id="doc-1_abc123",
            relevance_score=0.87,
            text_snippet="HbA1c is 7.2%",
        )
        base.update(overrides)
        return Citation(**base)

    def test_valid_citation(self):
        c = self._valid()
        assert c.section == "unknown"
        assert c.page_number is None

    def test_relevance_score_must_be_0_to_1(self):
        with pytest.raises(ValidationError):
            self._valid(relevance_score=1.5)
        with pytest.raises(ValidationError):
            self._valid(relevance_score=-0.1)

    def test_boundary_scores_accepted(self):
        assert self._valid(relevance_score=0.0).relevance_score == 0.0
        assert self._valid(relevance_score=1.0).relevance_score == 1.0

    def test_missing_chunk_id_raises(self):
        with pytest.raises(ValidationError):
            Citation(source_document="d", relevance_score=0.5, text_snippet="s")


# ---------------------------------------------------------------------------
# SafetyCheckResult / SafetyFlag / StructuredAIResponse
# ---------------------------------------------------------------------------

class TestSafetyModels:
    def test_safety_flag_values(self):
        assert SafetyFlag.PROMPT_INJECTION.value == "prompt_injection"
        assert SafetyFlag.RED_FLAG_SYMPTOM.value == "red_flag_symptom"
        assert SafetyFlag.DRUG_FOOD_INTERACTION.value == "drug_food_interaction"
        assert SafetyFlag.LOW_CONFIDENCE.value == "low_confidence"

    def test_safety_check_result_defaults(self):
        r = SafetyCheckResult(is_safe=True)
        assert r.flags == []
        assert r.reasons == []
        assert r.short_circuit is False

    def test_structured_response_defaults(self):
        r = StructuredAIResponse(response="Hello", confidence=0.9)
        assert r.citations == []
        assert r.safety_flags == []
        assert r.metadata == {}

    def test_structured_response_confidence_bounds(self):
        with pytest.raises(ValidationError):
            StructuredAIResponse(response="x", confidence=2.0)
        with pytest.raises(ValidationError):
            StructuredAIResponse(response="x", confidence=-1)

    def test_structured_response_missing_confidence_raises(self):
        with pytest.raises(ValidationError):
            StructuredAIResponse(response="x")

    def test_response_with_citations(self):
        r = StructuredAIResponse(
            response="Answer",
            citations=[{
                "source_document": "doc-1", "chunk_id": "c1",
                "relevance_score": 0.5, "text_snippet": "snippet",
            }],
            confidence=0.8,
            safety_flags=[SafetyFlag.LOW_CONFIDENCE],
        )
        assert r.citations[0].chunk_id == "c1"
        assert r.safety_flags == [SafetyFlag.LOW_CONFIDENCE]


# ---------------------------------------------------------------------------
# DocumentChunk / DocumentMetadata
# ---------------------------------------------------------------------------

class TestDocumentModels:
    def _chunk(self, **overrides):
        base = dict(
            chunk_id="doc1_abc", document_id="doc1", patient_id="p1",
            content="The patient reports chest pain.",
        )
        base.update(overrides)
        return DocumentChunk(**base)

    def test_valid_chunk_defaults(self):
        c = self._chunk()
        assert c.section_label == "unknown"
        assert c.token_count == 0
        assert c.embedding is None
        assert c.metadata == {}

    def test_missing_patient_id_raises(self):
        with pytest.raises(ValidationError):
            DocumentChunk(chunk_id="c", document_id="d", content="text")

    def test_extra_fields_ignored(self):
        c = self._chunk(random_extra="x")
        assert not hasattr(c, "random_extra")

    def test_metadata_created_at_defaults(self):
        m = DocumentMetadata(document_id="d1", patient_id="p1", title="T")
        assert isinstance(m.created_at, datetime)
        assert m.document_type == "clinical_note"
        assert m.source == "manual"
        assert m.tags == []

    def test_document_metadata_missing_title_raises(self):
        with pytest.raises(ValidationError):
            DocumentMetadata(document_id="d", patient_id="p")
