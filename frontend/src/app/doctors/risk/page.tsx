"use client";

import Link from "next/link";
import { DEMO_PATIENTS } from "@/lib/demo-data";
import { riskAssessment } from "@/lib/ai-engine";
import { PageHeader, Card, StatusBadge } from "@/components/ui";

/**
 * Background Risk Watcher — silent by default. This overview only shows
 * patients whose real thresholds are crossed (weight loss %, albumin,
 * appetite). Patients without crossed thresholds are not listed.
 */
export default function RiskWatcherPage() {
  const flagged = DEMO_PATIENTS.map((p) => ({ p, r: riskAssessment(p.id) })).filter(
    (x) => !x.r.silent && x.r.alert,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Doctor Portal"
        title="Risk Watcher"
        action={
          <span className="text-xs text-ink-secondary">
            {flagged.length} of {DEMO_PATIENTS.length} patients flagged
          </span>
        }
      />

      <p className="text-sm text-ink-secondary">
        The watcher runs silently in the background and never surfaces
        anything unless a real threshold is crossed: weight loss ≥5% in 6
        months (≥10% = severe), albumin &lt;3.5 g/dL, or appetite documented
        as poor. No noise otherwise.
      </p>

      {flagged.length === 0 ? (
        <Card>
          <p className="text-sm text-ink-secondary">
            No thresholds crossed. Nothing to show — by design.
          </p>
        </Card>
      ) : (
        flagged.map(({ p, r }) => (
          <Card key={p.id} className="border-status-review/40">
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <Link href={`/doctors/me/patients/${p.id}`}>
                    <span className="font-medium text-ink-primary hover:text-brand-teal">
                      {p.name} ({p.id})
                    </span>
                  </Link>
                  <StatusBadge
                    status={r.alert!.level === "high" ? "urgent" : "review"}
                    label={r.alert!.level === "high" ? "High" : "Watch"}
                    dot
                  />
                </div>
                <ul className="list-disc list-inside text-sm text-ink-primary mt-2 space-y-1">
                  {r.alert!.reasons.map((reason, i) => (
                    <li key={i}>{reason}</li>
                  ))}
                </ul>
              </div>
              <p className="text-xs text-ink-secondary max-w-xs">{r.alert!.suggestion}</p>
            </div>
          </Card>
        ))
      )}

      <Card>
        <p className="text-xs text-ink-secondary">
          {DEMO_PATIENTS.filter((p) => {
            const r = riskAssessment(p.id);
            return r.silent || !r.alert;
          })
            .map((p) => `${p.name} — no threshold crossed`)
            .join(" · ") || "None"}
        </p>
      </Card>
    </div>
  );
}
