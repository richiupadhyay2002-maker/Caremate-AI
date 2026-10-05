"""End-to-end tests for the nutrition feature.

Tests the full nutrition Q&A pipeline and the silent doctor-side
malnutrition risk watcher.
"""

import pytest

from caremate.models.patient import PatientContext, MedicationEntry
from caremate.models.response import StructuredAIResponse
from caremate.nutrition.qa import NutritionQA
from caremate.nutrition.malnutrition_watcher import MalnutritionWatcher


@pytest.fixture
def diabetic_patient():
    """A patient with diabetes and hypertension for nutrition testing."""
    return PatientContext(
        patient_id="nutri_test_1",
        name="Test Patient",
        age=62,
        sex="female",
        medical_history=["type 2 diabetes", "hypertension"],
        current_medications=[
            MedicationEntry(name="metformin", dosage="1000mg", frequency="daily"),
            MedicationEntry(name="lisinopril", dosage="10mg", frequency="daily"),
        ],
        dietary_restrictions=["low sodium", "limit sugar"],
        recent_weight=68.0,
        height=165,
        lab_results={"albumin": 3.6, "glucose": 155},
        notes="Patient has good appetite but needs guidance on diabetic diet.",
    )


@pytest.fixture
def malnourished_patient():
    """A patient showing malnutrition risk indicators."""
    return PatientContext(
        patient_id="malnutrition_test",
        name="At-Risk Patient",
        age=75,
        sex="male",
        medical_history=["cancer", "chronic kidney disease"],
        current_medications=[
            MedicationEntry(name="furosemide", dosage="20mg", frequency="daily"),
        ],
        dietary_restrictions=["low potassium"],
        recent_weight=58.0,
        height=170,
        lab_results={"albumin": 3.0, "glucose": 110},
        notes="Significant appetite loss, has not been eating well.",
    )


def test_nutrition_qa_returns_structured_response(pipeline, diabetic_patient):
    """The nutrition Q&A pipeline returns a typed StructuredAIResponse."""
    from caremate.nutrition.qa import NutritionQA
    qa = NutritionQA(pipeline)

    response = qa.answer(
        query="What should I eat for a diabetic diet?",
        patient=diabetic_patient,
    )

    assert isinstance(response, StructuredAIResponse)
    assert response.response  # non-empty
    assert 0.0 <= response.confidence <= 1.0
    # Citations should reference real documents
    for citation in response.citations:
        assert citation.source_document
        assert citation.chunk_id
        assert citation.text_snippet


def test_malnutrition_watcher_detects_risk(malnourished_patient):
    """The malnutrition watcher correctly flags high-risk patients."""
    watcher = MalnutritionWatcher(score_threshold=0.25)

    alert = watcher.check(malnourished_patient)

    assert alert is not None
    assert alert.risk_level in ("moderate", "high")
    assert alert.risk_score >= 0.25
    assert alert.requires_attention is True
    assert len(alert.factors) > 0
    assert "albumin" in alert.factors[0].lower() or "weight" in alert.factors[0].lower()


def test_malnutrition_watcher_no_false_alarm(diabetic_patient):
    """A healthy patient does not trigger a malnutrition alert."""
    watcher = MalnutritionWatcher(score_threshold=0.3)

    alert = watcher.check(diabetic_patient)

    # This patient has albumin 3.6 (normal) and no major risk factors
    assert alert is None or not alert.requires_attention
