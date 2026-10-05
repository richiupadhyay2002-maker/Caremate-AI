"""Interactive demo for Caremate AI — zero API keys required."""

from __future__ import annotations

from caremate.models.patient import PatientContext, MedicationEntry, AllergyEntry
from caremate.pipeline import CarematePipeline
from caremate.utils.config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Sample patient data (for demo)
# ---------------------------------------------------------------------------
SAMPLE_PATIENT = PatientContext(
    patient_id="patient_001",
    name="John Doe (Demo)",
    age=68,
    sex="male",
    medical_history=["heart failure", "hypertension", "type 2 diabetes", "osteoporosis"],
    current_medications=[
        MedicationEntry(name="lisinopril", dosage="10mg", frequency="daily"),
        MedicationEntry(name="metformin", dosage="500mg", frequency="twice daily"),
        MedicationEntry(name="atorvastatin", dosage="20mg", frequency="daily"),
        MedicationEntry(name="warfarin", dosage="5mg", frequency="daily"),
    ],
    allergies=[AllergyEntry(substance="penicillin", reaction="rash", severity="mild")],
    dietary_restrictions=["low sodium", "limit vitamin k"],
    recent_weight=72.5,
    height=175,
    lab_results={"albumin": 3.4, "glucose": 142, "sodium": 135},
    notes="Patient reports occasional appetite loss and difficulty eating large meals.",
)

SAMPLE_DOCUMENTS = [
    """PATIENT HISTORY
The patient is a 68-year-old male with history of heart failure, hypertension,
type 2 diabetes, and osteoporosis. On lisinopril, metformin,
atorvastatin, and warfarin for 6 months.

MEDICATIONS
- Lisinopril 10mg daily (ACE inhibitor)
- Metformin 500mg twice daily
- Atorvastatin 20mg daily
- Warfarin 5mg daily (blood thinner — monitor INR)

DIETARY INSTRUCTIONS
- Limit sodium to less than 2,000 mg per day
- Avoid grapefruit juice (interferes with atorvastatin)
- Avoid cranberry juice (interferes with warfarin)
- Increase protein intake for muscle maintenance
- Ensure adequate calcium (1200 mg daily) for osteoporosis
- Take warfarin consistently; avoid sudden vitamin K changes
""",
    """NUTRITIONAL ASSESSMENT
Signs of mild malnutrition risk. Weight loss ~3% recently. Serum albumin 3.4 g/dL (low).
Appetite poor, difficulty eating large meals.

RECOMMENDATIONS
- High-protein, small, frequent meals
- Protein shakes or smoothies if solid food insufficient
- Calcium citrate supplements (better absorbed)
- Vitamin D supplementation (800 IU daily)
- Monitor INR weekly while on warfarin with dietary changes
""",
]


def main():
    """Run the interactive demo."""
    print("=" * 72)
    print("  Caremate AI — Phase 1 Interactive Demo")
    print("  Provider: Mock (zero API keys required)")
    print("=" * 72)

    pipeline = CarematePipeline(use_mock=True)
    pipeline.add_documents(SAMPLE_DOCUMENTS, patient_id=SAMPLE_PATIENT.patient_id)

    print(f"\nLoaded sample patient: {SAMPLE_PATIENT.name}")
    print(f"  Age: {SAMPLE_PATIENT.age} | Conditions: {', '.join(SAMPLE_PATIENT.medical_history)}")
    print(f"  Medications: {', '.join([m.name for m in SAMPLE_PATIENT.current_medications])}")
    print(f"  Indexed documents for patient='{SAMPLE_PATIENT.patient_id}'")
    print()

    from caremate.nutrition.qa import NutritionQA
    from caremate.nutrition.malnutrition_watcher import MalnutritionWatcher

    qa = NutritionQA(pipeline)
    watcher = MalnutritionWatcher(score_threshold=0.25)

    # Silent doctor-side check on startup
    alert = watcher.check(SAMPLE_PATIENT)
    if alert and alert.requires_attention:
        print("=" * 72)
        print("  ⚠ DOCTOR ALERT — Malnutrition Risk Detected")
        print("=" * 72)
        print(f"  Risk Score: {alert.risk_score} | Level: {alert.risk_level}")
        print(f"  Factors: {', '.join(alert.factors)}")
        print(f"  Recommendation: {alert.recommendation}")
        print()

    print("Ask nutrition or health questions. Type 'quit' to exit.\n")

    while True:
        try:
            query = input("🩺 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        response = qa.answer(query=query, patient=SAMPLE_PATIENT)
        _ = watcher.check(SAMPLE_PATIENT)  # silent post-check

        print(f"\n🤖 Caremate: {response.response}")
        print(f"   Confidence: {response.confidence:.2f}")
        if response.safety_flags:
            print(f"   Safety Flags: {', '.join(response.safety_flags)}")
        if response.citations:
            print(f"   Citations ({len(response.citations)}):")
            for c in response.citations:
                snip = c.text_snippet[:100] + "..." if len(c.text_snippet) > 100 else c.text_snippet
                print(f"     • [{c.section}] {snip}")
        print()

    pipeline.close()
    watcher.clear()


if __name__ == "__main__":
    main()
