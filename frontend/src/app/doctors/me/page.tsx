"use client";

import Link from "next/link";
import {
  DEMO_PATIENTS,
  weightLossPercent,
  getLabs,
  getDocuments,
} from "@/lib/demo-data";
import { riskAssessment } from "@/lib/ai-engine";
import { PageHeader, Card, StatusBadge } from "@/components/ui";

/**
 * Patient List — all demo patients at a glance, each with a
 * background-computed nutrition/risk flag (weight-loss %, albumin,
 * documented appetite). Silent by design: a flag row shows "Stable"
 * when no threshold is crossed.
 */
export default function DoctorDashboardPage() {
  const patients = DEMO_PATIENTS;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Doctor Portal"
        title="Patient List"
        action={
          <span className="text-xs text-ink-secondary">
            {patients.length} patient{patients.length !== 1 ? "s" : ""} · demo data
          </span>
        }
      />

      <Card className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left py-3 px-4 font-medium text-ink-secondary">Patient</th>
                <th className="text-left py-3 px-4 font-medium text-ink-secondary">Diagnosis</th>
                <th className="text-left py-3 px-4 font-medium text-ink-secondary">Nutrition / risk flag</th>
                <th className="text-right py-3 px-4 font-medium text-ink-secondary">Documents</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((patient) => {
                const risk = riskAssessment(patient.id);
                const wl = weightLossPercent(patient.id);
                const labs = getLabs(patient.id);
                const latest = labs[labs.length - 1];

                return (
                  <tr key={patient.id} className="border-t border-clinical-border">
                    <td className="py-3 px-4">
                      <Link href={`/doctors/me/patients/${patient.id}/profile`}>
                        <span className="font-medium text-ink-primary hover:text-brand-teal cursor-pointer">
                          {patient.name}
                        </span>
                      </Link>
                      <p className="text-xs text-ink-secondary mt-0.5">
                        {patient.age}y · {patient.sex} · <span className="font-mono">{patient.id}</span>
                      </p>
                    </td>
                    <td className="py-3 px-4 align-top">
                      <p className="text-ink-secondary">{patient.diagnosis}</p>
                      <p className="text-xs text-ink-secondary mt-0.5">
                        {wl !== null ? `Weight ${wl > 0 ? "−" : "+"}${Math.abs(wl)}%` : "No weight trend"}
                        {latest ? ` · Albumin ${latest.albumin_g_dl} g/dL` : ""}
                      </p>
                    </td>
                    <td className="py-3 px-4">
                      {risk.silent || !risk.alert ? (
                        <StatusBadge status="safe" label="No flag — stable" />
                      ) : (
                        <StatusBadge
                          status={risk.alert.level === "high" ? "urgent" : "review"}
                          label={
                            risk.alert.level === "high"
                              ? "High — dietitian suggested"
                              : "Watch — thresholds near"
                          }
                          dot
                        />
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span className="text-xs text-ink-secondary">
                        {getDocuments(patient.id).length}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <p className="text-xs text-ink-secondary">
        Risk flags are computed in the background from real thresholds
        (weight loss ≥5%/6 mo or ≥10%, albumin &lt;3.5 g/dL, documented poor
        appetite). No flag is shown unless a threshold is crossed. All data is
        synthetic demo data.
      </p>
    </div>
  );
}
