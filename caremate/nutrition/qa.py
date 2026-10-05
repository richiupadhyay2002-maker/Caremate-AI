"""Nutrition Q&A — patient-facing nutrition question answering.

Wraps the core pipeline to provide structured, cited nutrition responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from caremate.models.patient import PatientContext
from caremate.models.response import StructuredAIResponse, Citation, SafetyFlag
from caremate.pipeline import CarematePipeline
from caremate.nutrition.database import get_dietary_recommendations, FOOD_GROUPS


@dataclass
class NutritionContext:
    """Nutrition-specific context extracted from the patient record."""
    conditions: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    dietary_restrictions: list[str] = field(default_factory=list)
    weight: Optional[float] = None
    height: Optional[float] = None
    recent_weight_change: Optional[float] = None  # percent


class NutritionQA:
    """Provides structured nutrition Q&A using the Caremate pipeline.

    Enhances the patient context with nutrition-specific data before
    running the pipeline, ensuring responses account for medical conditions
    and medication interactions.
    """

    def __init__(self, pipeline: CarematePipeline):
        self._pipeline = pipeline

    def answer(
        self,
        query: str,
        patient: PatientContext,
        raw_documents: list[str] | None = None,
    ) -> StructuredAIResponse:
        """Answer a nutrition-related question for the patient.

        Args:
            query: The patient's nutrition question.
            patient: The patient's medical context.
            raw_documents: Optional additional nutrition documents.

        Returns:
            A typed, cited StructuredAIResponse.
        """
        # Build nutrition-specific documents if none provided
        if not raw_documents:
            raw_documents = self._build_nutrition_documents(patient)

        return self._pipeline.run(query=query, patient=patient, raw_documents=raw_documents)

    def _build_nutrition_documents(self, patient: PatientContext) -> list[str]:
        """Generate nutrition guidance documents based on patient conditions."""
        docs: list[str] = []
        conditions = patient.medical_history
        recommendations, avoid = get_dietary_recommendations(conditions)

        # Build a nutrition guidance document
        doc_parts = ["NUTRITION ASSESSMENT AND DIETARY RECOMMENDATIONS\n\n"]

        if recommendations:
            doc_parts.append("RECOMMENDED:\n")
            for rec in recommendations:
                doc_parts.append(f"- {rec}\n")
            doc_parts.append("\n")

        if avoid:
            doc_parts.append("FOODS TO AVOID:\n")
            for item in avoid:
                doc_parts.append(f"- {item}\n")
            doc_parts.append("\n")

        # Add medication-specific warnings
        if patient.current_medications:
            doc_parts.append("MEDICATION CONSIDERATIONS:\n")
            for med in patient.current_medications:
                doc_parts.append(f"- {med.name} ({med.dosage}): ")
                doc_parts.append(self._med_warning(med.name))
                doc_parts.append("\n")

        # Add allergy guidance
        if patient.allergies:
            doc_parts.append("\nALLERGY CONSIDERATIONS:\n")
            for allergy in patient.allergies:
                doc_parts.append(f"- Avoid {allergy.substance}: {allergy.reaction}\n")

        docs.append("".join(doc_parts))
        return docs

    def _med_warning(self, med_name: str) -> str:
        """Return nutrition-related warning for a medication."""
        med_lower = med_name.lower()
        from caremate.guardrails.drug_food_interactions import DRUG_FOOD_INTERACTIONS
        if med_lower in DRUG_FOOD_INTERACTIONS:
            foods = DRUG_FOOD_INTERACTIONS[med_lower]
            if foods:
                return f"Avoid: {', '.join(foods[:3])}"
        return "No specific dietary restrictions"
