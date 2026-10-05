"""Guardrails package — safety checks for the pipeline."""

from caremate.guardrails.prompt_injection import PromptInjectionDetector, InjectionResult
from caremate.guardrails.red_flag_symptoms import RedFlagDetector, SymptomResult
from caremate.guardrails.drug_food_interactions import (
    DrugFoodInteractionChecker,
    InteractionResult,
    DRUG_FOOD_INTERACTIONS,
)

__all__ = [
    "PromptInjectionDetector",
    "InjectionResult",
    "RedFlagDetector",
    "SymptomResult",
    "DrugFoodInteractionChecker",
    "InteractionResult",
    "DRUG_FOOD_INTERACTIONS",
]
