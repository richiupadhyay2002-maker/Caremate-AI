"""Safety agent — runs guardrails and short-circuits if needed.

Fifth agent in the pipeline: Document → Retrieval → Summarization →
Citation → Safety → Response.

Checks for prompt injection, red-flag symptoms, and drug-food
interactions. If any check triggers a short-circuit, the pipeline
aborts and returns a safety-blocked response.
"""

from __future__ import annotations

from caremate.agents.base import BaseAgent, PipelineData
from caremate.guardrails.prompt_injection import PromptInjectionDetector, InjectionResult
from caremate.guardrails.red_flag_symptoms import RedFlagDetector, SymptomResult
from caremate.guardrails.drug_food_interactions import (
    DrugFoodInteractionChecker,
    InteractionResult,
)
from caremate.models.response import (
    SafetyCheckResult,
    SafetyFlag,
    Citation,
    StructuredAIResponse,
)
from caremate.utils.config import get_logger

logger = get_logger(__name__)


class SafetyAgent(BaseAgent):
    """Runs all safety guardrails on the pipeline output.

    If any guardrail triggers a short-circuit, the pipeline aborts
    and produces a safe, conservative response.
    """

    def __init__(
        self,
        injection_detector: PromptInjectionDetector | None = None,
        red_flag_detector: RedFlagDetector | None = None,
        interaction_checker: DrugFoodInteractionChecker | None = None,
    ):
        self._injector = injection_detector or PromptInjectionDetector()
        self._red_flags = red_flag_detector or RedFlagDetector()
        self._interactions = interaction_checker or DrugFoodInteractionChecker()

    @property
    def name(self) -> str:
        return "SafetyAgent"

    def process(self, data: PipelineData) -> PipelineData:
        """Run all safety checks on the query, summary, and patient context."""
        data.trace(self.name, "Running safety guardrails")

        flags: list[SafetyFlag] = []
        reasons: list[str] = []
        short_circuit = False

        # 1. Prompt injection detection on the user query
        injection_result = self._injector.detect(data.query)
        if injection_result.detected:
            flags.append(SafetyFlag.PROMPT_INJECTION)
            reasons.append(injection_result.reason)
            short_circuit = True
            data.trace(self.name, f"PROMPT INJECTION DETECTED: {injection_result.reason}")

        # 2. Red-flag symptom detection on the query AND the summary
        query_flags = self._red_flags.check(data.query)
        summary_flags = self._red_flags.check(data.summary) if data.summary else SymptomResult(detected=False)

        if query_flags.detected:
            flags.append(SafetyFlag.RED_FLAG_SYMPTOM)
            reasons.append(query_flags.reason)
            if query_flags.severity in ("emergency", "warning"):
                short_circuit = True
            data.trace(self.name, f"RED FLAG in query: {query_flags.flags} (severity: {query_flags.severity})")

        if summary_flags.detected:
            flags.append(SafetyFlag.RED_FLAG_SYMPTOM)
            reasons.append(summary_flags.reason)
            if summary_flags.severity in ("emergency", "warning"):
                short_circuit = True
            data.trace(self.name, f"RED FLAG in summary: {summary_flags.flags}")

        # 3. Drug-food interaction check
        if data.patient and data.retrieved_chunks:
            meds = data.patient.medication_names
            # Extract dietary recommendations from retrieved chunks
            diet_terms = self._extract_diet_terms(data.retrieved_chunks)
            interaction_result = self._interactions.check(meds, diet_terms)
            if interaction_result.has_interactions:
                flags.append(SafetyFlag.DRUG_FOOD_INTERACTION)
                reasons.append(interaction_result.reason)
                if interaction_result.severity in ("major", "moderate"):
                    short_circuit = True
                data.trace(self.name, f"DRUG-FOOD INTERACTION: {interaction_result.interactions}")

        # 4. Low confidence check
        if data.confidence < 0.3 and not short_circuit:
            flags.append(SafetyFlag.LOW_CONFIDENCE)
            reasons.append(f"Low confidence score: {data.confidence:.2f}")
            data.trace(self.name, "Low confidence detected")

        # Build the safety result
        is_safe = not short_circuit
        safety_result = SafetyCheckResult(
            is_safe=is_safe,
            flags=flags,
            reasons=reasons,
            short_circuit=short_circuit,
        )

        data.safety_result = safety_result
        data.trace(self.name, f"Safety result: safe={is_safe}, short_circuit={short_circuit}, flags={flags}")
        logger.info("SafetyAgent: safe=%s, short_circuit=%s, flags=%s",
                     is_safe, short_circuit, flags)
        return data

    @staticmethod
    def _extract_diet_terms(chunks: list) -> list[str]:
        """Extract food-related terms from retrieved chunk content."""
        import re
        food_keywords = [
            "calcium", "protein", "sodium", "potassium", "vitamin k",
            "iron", "grapefruit", "cranberry", "dairy", "cheese", "milk",
            "leafy greens", "spinach", "kale", "broccoli",
            "salt substitute", "tyramine", "aged cheese", "red wine",
        ]
        found: list[str] = []
        for chunk, _ in chunks:
            content_lower = chunk.content.lower()
            for kw in food_keywords:
                if kw in content_lower:
                    found.append(kw)
        return list(set(found))
