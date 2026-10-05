"""Red-flag symptom detection guardrail.

Detects dangerous medical symptoms that require immediate attention.
When detected, the pipeline short-circuits to prevent harmful responses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SymptomResult:
    """Result of a red-flag symptom check."""
    detected: bool
    flags: list[str] = field(default_factory=list)
    severity: str = "none"  # "none", "caution", "warning", "emergency"
    reason: str = ""


RED_FLAG_SYMPTOMS: list[tuple[str, str, str]] = [
    # Emergency-level
    (r"\bchest\s+pain\b", "chest_pain", "emergency"),
    (r"\bchest\s+tightness\b", "chest_tightness", "emergency"),
    (r"\bdifficulty\s+breathing\b", "difficulty_breathing", "emergency"),
    (r"\bshortness\s+of\s+breath\b", "shortness_of_breath", "emergency"),
    (r"\b(severe|worst)\s+(?:headache|head\s+pain)\b", "severe_headache", "emergency"),
    (r"\bsudden\s+(?:numbness|weakness|paralysis)\b", "sudden_weakness", "emergency"),
    (r"\bsudden\s+slurred\s+speech\b", "slurred_speech", "emergency"),
    (r"\b(unconscious|unresponsive|fainted|fainting)\b", "loss_of_consciousness", "emergency"),
    (r"\bsevere\s+abdominal\s+pain\b", "severe_abdominal_pain", "emergency"),
    (r"\b(severe|persistent)\s+(?:vomiting|bleeding)\b", "severe_bleeding", "emergency"),
    # Warning-level
    (r"\b(unintended|unexplained|significant)\s+weight\s+loss\b", "unexplained_weight_loss", "warning"),
    (r"\bpersistent\s+fever\b", "persistent_fever", "warning"),
    (r"\bsudden\s+vision\s+changes\b", "vision_changes", "warning"),
    (r"\b(severe|constant)\s+(?:dizziness|lightheadedness)\b", "severe_dizziness", "warning"),
    (r"\b(heart\s+palpitations|sudden\s+irregular\s+heartbeat)\b", "heart_palpitations", "warning"),
    (r"\b(dehydration|severely\s+dehydrated)\b", "dehydration", "warning"),
    (r"\b(skin\s+yellowing|jaundice)\b", "jaundice", "warning"),
    # Caution-level
    (r"\b(not\s+eating|loss\s+of\s+appetite|poor\s+appetite)\b", "appetite_loss", "caution"),
    (r"\b(unable\s+to\s+swallow|difficulty\s+swallowing)\b", "swallowing_difficulty", "caution"),
    (r"\b(constant\s+fatigue|extreme\s+fatigue|severe\s+fatigue)\b", "extreme_fatigue", "caution"),
    (r"\bnausea\s+(and|&)\s+vomiting\b", "nausea_vomiting", "caution"),
]

# Alias for backward compatibility
RED_FLAG_SYMBOLS = RED_FLAG_SYMPTOMS


class RedFlagDetector:
    """Detects red-flag medical symptoms in user input or AI responses."""

    def __init__(self):
        self._compiled: list[tuple[re.Pattern, str, str]] = [
            (re.compile(pat, re.IGNORECASE), label, sev)
            for pat, label, sev in RED_FLAG_SYMPTOMS
        ]

    def check(self, text: str) -> SymptomResult:
        """Scan text for red-flag symptoms.

        Returns:
            SymptomResult with detected flags and severity level.
        """
        detected_flags: list[str] = []
        max_severity = "none"

        for pattern, label, severity in self._compiled:
            if pattern.search(text):
                detected_flags.append(label)
                if severity == "emergency":
                    max_severity = "emergency"
                elif severity == "warning" and max_severity != "emergency":
                    max_severity = "warning"
                elif severity == "caution" and max_severity == "none":
                    max_severity = "caution"

        if detected_flags:
            return SymptomResult(
                detected=True,
                flags=detected_flags,
                severity=max_severity,
                reason=f"Red-flag symptom(s) detected: {', '.join(detected_flags)}. "
                       f"Severity: {max_severity}. Seek medical attention.",
            )

        return SymptomResult(
            detected=False, severity="none",
            reason="No red-flag symptoms detected",
        )

    @property
    def all_symptoms(self) -> list[str]:
        """Return list of all known red-flag symptom labels."""
        return [label for _, label, _ in RED_FLAG_SYMPTOMS]
