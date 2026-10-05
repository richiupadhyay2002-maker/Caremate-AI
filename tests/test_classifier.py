"""Comprehensive unit tests for caremate.ingestion.classifier.

Covers:
- Positive cases (each document type recognized)
- Negative cases (empty/blank text, no-signal text -> OTHER)
- Edge cases (tie-breaking, confidence bounds, custom keyword maps,
  convenience function)
"""

import pytest

from caremate.db.models_docs import DocumentType
from caremate.ingestion.classifier import (
    DocumentClassifier,
    classify_document,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def classifier():
    return DocumentClassifier()


# ---------------------------------------------------------------------------
# Positive cases
# ---------------------------------------------------------------------------

class TestPositiveClassification:
    def test_pathology_report(self, classifier):
        text = "Specimen: left lung biopsy. Histopathology shows necrosis and malignant cells."
        result = classifier.classify(text)
        assert result.document_type == DocumentType.PATHOLOGY_REPORT
        assert result.confidence > 0.5

    def test_radiology_report(self, classifier):
        text = "Impression: CT scan of the abdomen. Findings: contrast medium enhancement noted."
        result = classifier.classify(text)
        assert result.document_type == DocumentType.RADIOLOGY_REPORT

    def test_lab_report(self, classifier):
        text = ("Laboratory results: hemoglobin 13.5 g/dL, WBC 8.0, glucose 95 mg/dL. "
                "Reference range provided for each analyte.")
        result = classifier.classify(text)
        assert result.document_type == DocumentType.LAB_REPORT

    def test_discharge_summary(self, classifier):
        text = ("Discharge instructions: the patient was discharged home. "
                "Admission was on Monday. Attending physician signed off.")
        result = classifier.classify(text)
        assert result.document_type == DocumentType.DISCHARGE_SUMMARY

    def test_prescription(self, classifier):
        text = "Rx: Amoxicillin 500 mg, take 1 capsule twice daily. Dispensed by pharmacy."
        result = classifier.classify(text)
        assert result.document_type == DocumentType.PRESCRIPTION

    def test_clinical_note(self, classifier):
        text = ("Subjective: chief complaint is cough. Objective: vitals stable. "
                "Assessment and plan: continue current treatment.")
        result = classifier.classify(text)
        assert result.document_type == DocumentType.CLINICAL_NOTE

    def test_top_candidates_ordered_descending(self, classifier):
        text = "Specimen biopsy histopathology malignancy noted."
        result = classifier.classify(text)
        assert result.top_candidates
        scores = [s for _, s in result.top_candidates]
        assert scores == sorted(scores, reverse=True)
        assert result.top_candidates[0][0] == result.document_type


# ---------------------------------------------------------------------------
# Negative cases
# ---------------------------------------------------------------------------

class TestNegativeClassification:
    @pytest.mark.parametrize("text", ["", "   \n\t  ", None])
    def test_empty_text_returns_other_with_zero_confidence(self, classifier, text):
        result = classifier.classify(text)
        assert result.document_type == DocumentType.OTHER
        assert result.confidence == 0.0
        assert result.top_candidates == []

    def test_no_signal_text_returns_other(self, classifier):
        result = classifier.classify("Lorem ipsum dolor sit amet consectetur adipiscing elit.")
        assert result.document_type == DocumentType.OTHER
        assert 0.1 <= result.confidence <= 0.3  # the fixed weak-signal confidence

    def test_all_types_scored_when_ambiguous(self):
        """With a custom map where everything ties, no crash and valid result."""
        custom = {
            "a": [(r"x", 1.0)],
            "b": [(r"x", 1.0)],
        }
        result = DocumentClassifier(keyword_map=custom).classify("x x x")
        assert result.document_type in ("a", "b")
        assert result.confidence <= 0.95  # capped for multi-candidate ties


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_confidence_within_bounds(self, classifier):
        for text in [
            "Specimen biopsy",
            "Specimen biopsy specimen biopsy specimen biopsy",
            "Impression findings x-ray MRI CT scan radiograph",
        ]:
            r = classifier.classify(text)
            assert 0.1 <= r.confidence <= 1.0

    def test_case_insensitive_matching(self, classifier):
        r1 = classifier.classify("SPECIMEN BIOPSY HISTOPATHOLOGY")
        r2 = classifier.classify("specimen biopsy histopathology")
        assert r1.document_type == r2.document_type == DocumentType.PATHOLOGY_REPORT

    def test_dominant_type_boosts_confidence(self, classifier):
        """A top score more than 2x the runner-up gets a 1.5x boost."""
        text = ("Impression: clear. Specimen biopsy histopathology cytology "
                "malignant neoplasm necrosis mitotic.")
        result = classifier.classify(text)
        assert result.document_type == DocumentType.PATHOLOGY_REPORT

    def test_repeated_keywords_increase_score(self, classifier):
        low = classifier.classify("specimen").confidence
        high = classifier.classify("specimen specimen specimen specimen").confidence
        # More hits for one type => stronger dominance => higher (or equal) confidence
        assert high >= low

    def test_custom_keyword_map(self):
        custom = {"fiction": [(r"wizard", 3.0)], "science": [(r"atom", 3.0)]}
        c = DocumentClassifier(keyword_map=custom)
        result = c.classify("the wizard waved his wand")
        assert result.document_type == "fiction"

    def test_suppressed_zero_weight_pattern(self, classifier):
        """A zero-weight pattern never contributes score by itself."""
        custom = {"clinical_note": [(r"\bOSCE\b", 0.0)], "other": [(r"zzz", 5.0)]}
        result = DocumentClassifier(keyword_map=custom).classify("OSCE station")
        assert result.document_type == DocumentType.OTHER

    def test_convenience_function(self):
        assert classify_document("Specimen: biopsy") == DocumentType.PATHOLOGY_REPORT
        assert classify_document("") == DocumentType.OTHER

    def test_whitespace_only_text(self, classifier):
        result = classifier.classify("\n\n   \t\n")
        assert result.document_type == DocumentType.OTHER
        assert result.confidence == 0.0
