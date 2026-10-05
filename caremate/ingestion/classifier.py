"""Document classification into the fixed DOCUMENT_TYPES set.

Uses keyword-based heuristics so the pipeline works without external LLM
calls during ingestion — matching the existing mock-provider architecture.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from caremate.db.models_docs import DocumentType

# Each document type maps to a list of (pattern, weight) tuples.
# Patterns are matched case-insensitively against the document text.
_TYPE_KEYWORDS: dict[str, list[tuple[str, float]]] = {
    DocumentType.PATHOLOGY_REPORT: [
        (r"\bspecimen\b", 3.0),
        (r"\bbiopsy\b", 3.0),
        (r"\bhistopathology\b", 3.0),
        (r"\bcytology\b", 3.0),
        (r"\bimmunohistochemistry\b", 2.0),
        (r"\bvascular\spinion\b", 1.5),
        (r"\bnecrosis\b", 1.5),
        (r"\bmitotic\b", 1.5),
        (r"\bmalignan", 2.0),
        (r"\bneoplasm", 2.0),
        (r"\binfiltrate\b", 1.0),
        (r"\bmetaplasia\b", 1.0),
    ],
    DocumentType.RADIOLOGY_REPORT: [
        (r"\bimpression\b", 2.0),
        (r"\bfindings\b", 2.0),
        (r"\bx-?ray\b", 2.0),
        (r"\bMRI\b", 2.0),
        (r"\bCT\s*scan\b", 2.0),
        (r"\bCT\b", 1.0),
        (r"\bradiograph", 2.0),
        (r"\bcontrast\s*medium\b", 1.5),
        (r"\bechocardiogram\b", 1.5),
        (r"\bDoppler\b", 1.5),
        (r"\bcomputed\s*tomography\b", 2.0),
    ],
    DocumentType.LAB_REPORT: [
        (r"\blab(?:oratory)?\b", 2.0),
        (r"\breference\s*range\b", 2.0),
        (r"\bhemoglobin\b", 2.0),
        (r"\bWBC\b", 2.0),
        (r"\bglucose\b", 2.0),
        (r"\bcreatinine\b", 1.5),
        (r"\bbilirubin\b", 1.5),
        (r"\bplatelet", 1.5),
        (r"\bmmol/L\b", 1.0),
        (r"\bng/mL\b", 1.0),
        (r"\bu/L\b", 1.0),
        (r"\bg/dL\b", 1.0),
        (r"\bHematocrit\b", 1.5),
    ],
    DocumentType.DISCHARGE_SUMMARY: [
        (r"\bdischarge\s*instructions?", 3.0),
        (r"\badmission\b", 2.0),
        (r"\bdischarged\b", 2.0),
        (r"\bdischarge\b", 1.5),
        (r"\bdischarged\s*to\b", 2.0),
        (r"\battending\b", 1.0),
        (r"\bhospitalization\b", 1.0),
        (r"\bward\b", 1.0),
    ],
    DocumentType.PRESCRIPTION: [
        (r"\brx\b", 2.0),
        (r"\bdispensed?\b", 2.0),
        (r"\bpharmacy\b", 2.0),
        (r"\bprescri", 2.0),
        (r"\bmedication\b", 1.0),
        (r"\bdosage\b", 1.5),
        (r"\btake\s*\d", 1.5),
        (r"\bonce\s*daily\b", 1.0),
        (r"\btwice\s*daily\b", 1.0),
        (r"\bMG\b", 0.5),
        (r"\bmg\b", 0.5),
    ],
    DocumentType.CLINICAL_NOTE: [
        (r"\bchief\s*complaint\b", 2.5),
        (r"\bosce\b", 0.0),  # suppress "CC" false positive
        (r"\bROS\b", 1.5),
        (r"\breview\s*of\s*systems\b", 2.0),
        (r"\bassessment\b", 1.5),
        (r"\bplan\b", 1.0),
        (r"\bsubjective\b", 2.0),
        (r"\bobjective\b", 2.0),
        (r"\bSOAP\b", 2.0),
        (r"\bnote\b", 1.0),
    ],
}


@dataclass
class ClassificationResult:
    """Result of classifying a document."""
    document_type: str
    confidence: float  # 0.0–1.0 confidence in the classification
    top_candidates: list[tuple[str, float]]


class DocumentClassifier:
    """Keyword-based classifier for medical documents.

    Scores each document type against keyword patterns and returns the best
    match.  Falls back to ``DocumentType.OTHER`` when no strong signal exists.
    """

    def __init__(self, keyword_map: dict[str, list[tuple[str, float]]] | None = None):
        self._keyword_map = keyword_map or _TYPE_KEYWORDS
        # Pre-compile regex patterns for performance
        self._compiled: dict[str, list[tuple[re.Pattern, float]]] = {
            dtype: [(re.compile(pat, re.IGNORECASE), w) for pat, w in patterns]
            for dtype, patterns in self._keyword_map.items()
        }

    def classify(self, text: str) -> ClassificationResult:
        """Classify a document based on its extracted text.

        Args:
            text: Full extracted document text.

        Returns:
            A :class:`ClassificationResult` with the predicted type and confidence.
        """
        if not text or not text.strip():
            return ClassificationResult(
                document_type=DocumentType.OTHER,
                confidence=0.0,
                top_candidates=[],
            )

        scores: dict[str, float] = {}
        for dtype, patterns in self._compiled.items():
            score = 0.0
            for pattern, weight in patterns:
                score += weight * len(pattern.findall(text))
            if score > 0:
                scores[dtype] = score

        if not scores:
            return ClassificationResult(
                document_type=DocumentType.OTHER,
                confidence=0.3,
                top_candidates=[],
            )

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        total = sum(scores.values())
        best_type, best_score = ranked[0]
        confidence = best_score / total if total > 0 else 0.0

        # Normalise confidence: if top score dominates, confidence is higher
        if len(ranked) > 1:
            second_score = ranked[1][1]
            if best_score > second_score * 2:
                confidence = min(1.0, confidence * 1.5)
            else:
                confidence = min(0.95, confidence)
        else:
            confidence = min(1.0, confidence * 1.3)

        confidence = max(0.1, min(1.0, confidence))
        top_candidates = [(t, s / total if total > 0 else 0.0) for t, s in ranked]

        return ClassificationResult(
            document_type=best_type,
            confidence=round(confidence, 4),
            top_candidates=top_candidates,
        )


def classify_document(text: str) -> str:
    """Convenience function: return the classified document type string."""
    return DocumentClassifier().classify(text).document_type
