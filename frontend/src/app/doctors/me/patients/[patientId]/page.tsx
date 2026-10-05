"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getPatient, getDocuments } from "@/lib/demo-data";
import { patientBrief, riskAssessment, findTermExplanations } from "@/lib/ai-engine";
import { PageHeader, Card, StatusBadge } from "@/components/ui";

type ReviewStatus = "draft" | "approved" | "edited" | "rejected";

interface AuditEvent {
  time: string;
  action: string;
}

const AUDIT_KEY = "caremate_brief_audit_";

/**
 * Patient Brief — AI-drafted summary (overview, recent labs, nutrition
 * status, missing information). Always labeled DRAFT, never auto-applied.
 * Includes Approve / Edit / Reject controls with a visible audit trail
 * and an evidence & source panel.
 */
export default function PatientBriefPage() {
  const params = useParams<{ patientId: string }>();
  const patientId = params.patientId;
  const patient = getPatient(patientId);
  const brief = patientBrief(patientId);
  const risk = riskAssessment(patientId);

  const [reviewStatus, setReviewStatus] = useState<ReviewStatus>("draft");
  const [editedText, setEditedText] = useState<string | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(AUDIT_KEY + patientId);
      if (raw) setAudit(JSON.parse(raw));
    } catch {
      /* ignore */
    }
  }, [patientId]);

  const logEvent = (action: string) => {
    const event: AuditEvent = {
      time: new Date().toLocaleString(),
      action,
    };
    const next = [event, ...audit];
    setAudit(next);
    localStorage.setItem(AUDIT_KEY + patientId, JSON.stringify(next));
  };

  if (!patient || !brief) {
    return <p className="text-ink-secondary">Patient not found in demo data.</p>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Doctor Portal"
        title={patient.name}
        action={
          <span className="flex gap-3 text-sm">
            <Link
              href={`/doctors/me/patients/${patientId}/profile`}
              className="text-brand-teal font-medium"
            >
              Health profile →
            </Link>
            <Link
              href={`/doctors/me/patients/${patientId}/timeline`}
              className="text-sm text-brand-teal font-medium"
            >
              Medical timeline →
            </Link>
          </span>
        }
      />

      <p className="text-sm text-ink-secondary">
        <span className="font-mono">{patient.id}</span> · {patient.age}y{" "}
        {patient.sex} · {patient.diagnosis}
      </p>

      {/* Background risk watcher — silent unless thresholds crossed */}
      {!risk.silent && risk.alert && (
        <Card className="border-status-review/40">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <StatusBadge
                status={risk.alert.level === "high" ? "urgent" : "review"}
                label="Nutrition risk (background watcher)"
                dot
              />
              <ul className="list-disc list-inside text-sm text-ink-primary mt-2 space-y-1">
                {risk.alert.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
            <p className="text-xs text-ink-secondary max-w-xs">{risk.alert.suggestion}</p>
          </div>
        </Card>
      )}

      {/* AI DRAFT brief */}
      <Card className="border-status-review/40">
        <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
          <StatusBadge status="pending" label="AI DRAFT — not applied to the record" dot />
          <span className="text-xs text-ink-secondary">
            {reviewStatus === "draft"
              ? "Review required before any use"
              : `Status: ${reviewStatus}`}
          </span>
        </div>

        {reviewStatus !== "edited" ? (
          <>
            <h2 className="text-base font-heading text-ink-primary mb-1">Overview</h2>
            <p className="text-sm text-ink-primary leading-relaxed">{brief.overview}</p>

            <h3 className="text-sm font-semibold text-ink-secondary uppercase tracking-wider mt-4 mb-1">
              Recent labs
            </h3>
            <ul className="text-sm text-ink-primary space-y-1">
              {brief.recent_labs.length > 0 ? (
                brief.recent_labs.map((l, i) => <li key={i}>{l}</li>)
              ) : (
                <li className="text-ink-secondary">None in the demo record.</li>
              )}
            </ul>

            <h3 className="text-sm font-semibold text-ink-secondary uppercase tracking-wider mt-4 mb-1">
              Nutrition status
            </h3>
            <p className="text-sm text-ink-primary">{brief.nutrition_status}</p>

            <h3 className="text-sm font-semibold text-ink-secondary uppercase tracking-wider mt-4 mb-1">
              Missing information
            </h3>
            <ul className="list-disc list-inside text-sm text-ink-secondary space-y-1">
              {brief.missing_information.map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>

            {(() => {
              const plainTerms = findTermExplanations(
                brief.overview + " " + brief.nutrition_status + " " + brief.recent_labs.join(" ")
              );
              if (plainTerms.length === 0) return null;
              return (
                <div className="mt-4 pt-3 border-t border-clinical-border">
                  <h3 className="text-sm font-semibold text-ink-secondary uppercase tracking-wider mb-2">
                    In plain language (for the patient)
                  </h3>
                  <ul className="space-y-2">
                    {plainTerms.map((t, i) => (
                      <li key={i} className="text-sm border-l-2 border-clinical-border pl-3">
                        <span className="font-medium text-ink-primary">{t.term}.</span>{" "}
                        <span className="text-xs font-semibold text-ink-secondary uppercase tracking-wider mr-1">
                          Explain:
                        </span>
                        <span className="text-ink-secondary">{t.meaning}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="text-xs text-ink-secondary mt-2">
                    Shareable wording to explain this brief to the patient in layman terms.
                  </p>
                </div>
              );
            })()}
          </>
        ) : (
          <div>
            <h3 className="text-sm font-semibold text-ink-secondary uppercase tracking-wider mb-1">
              Doctor-edited brief
            </h3>
            <textarea
              value={editedText ?? ""}
              onChange={(e) => setEditedText(e.target.value)}
              className="w-full px-3 py-2 border border-clinical-border rounded-[10px] bg-clinical-surface text-sm text-ink-primary outline-none min-h-[180px] font-body"
            />
            <div className="flex gap-2 mt-2">
              <button
                type="button"
                onClick={() => {
                  setReviewStatus("approved");
                  logEvent("Saved doctor-edited brief and approved");
                  setReviewStatus("draft");
                  setEditedText(null);
                }}
                className="text-xs px-3 py-1.5 rounded-[8px] bg-brand-teal text-white cursor-pointer"
              >
                Save edit
              </button>
              <button
                type="button"
                onClick={() => {
                  setReviewStatus("draft");
                  setEditedText(null);
                }}
                className="text-xs px-3 py-1.5 rounded-[8px] border border-clinical-border text-ink-secondary cursor-pointer"
              >
                Discard edit
              </button>
            </div>
          </div>
        )}

        {/* Review controls */}
        <div className="flex flex-wrap gap-2 mt-5 pt-4 border-t border-clinical-border">
          <button
            type="button"
            data-testid="approve-brief"
            onClick={() => {
              setReviewStatus("approved");
              logEvent("Brief approved by Dr. K. Sharma (demo)");
            }}
            disabled={reviewStatus === "edited"}
            className="text-xs px-3 py-1.5 rounded-[8px] bg-status-safe-bg text-status-safe font-medium cursor-pointer disabled:opacity-50"
          >
            Approve
          </button>
          <button
            type="button"
            data-testid="edit-brief"
            onClick={() => {
              setEditedText(brief.overview + "\n\n" + brief.nutrition_status);
              setReviewStatus("edited");
            }}
            className="text-xs px-3 py-1.5 rounded-[8px] bg-status-review-bg text-status-review font-medium cursor-pointer"
          >
            Edit
          </button>
          <button
            type="button"
            data-testid="reject-brief"
            onClick={() => {
              setReviewStatus("rejected");
              logEvent("Brief rejected by Dr. K. Sharma (demo)");
            }}
            disabled={reviewStatus === "edited"}
            className="text-xs px-3 py-1.5 rounded-[8px] bg-status-urgent-bg text-status-urgent font-medium cursor-pointer disabled:opacity-50"
          >
            Reject
          </button>
        </div>
      </Card>

      {/* Evidence & Source panel */}
      <Card>
        <h2 className="text-base font-heading text-ink-primary mb-3">
          Evidence &amp; sources
        </h2>
        <p className="text-xs text-ink-secondary mb-3">
          Every AI claim above traces to a specific document section.
        </p>
        <ul className="space-y-3">
          {brief.citations.map((c, i) => (
            <li key={i} className="text-sm border-l-2 border-brand-teal pl-3">
              <p className="text-xs text-ink-secondary">
                <span className="font-medium text-ink-primary">{c.document_title}</span>
                {` — ${c.section}`}
              </p>
              <p className="text-xs text-ink-secondary italic mt-0.5">
                &ldquo;{c.snippet}&rdquo;
              </p>
            </li>
          ))}
        </ul>
      </Card>

      {/* Audit trail */}
      <Card>
        <h2 className="text-base font-heading text-ink-primary mb-3">
          Review audit trail
        </h2>
        {audit.length === 0 ? (
          <p className="text-sm text-ink-secondary">No review actions recorded yet.</p>
        ) : (
          <ul className="divide-y divide-clinical-border">
            {audit.map((a, i) => (
              <li key={i} className="py-2 text-sm text-ink-primary flex justify-between gap-4">
                <span>{a.action}</span>
                <span className="text-xs text-ink-secondary whitespace-nowrap">{a.time}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* Documents in record */}
      <Card>
        <h2 className="text-base font-heading text-ink-primary mb-3">
          Documents in record ({getDocuments(patientId).length})
        </h2>
        <ul className="divide-y divide-clinical-border">
          {getDocuments(patientId).map((d) => (
            <li key={d.id} className="py-2 text-sm">
              <p className="text-ink-primary">{d.title}</p>
              <p className="text-xs text-ink-secondary">
                {d.date} · {d.type} · {d.source}
              </p>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
