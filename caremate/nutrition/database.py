"""Nutrition knowledge database.

Curated medical nutrition knowledge: food groups, nutrient content,
dietary recommendations for medical conditions, and malnutrition risk factors.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Food group definitions
# ---------------------------------------------------------------------------
FOOD_GROUPS: dict[str, list[str]] = {
    "protein": [
        "chicken", "turkey", "fish", "eggs", "beef", "pork",
        "beans", "lentils", "tofu", "nuts", "seeds",
        "Greek yogurt", "cottage cheese", "protein powder",
    ],
    "dairy_calcium": [
        "milk", "cheese", "yogurt", "butter", "cream",
        "fortified plant milk", "sardines", "salmon with bones",
    ],
    "leafy_greens": [
        "spinach", "kale", "broccoli", "brussels sprouts",
        "collard greens", "swiss chard", "arugula",
    ],
    "fruits": [
        "apple", "banana", "orange", "berries", "grapefruit",
        "kiwi", "avocado", "tomato", "lemon",
    ],
    "grains": [
        "rice", "oats", "quinoa", "bread", "pasta",
        "cereal", "barley", "whole wheat",
    ],
    "hydration": [
        "water", "herbal tea", "broth", "electrolyte solutions",
    ],
}

# ---------------------------------------------------------------------------
# Medical condition → dietary recommendation mapping
# ---------------------------------------------------------------------------
CONDITION_DIETARY_RECOMMENDATIONS: dict[str, dict[str, list[str]]] = {
    "chronic kidney disease": {
        "recommend": ["limit potassium foods like bananas and oranges",
                      "limit phosphorus", "choose high-quality protein in moderation"],
        "avoid": ["salt substitutes with potassium chloride"],
    },
    "heart failure": {
        "recommend": ["limit sodium to less than 2,300 mg per day",
                      "limit fluid intake if advised", "choose lean proteins"],
        "avoid": ["processed foods high in sodium", "added salt"],
    },
    "diabetes": {
        "recommend": ["pair carbs with protein for stable glucose",
                      "choose fiber-rich foods", "maintain consistent meal timing"],
        "avoid": ["refined sugars", "sugary beverages"],
    },
    "osteoporosis": {
        "recommend": ["aim for 1200 mg calcium daily",
                      "ensure adequate vitamin D", "include exercise"],
        "avoid": ["excessive caffeine", "high sodium intake"],
    },
    "hypertension": {
        "recommend": ["follow DASH eating pattern",
                      "limit sodium to less than 1,500 mg if possible"],
        "avoid": ["pickled or cured foods", "canned soups"],
    },
}


def get_dietary_recommendations(conditions: list[str]) -> tuple[list[str], list[str]]:
    """Get dietary recommendations for a list of medical conditions.

    Returns:
        Tuple of (recommended_items, foods_to_avoid).
    """
    recommendations: list[str] = []
    avoid: list[str] = []

    for condition in conditions:
        cl = condition.lower().strip()
        matched = False
        for known, advice in CONDITION_DIETARY_RECOMMENDATIONS.items():
            if known in cl or cl in known:
                recommendations.extend(advice["recommend"])
                avoid.extend(advice["avoid"])
                matched = True
        if not matched:
            recommendations.append("Follow a balanced diet appropriate for your condition")

    return recommendations, avoid
    return recommendations, avoid


# ---------------------------------------------------------------------------
# Malnutrition risk factors
# ---------------------------------------------------------------------------
MALNUTRITION_RISK_FACTORS: list[dict] = [
    {"name": "low_albumin", "field": "albumin", "threshold": 3.5, "operator": "<",
     "weight": 0.3, "desc": "Serum albumin below 3.5 g/dL indicates malnutrition"},
    {"name": "weight_loss", "field": "weight_loss_percent", "threshold": 5.0,
     "operator": ">", "weight": 0.25, "desc": "Unintentional weight loss >5% in 30 days"},
    {"name": "low_bmi", "field": "bmi", "threshold": 18.5, "operator": "<",
     "weight": 0.2, "desc": "BMI below 18.5 is underweight"},
    {"name": "appetite_loss", "field": "appetite_issues", "threshold": 1,
     "operator": "exists", "weight": 0.15, "desc": "Reported appetite loss or eating difficulty"},
    {"name": "chronic_disease", "field": "chronic_count", "threshold": 2,
     "operator": ">=", "weight": 0.1, "desc": "Multiple chronic conditions increase risk"},
]


def assess_malnutrition_risk(patient_context) -> dict:
    """Assess malnutrition risk for a patient.

    Checks lab results, weight trends, BMI, appetite, and chronic conditions.

    Returns dict with 'risk_score' (0-1), 'risk_level' ('low'|'moderate'|'high'),
    'factors' (list), 'alert' (bool), and 'recommendation' (str).
    """
    score = 0.0
    factors: list[str] = []

    # Albumin
    albumin = _get_nested(patient_context, "lab_results", "albumin")
    if albumin is not None and albumin < 3.5:
        score += 0.3
        factors.append(f"Low serum albumin ({albumin} g/dL)")

    # Weight loss
    wl = _get_nested(patient_context, "weight_loss_percent")
    if wl is not None and wl > 5.0:
        score += 0.25
        factors.append(f"Unintentional weight loss ({wl:.1f}%)")

    # BMI
    bmi = _get_nested(patient_context, "bmi")
    if bmi is not None and bmi < 18.5:
        score += 0.2
        factors.append(f"Low BMI ({bmi:.1f})")

    # Appetite issues
    notes = str(_get_nested(patient_context, "notes") or "")
    if any(w in notes.lower() for w in ["appetite", "not eating", "swallow", "eat"]):
        score += 0.15
        factors.append("Reported appetite loss or eating difficulties")

    # Chronic conditions
    history = _get_nested(patient_context, "medical_history", as_list=True)
    if history and len(history) >= 2:
        score += 0.1
        factors.append(f"Multiple chronic conditions ({len(history)})")

    if score >= 0.5:
        risk_level, alert = "high", True
    elif score >= 0.3:
        risk_level, alert = "moderate", True
    else:
        risk_level, alert = "low", False

    return {
        "risk_score": round(score, 2),
        "risk_level": risk_level,
        "factors": factors,
        "alert": alert,
        "recommendation": (
            "Refer to dietitian for nutritional assessment" if alert
            else "Continue routine monitoring"
        ),
    }


def _get_nested(obj, *keys, as_list: bool = False, default=None):
    """Safely access nested dict/object attributes."""
    current = obj
    for key in keys:
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            current = getattr(current, key, default)
    if as_list and current is None:
        return []
    return current

