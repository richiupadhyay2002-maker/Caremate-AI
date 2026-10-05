"""PII/PHI detection and redaction utilities.

This module provides:

* :func:`redact_phi` — a standalone function that scans arbitrary text and
  replaces patterns that look like protected health information with
  ``[REDACTED]``.

* :class:`PhiRedactionFilter` — a :class:`logging.Filter` that can be attached
  to any handler so that **every** log message is automatically scrubbed before
  it hits disk, stdout, or any external log-aggregator.

The patterns are deliberately conservative: they err on the side of redacting
*more* rather than *less*.  A false positive (over-redaction) is acceptable;
a false negative (leaking PHI) is not.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Pattern catalogue
# ---------------------------------------------------------------------------

# Common medication names (lowercase) — matches "warfarin 5mg daily" style.
_MEDICATIONS = [
    "warfarin", "lisinopril", "metformin", "atorvastatin", "aspirin",
    "heparin", "insulin", "digoxin", "furosemide", "spironolactone",
    "ramipril", "losartan", "valsartan", "amlodipine", "simvastatin",
    "omeprazole", "pantoprazole", "levothyroxine", "prednisone",
    "prednisolone", "methotrexate", "hydroxychloroquine", "amiodarone",
    "sotalol", "rivaroxaban", "apixaban", "dabigatran",
    "carbamazepine", "phenytoin", "levetiracetam", "lamotrigine",
    "topiramate", "colchicine", "allopurinol", "probenecid",
    "clopidogrel", "prasugrel", "ticagrelor",
]

_MED_RE = (
    r"\b(" + "|".join(_MEDICATIONS) + r")\b"
    r"(?:\s*\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|units?|tabs?|caps?))?"
    r"(?:\s+(?:daily|twice|BID|once|TID|QID|nocte|weekly|monthly))?"
)

# Lab test keywords
_LAB_KW = (
    r"HbA1c|Hemoglobin\s*A1c|glucose|BUN|creatinine|urea|"
    r"Na\+|NaCL|Sodium|potassium|K\+|chloride|CO2|bicarb|TCO2|"
    r"WBC|white\s*blood|platelets?|PLT|hematocrit|Hct|hemoglobin|Hb|"
    r"albumin|prealbumin|total\s*protein|TP|AST|ALT|SGOT|SGPT|"
    r"bilirubin|ALP|GGT|LDH|CPK|troponin|BNP|INR|PTT|aPTT|ESR|CRP|"
    r"cholesterol|LDL|HLD|HDL|triglycerides|TGL|fibrinogen"
)
_LAB_RE = r"\b(?:" + _LAB_KW + r")\b(?:\s*[:=-]?\s*\d+(?:\.\d+)?\s*\w+)?"

# Individual regex patterns (no inline (?i) — we apply re.IGNORECASE globally)
_PATTERNS: list[str] = [
    r"\b\d{3}-\d{2}-\d{4}\b",                                             # SSN
    r"\bMRN\s*[:#]\s*\d{6,10}\b",                                          # MRN
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",                 # Email
    r"\b(?:\+?1[-\s.]?)?\(?\d{3}\)?[-\s.]\d{3}[-\s.]\d{4}\b",              # Phone
    r"\b(?:DOB|Date\s*of\s*Birth|Admitted|Discharged|Birth\s*Date)"
    r"\s*[:=]?\s*\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b",                        # Dates
    r"\b\d{1,3}\s*(?:year|y|years)\s*old|\d{1,3}\s*y/o|"
    r"age\s*[:=]?\s*\d{1,3}\b",                                              # Age
    _LAB_RE,                                                                # Lab values
    _MED_RE,                                                                # Medications
]

# Compile each pattern individually
_COMPILED: list[re.Pattern] = [
    re.compile(pat, re.IGNORECASE) for pat in _PATTERNS
]

# Combined regex — wrap each in a non-capturing group for safe alternation
_REDACT_REGEX: re.Pattern = re.compile(
    "|".join(f"(?:{pat})" for pat in _PATTERNS),
    re.IGNORECASE,
)


def redact_phi(text: str) -> str:
    """Replace PHI patterns in *text* with ``[REDACTED]``.

    Args:
        text: Arbitrary string that may contain PHI.

    Returns:
        A copy of *text* with each detected PHI span replaced by
        ``[REDACTED]``.  Non-string inputs are converted via ``str()``.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return _REDACT_REGEX.sub("[REDACTED]", text)


class PhiRedactionFilter:
    """A :class:`logging.Filter` that redacts PHI from log records.

    Usage::

        import logging
        handler = logging.StreamHandler()
        handler.addFilter(PhiRedactionFilter())
        logger.addHandler(handler)

    The filter modifies ``record.msg`` and ``record.args`` in-place so that
    downstream handlers (or log aggregators) never see raw PHI, even if the
    calling code logs a medical document verbatim.
    """

    def filter(self, record) -> bool:  # noqa: D401
        try:
            if isinstance(record.msg, str):
                record.msg = redact_phi(record.msg)
            if record.args:
                record.args = tuple(
                    redact_phi(a) if isinstance(a, str) else a
                    for a in record.args
                )
        except Exception:
            # Never let redaction errors break logging
            pass
        return True
