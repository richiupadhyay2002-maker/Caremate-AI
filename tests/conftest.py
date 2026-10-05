"""Shared pytest fixtures for Caremate AI tests."""

import pytest

from caremate.utils.config import get_settings
# Clear cached settings before each test for isolation
get_settings.cache_clear()

from caremate.models.patient import PatientContext, MedicationEntry, AllergyEntry
from caremate.models.document import DocumentChunk
from caremate.providers.mock import MockLLMProvider, MockEmbeddingProvider
from caremate.retrieval.chunker import SectionAwareChunker
from caremate.retrieval.vector_store import PatientIsolatedVectorStore
from caremate.retrieval.retriever import HybridRetriever
from caremate.retrieval.embeddings import EmbeddingManager
from caremate.pipeline import CarematePipeline


@pytest.fixture
def mock_llm():
    """A MockLLMProvider instance."""
    return MockLLMProvider()


@pytest.fixture
def mock_embedding_provider():
    """A MockEmbeddingProvider instance."""
    return MockEmbeddingProvider(dim=384)


@pytest.fixture
def embedding_manager(mock_embedding_provider):
    """An EmbeddingManager wrapping the mock provider."""
    return EmbeddingManager(mock_embedding_provider)


@pytest.fixture
def chunker():
    """A SectionAwareChunker instance."""
    return SectionAwareChunker()


@pytest.fixture
def vector_store():
    """A PatientIsolatedVectorStore instance."""
    return PatientIsolatedVectorStore(dim=384)


@pytest.fixture
def sample_patient():
    """A sample patient for testing."""
    return PatientContext(
        patient_id="patient_A",
        name="Test Patient A",
        age=65,
        sex="male",
        medical_history=["heart failure", "hypertension"],
        current_medications=[
            MedicationEntry(name="lisinopril", dosage="10mg", frequency="daily"),
            MedicationEntry(name="warfarin", dosage="5mg", frequency="daily"),
        ],
        allergies=[AllergyEntry(substance="penicillin", reaction="rash")],
        dietary_restrictions=["low sodium"],
        lab_results={"albumin": 3.4},
        notes="Reports poor appetite and weight loss.",
    )


@pytest.fixture
def another_patient():
    """A second patient for isolation tests."""
    return PatientContext(
        patient_id="patient_B",
        name="Test Patient B",
        age=70,
        sex="female",
        medical_history=["diabetes", "osteoporosis"],
        current_medications=[
            MedicationEntry(name="metformin", dosage="500mg", frequency="twice daily"),
        ],
        dietary_restrictions=["low sugar"],
    )


@pytest.fixture
def medical_document_text():
    """A sample medical document with section headers."""
    return """
PATIENT HISTORY
The patient is a 65-year-old male with a history of heart failure
and hypertension. He has been on lisinopril and warfarin.

MEDICATIONS
- Lisinopril 10mg daily (ACE inhibitor)
- Warfarin 5mg daily (monitor INR weekly)

DIETARY INSTRUCTIONS
- Limit sodium to less than 2,000 mg per day
- Avoid cranberry juice (interferes with warfarin)
- Take levothyroxine on empty stomach, 30 min before food
- Increase protein intake for muscle maintenance

LABORATORY RESULTS
- Sodium: 135 mmol/L
- Albumin: 3.4 g/dL
- INR: 2.8 (within therapeutic range)

NUTRITIONAL ASSESSMENT
The patient shows signs of mild malnutrition risk. Weight loss
of approximately 3% has been noted over the past month.
"""


@pytest.fixture
def pipeline():
    """A CarematePipeline with mock providers and pre-seeded patient data."""
    p = CarematePipeline(use_mock=True)
    return p


@pytest.fixture
def pipeline_with_data(pipeline, sample_patient, medical_document_text):
    """Pipeline with a sample patient's documents pre-indexed."""
    pipeline.add_documents([medical_document_text], patient_id=sample_patient.patient_id)
    return pipeline
