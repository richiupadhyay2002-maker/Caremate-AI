"""Silent doctor-side malnutrition risk watcher.

Runs automatically after each nutrition Q&A session, analyzing the
patient's data for malnutrition risk indicators and generating alerts
for the doctor's review — without interrupting the patient-facing response.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional

from caremate.models.patient import PatientContext
from caremate.nutrition.database import assess_malnutrition_risk


@dataclass
class MalnutritionRiskAlert:
    """A malnutrition risk alert for doctor review."""
    patient_id: str
    risk_score: float
    risk_level: str  # "low", "moderate", "high"
    factors: list[str] = field(default_factory=list)
    recommendation: str = ""
    timestamp: str = field(default_factory=lambda: _dt.datetime.now().isoformat())
    requires_attention: bool = False

    def to_dict(self) -> dict:
        return {
            "patient_id": self.patient_id,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "factors": self.factors,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
            "requires_attention": self.requires_attention,
        }


class MalnutritionWatcher:
    """Silent background analyzer for malnutrition risk.

    Not visible to the patient. Runs after nutrition Q&A and generates
    alerts only for the doctor's dashboard.
    """

    def __init__(self, score_threshold: float = 0.3):
        """Initialize the watcher.

        Args:
            score_threshold: Risk score at or above which an alert is generated.
        """
        self._threshold = score_threshold
        self._alerts: list[MalnutritionRiskAlert] = []

    def check(self, patient: PatientContext) -> Optional[MalnutritionRiskAlert]:
        """Run a malnutrition risk assessment for the patient.

        Args:
            patient: Patient context to assess.

        Returns:
            MalnutritionRiskAlert if risk is elevated, None otherwise.
        """
        result = assess_malnutrition_risk(patient)

        alert = MalnutritionRiskAlert(
            patient_id=patient.patient_id,
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
            factors=result["factors"],
            recommendation=result["recommendation"],
            requires_attention=result["alert"],
        )

        # Log all checks, but only store alerts above threshold
        if result["risk_score"] >= self._threshold:
            self._alerts.append(alert)

        return alert if alert.requires_attention else None

    def get_alerts(self, patient_id: Optional[str] = None) -> list[MalnutritionRiskAlert]:
        """Return stored alerts, optionally filtered by patient."""
        if patient_id:
            return [a for a in self._alerts if a.patient_id == patient_id]
        return list(self._alerts)

    def clear(self) -> None:
        """Clear all stored alerts."""
        self._alerts.clear()

    @property
    def alert_count(self) -> int:
        return len(self._alerts)

    @property
    def recent_alerts(self) -> list[MalnutritionRiskAlert]:
        """Return alerts requiring attention, sorted by timestamp."""
        return [a for a in self._alerts if a.requires_attention]
