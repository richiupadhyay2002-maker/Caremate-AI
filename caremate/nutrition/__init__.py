"""Nutrition feature: Q&A and malnutrition risk watcher."""

from caremate.nutrition.qa import NutritionQA, NutritionContext
from caremate.nutrition.malnutrition_watcher import MalnutritionWatcher, MalnutritionRiskAlert
from caremate.nutrition.database import (
    FOOD_GROUPS,
    get_dietary_recommendations,
    assess_malnutrition_risk,
    MALNUTRITION_RISK_FACTORS,
)

__all__ = [
    "NutritionQA",
    "NutritionContext",
    "MalnutritionWatcher",
    "MalnutritionRiskAlert",
    "FOOD_GROUPS",
    "get_dietary_recommendations",
    "assess_malnutrition_risk",
    "MALNUTRITION_RISK_FACTORS",
]
