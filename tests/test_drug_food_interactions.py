"""Comprehensive unit tests for caremate.guardrails.drug_food_interactions.

Covers:
- Positive cases (known interactions detected)
- Negative cases (safe combinations, unknown drugs)
- Edge cases (case sensitivity, whitespace, severity escalation,
  empty inputs, custom knowledge bases)
"""

import pytest

from caremate.guardrails.drug_food_interactions import (
    DRUG_FOOD_INTERACTIONS,
    INTERACTION_SEVERITY,
    DrugFoodInteractionChecker,
    InteractionResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def checker():
    """Checker wired to the real knowledge base."""
    return DrugFoodInteractionChecker()


# ---------------------------------------------------------------------------
# Positive cases
# ---------------------------------------------------------------------------

class TestPositiveDetection:
    """Known drug + contraindicated food pairs are detected."""

    def test_warfarin_with_spinach(self, checker):
        result = checker.check(
            patient_medications=["warfarin"],
            dietary_recommendations=["eat more spinach"],
        )
        assert result.has_interactions is True
        assert result.severity == "major"
        assert any("warfarin + spinach" in i for i in result.interactions)

    def test_atorvastatin_with_grapefruit(self, checker):
        result = checker.check(
            patient_medications=["atorvastatin"],
            dietary_recommendations=["grapefruit juice with breakfast"],
        )
        assert result.has_interactions is True
        assert result.severity == "moderate"

    def test_multiple_meds_and_foods(self, checker):
        result = checker.check(
            patient_medications=["warfarin", "lisinopril"],
            dietary_recommendations=["kale", "potassium supplement"],
        )
        assert result.has_interactions is True
        assert len(result.interactions) >= 2

    def test_max_severity_escalates_to_major(self, checker):
        """A minor drug plus a major drug yields 'major' overall."""
        result = checker.check(
            patient_medications=["metformin", "warfarin"],
            dietary_recommendations=["alcohol", "spinach"],
        )
        assert result.has_interactions is True
        assert result.severity == "major"

    def test_partial_food_match_in_joined_text(self, checker):
        """A contraindicated food appearing inside a longer string matches."""
        result = checker.check(
            patient_medications=["ciprofloxacin"],
            dietary_recommendations=["avoid dairy products and calcium"],
        )
        assert result.has_interactions is True

    def test_reason_mentions_max_severity(self, checker):
        result = checker.check(
            patient_medications=["phenelzine"],
            dietary_recommendations=["aged cheese"],
        )
        assert "major" in result.reason


# ---------------------------------------------------------------------------
# Negative cases
# ---------------------------------------------------------------------------

class TestNegativeDetection:
    """Safe or unknown combinations produce no interactions."""

    def test_unknown_drug(self, checker):
        result = checker.check(
            patient_medications=["placebo_magical_dust"],
            dietary_recommendations=["spinach", "kale"],
        )
        assert result.has_interactions is False
        assert result.interactions == []
        assert result.severity == "none"

    def test_known_drug_but_safe_foods(self, checker):
        result = checker.check(
            patient_medications=["warfarin"],
            dietary_recommendations=["rice", "chicken", "apples"],
        )
        assert result.has_interactions is False

    def test_reason_for_no_interactions(self, checker):
        result = checker.check([], [])
        assert "No known drug-food interactions" in result.reason

    def test_default_severity_is_none(self):
        result = InteractionResult(has_interactions=False)
        assert result.severity == "none"
        assert result.interactions == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Boundary and robustness cases."""

    def test_empty_medications_list(self, checker):
        result = checker.check([], ["spinach"])
        assert result.has_interactions is False

    def test_empty_dietary_recommendations(self, checker):
        result = checker.check(["warfarin"], [])
        assert result.has_interactions is False

    def test_both_lists_empty(self, checker):
        result = checker.check([], [])
        assert result.has_interactions is False
        assert result.severity == "none"

    def test_case_insensitivity(self, checker):
        result = checker.check(
            patient_medications=["WARFARIN"],
            dietary_recommendations=["SPINACH"],
        )
        assert result.has_interactions is True

    def test_whitespace_is_stripped(self, checker):
        result = checker.check(
            patient_medications=["  warfarin  "],
            dietary_recommendations=["  spinach  "],
        )
        assert result.has_interactions is True

    def test_patient_context_ignored_but_accepted(self, checker, dummy_context):
        """Passing patient_context must not break anything."""
        result = checker.check(
            ["warfarin"], ["spinach"], patient_context=dummy_context,
        )
        assert result.has_interactions is True

    def test_substring_of_food_matches(self, checker):
        """'cranberry' is in the list, so 'cranberry juice cocktail' matches."""
        result = checker.check(["warfarin"], ["cranberry juice cocktail"])
        assert result.has_interactions is True

    def test_repeated_detection_not_duplicated_per_food(self, checker):
        """Each (drug, food) pair appears at most once in results."""
        result = checker.check(["warfarin"], ["spinach spinach spinach"])
        # 'spinach' matches once against the joined diet text
        warfarin_spinach = [i for i in result.interactions if "warfarin + spinach" in i]
        assert len(warfarin_spinach) == 1

    @pytest.mark.parametrize("drug,food,expected_severity", [
        ("warfarin", "spinach", "major"),
        ("levothyroxine", "calcium", "moderate"),
        ("ibuprofen", "alcohol", "minor"),
        ("unknown_drug_x", "spinach", None),  # not in KB -> no interaction
    ])
    def test_severity_matrix(self, drug, food, expected_severity):
        result = DrugFoodInteractionChecker().check([drug], [food])
        if expected_severity is None:
            assert result.has_interactions is False
        else:
            assert result.severity == expected_severity


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class TestInternalHelpers:
    def test_get_severity_known_drug(self, checker):
        assert checker._get_severity("warfarin") == "major"
        assert checker._get_severity("metformin") == "minor"

    def test_get_severity_unlisted_defaults_to_moderate(self, checker):
        # A drug present in the KB but not in INTERACTION_SEVERITY
        unlisted = next(
            (d for d in DRUG_FOOD_INTERACTIONS
             if d not in {x for drugs in INTERACTION_SEVERITY.values() for x in drugs}),
            None,
        )
        if unlisted is not None:
            assert checker._get_severity(unlisted) == "moderate"

    def test_get_severity_unknown_drug(self, checker):
        assert checker._get_severity("not_in_kb") == "moderate"

    def test_upgrade_severity(self):
        up = DrugFoodInteractionChecker._upgrade_severity
        assert up("none", "minor") == "minor"
        assert up("none", "major") == "major"
        assert up("moderate", "minor") == "moderate"  # never downgrades
        assert up("major", "major") == "major"

    def test_custom_knowledge_base(self):
        custom = {"superdrug": ["bogus food"]}
        checker = DrugFoodInteractionChecker(interactions=custom)
        result = checker.check(["superdrug"], ["bogus food"])
        assert result.has_interactions is True
        # Real KB entries are gone
        assert checker.check(["warfarin"], ["spinach"]).has_interactions is False


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_context():
    from caremate.models.patient import PatientContext
    return PatientContext(patient_id="p1")
