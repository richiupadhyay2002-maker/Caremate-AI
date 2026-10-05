"""Tests for red-flag symptom detection and pipeline short-circuiting.

When dangerous symptoms are detected, the SafetyAgent should
short-circuit the pipeline and produce a safety-blocked response.
"""

import pytest

from caremate.agents.safety_agent import SafetyAgent
from caremate.agents.base import PipelineData
from caremate.agents.response_agent import ResponseAgent
from caremate.guardrails.red_flag_symptoms import RedFlagDetector
from caremate.models.response import SafetyFlag, StructuredAIResponse


@pytest.fixture
def safety_agent():
    return SafetyAgent()


@pytest.fixture
def sample_patient_ctx(sample_patient):
    return sample_patient


def test_chest_pain_triggers_short_circuit(safety_agent, sample_patient_ctx):
    """Chest pain in the query triggers emergency-level short-circuit."""
    data = PipelineData(
        query="I have severe chest pain and pressure in my chest.",
        patient=sample_patient_ctx,
        summary="Patient reports chest pain.",
    )
    result = safety_agent.process(data)
    assert result.safety_result is not None
    assert result.safety_result.short_circuit is True
    assert SafetyFlag.RED_FLAG_SYMPTOM in result.safety_result.flags


def test_difficulty_breathing_triggers_short_circuit(safety_agent, sample_patient_ctx):
    """Difficulty breathing triggers emergency-level short-circuit."""
    data = PipelineData(
        query="I'm having difficulty breathing and my lips are blue.",
        patient=sample_patient_ctx,
        summary="Patient reports breathing difficulty.",
    )
    result = safety_agent.process(data)
    assert result.safety_result is not None
    assert result.safety_result.short_circuit is True
    assert result.safety_result.flags


def test_severe_headache_triggers_short_circuit(safety_agent, sample_patient_ctx):
    """Severe headache triggers emergency-level short-circuit."""
    data = PipelineData(
        query="I have the worst headache of my life and I'm confused.",
        patient=sample_patient_ctx,
        summary="Patient reports severe headache.",
    )
    result = safety_agent.process(data)
    assert result.safety_result is not None
    assert result.safety_result.short_circuit is True
    assert SafetyFlag.RED_FLAG_SYMPTOM in result.safety_result.flags


def test_sudden_weakness_triggers_short_circuit(safety_agent, sample_patient_ctx):
    """Sudden weakness triggers emergency-level short-circuit."""
    data = PipelineData(
        query="I suddenly can't move my left arm and my speech is slurred.",
        patient=sample_patient_ctx,
        summary="Patient reports sudden weakness and slurred speech.",
    )
    result = safety_agent.process(data)
    assert result.safety_result is not None
    assert result.safety_result.short_circuit is True


def test_normal_query_no_short_circuit(safety_agent, sample_patient_ctx):
    """Normal nutrition questions should not trigger short-circuiting."""
    data = PipelineData(
        query="What foods are high in protein?",
        patient=sample_patient_ctx,
        summary="Protein is important for healing.",
        confidence=0.8,
    )
    result = safety_agent.process(data)
    assert result.safety_result is not None
    assert result.safety_result.short_circuit is False
    assert result.safety_result.is_safe is True


def test_pipeline_aborts_on_red_flag(pipeline, sample_patient):
    """End-to-end: pipeline short-circuits when red-flag symptom is in query."""
    pipeline.add_documents([
        "PATIENT HISTORY\nThe patient has hypertension."
    ], patient_id=sample_patient.patient_id)

    response = pipeline.run(
        query="I have sudden severe chest pain and difficulty breathing!",
        patient=sample_patient,
    )
    assert isinstance(response, StructuredAIResponse)
    assert SafetyFlag.RED_FLAG_SYMPTOM in response.safety_flags
    assert "cannot" in response.response.lower() or "consult" in response.response.lower()
