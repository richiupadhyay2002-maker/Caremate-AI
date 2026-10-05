"use client";

import { useState } from "react";
import { useApp } from "@/lib/auth-context";
import { getDocuments, getPatient } from "@/lib/demo-data";
import { explainReport, ReportExplanation } from "@/lib/ai-engine";
import { PageHeader, Card, StatusBadge } from "@/components/ui";

/**
 * Report Explainer — plain-language translation of pathology/radiology/lab
 * reports, including what the report explicitly does NOT say.
 */
export default function ReportsPage() {
  const { patientId } = useApp();
  const patient = getPatient(patientId);
  const docs = getDocuments(patientId);
  const [selected, setSelected] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<ReportExplanation | null>(null);

  const handleExplain = (docId: string) => {
    setSelected(docId);
    setExplanation(explainReport(docId));
  };

  if (!patient) return <p className="text-ink-secondary">No patient data found.</p>;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Patient Portal" title="Report Explainer" />

      <p className="text-sm text-ink-secondary">
        Plain-language translations of your reports — including what each
        report explicitly does <em>not</em> say. A plain-language rewording can
        lose nuance; always confirm with the doctor who ordered the test.
      </p>

      <Card className="p-0">
        <div className="divide-y divide-clinical-border">
          {docs.map((d) => (
            <button
              key={d.id}
              type="button"
              onClick={() => handleExplain(d.id)}
              className={`w-full text-left px-4 py-3 flex items-center justify-between gap-4 cursor-pointer hover:bg-clinical-border/10 ${selected === d.id ? "bg-clinical-border/10" : ""
                }`}
            >
              <div>
                <p className="text-sm font-medium text-ink-primary">{d.title}</p>
                <p className="text-xs text-ink-secondary mt-0.5">
                  {d.date} · {d.type} · {d.source}
                </p>
              </div>
              <span className="text-xs text-brand-teal font-medium whitespace-nowrap">
                Explain →
              </span>
            </button>
          ))}
        </div>
      </Card>

      {explanation && (
        <>
          <Card>
            <div className="flex items-start justify-between flex-wrap gap-2 mb-3">
              <div>
                <h2 className="text-lg font-heading text-ink-primary">
                  {explanation.document_title}
                </h2>
                <p className="text-xs text-ink-secondary">{explanation.date}</p>
              </div>
              <StatusBadge status="review" label="Needs clinician review" dot />
            </div>

            <h3 className="text-sm font-semibold text-ink-secondary uppercase tracking-wider mb-1">
              In plain language
            </h3>
            <p className="text-sm text-ink-primary leading-relaxed">
              {explanation.plain_summary}
            </p>
          </Card>

          {explanation.term_explanations.length > 0 && (
            <Card>
              <h3 className="text-base font-heading text-ink-primary mb-3">
                Medical terms, translated
              </h3>
              <ul className="space-y-3">
                {explanation.term_explanations.map((t, i) => (
                  <li key={i} className="border-l-2 border-brand-teal pl-3">
                    <p className="text-sm font-medium text-ink-primary">{t.term}</p>
                    <p className="text-sm text-ink-secondary">{t.meaning}</p>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <Card>
            <h3 className="text-base font-heading text-ink-primary mb-3">
              What this report explicitly does not say
            </h3>
            <ul className="list-disc list-inside space-y-1.5 text-sm text-ink-primary">
              {explanation.explicitly_not_said.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </Card>

          <Card>
            <h3 className="text-base font-heading text-ink-primary mb-3">Sources</h3>
            <ul className="space-y-2">
              {explanation.citations.map((c, i) => (
                <li key={i} className="text-sm">
                  <p className="text-xs text-ink-secondary">
                    ↳ <span className="font-medium text-ink-primary">{c.document_title}</span>
                    {` — ${c.section}`}
                  </p>
                  <p className="text-xs text-ink-secondary italic mt-0.5">
                    &ldquo;{c.snippet}&rdquo;
                  </p>
                </li>
              ))}
            </ul>
            <p className="text-xs text-ink-secondary mt-3">{explanation.safety_note}</p>
          </Card>
        </>
      )}
    </div>
  );
}
