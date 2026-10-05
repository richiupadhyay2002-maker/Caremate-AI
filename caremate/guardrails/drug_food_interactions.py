"""Drug-food interaction checking guardrail.

Checks patient medications against dietary recommendations and known
drug-food interaction pairs to prevent harmful combinations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from caremate.models.response import SafetyFlag


# Known drug-food interaction knowledge base
# Format: {drug_name_lower: [contraindicated_foods_lower]}
DRUG_FOOD_INTERACTIONS: dict[str, list[str]] = {
    # Warfarin
    "warfarin": ["vitamin k", "green leafy", "spinach", "kale", "broccoli",
                 "brussels sprouts", "cranberry juice", "cranberry",
                 "vitamin e supplements"],
    # ACE Inhibitors
    "lisinopril": ["potassium", "salt substitutes", "potassium chloride"],
    "enalapril": ["potassium", "salt substitutes"],
    "ramipril": ["potassium", "salt substitutes"],
    "captopril": ["potassium", "salt substitutes"],
    # ARBs
    "losartan": ["potassium", "salt substitutes"],
    "valsartan": ["potassium", "salt substitutes"],
    # Antibiotics
    "levothyroxine": ["calcium", "iron supplements", "antacids", "fiber supplements",
                      "soy products", "walnuts"],
    "tetracycline": ["calcium", "iron", "magnesium", "aluminum", "dairy products",
                     "milk", "cheese", "yogurt"],
    "ciprofloxacin": ["calcium", "iron", "magnesium", "dairy products",
                      "cranberry juice"],
    "fluoroquinolone": ["calcium", "iron", "magnesium", "dairy products"],
    # MAOIs
    "phenelzine": ["tyramine", "aged cheese", "red wine", "chocolate",
                   "cured meats", "fermented foods", "soy sauce", "coffee"],
    "tranylcypromine": ["tyramine", "aged cheese", "red wine"],
    # Diuretics
    "furosemide": ["potassium", "salt substitutes", "lithium"],
    "spironolactone": ["potassium", "salt substitutes"],
    # Statins
    "atorvastatin": ["grapefruit", "grapefruit juice"],
    "simvastatin": ["grapefruit", "grapefruit juice"],
    "lovastatin": ["grapefruit", "grapefruit juice"],
    # Diabetes meds
    "metformin": ["high alcohol intake", "large amounts of alcohol"],
    "insulin": ["high alcohol intake", "emergency alcohol consumption"],
    # Blood thinners
    "rivaroxaban": ["cranberry juice", "ginkgo", "garlic supplements",
                    "ginseng"],
    "apixaban": ["ginkgo", "garlic supplements", "ginseng"],
    "dabigatran": ["ginkgo", "garlic supplements", "ginseng"],
    # NSAIDs
    "ibuprofen": ["alcohol", "high alcohol intake"],
    "naproxen": ["alcohol", "high alcohol intake"],
    # Thyroid
    "methimazole": ["vitamin k"],
    "propylthiouracil": ["vitamin k"],
}

# Severity levels for interactions
INTERACTION_SEVERITY: dict[str, str] = {
    "major": ["warfarin", "phenelzine", "tranylcypromine", "ciprofloxacin",
              "fluoroquinolone", "tetracycline"],
    "moderate": ["levothyroxine", "atorvastatin", "simvastatin", "rivaroxaban",
                 "apixaban", "dabigatran", "lisinopril", "losartan", "furosemide"],
    "minor": ["metformin", "ibuprofen"],
}


@dataclass
class InteractionResult:
    """Result of a drug-food interaction check."""
    has_interactions: bool
    interactions: list[str] = field(default_factory=list)
    severity: str = "none"  # "none", "minor", "moderate", "major"
    reason: str = ""


class DrugFoodInteractionChecker:
    """Checks for dangerous drug-food interactions given a patient's medications."""

    def __init__(self, interactions: dict[str, list[str]] | None = None):
        self._interactions = interactions or DRUG_FOOD_INTERACTIONS

    def check(
        self,
        patient_medications: list[str],
        dietary_recommendations: list[str],
        patient_context=None,
    ) -> InteractionResult:
        """Check if any patient medications interact with recommended foods.

        Args:
            patient_medications: List of medication names the patient is taking.
            dietary_recommendations: List of food/diet recommendations.
            patient_context: Optional PatientContext for additional context.

        Returns:
            InteractionResult with any detected interactions.
        """
        detected: list[str] = []
        max_severity = "none"

        meds_lower = [m.lower().strip() for m in patient_medications]
        diet_lower = [d.lower().strip() for d in dietary_recommendations]
        all_diet_text = " ".join(diet_lower)

        for med in meds_lower:
            if med not in self._interactions:
                continue
            contraindicated = self._interactions[med]
            for food in contraindicated:
                if food in all_diet_text:
                    severity = self._get_severity(med)
                    detected.append(f"{med} + {food} (severity: {severity})")
                    max_severity = self._upgrade_severity(max_severity, severity)

        if detected:
            return InteractionResult(
                has_interactions=True,
                interactions=detected,
                severity=max_severity,
                reason=f"Drug-food interactions detected: {'; '.join(detected)}. "
                       f"Max severity: {max_severity}.",
            )

        return InteractionResult(
            has_interactions=False,
            severity="none",
            reason="No known drug-food interactions detected.",
        )

    def _get_severity(self, drug_name: str) -> str:
        for sev, drugs in INTERACTION_SEVERITY.items():
            if drug_name in [d.lower() for d in drugs]:
                return sev
        return "moderate"

    @staticmethod
    def _upgrade_severity(current: str, new: str) -> str:
        order = ["none", "minor", "moderate", "major"]
        ci, ni = order.index(current), order.index(new)
        return new if ni > ci else current
