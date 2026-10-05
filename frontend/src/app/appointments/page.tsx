"use client";

import { useApp } from "@/lib/auth-context";
import { getPatient } from "@/lib/demo-data";
import { appointmentPrep } from "@/lib/ai-engine";
import { PageHeader, Card, StatusBadge } from "@/components/ui";

/**
 * Appointment Preparation — AI-suggested questions to bring to the next
 * oncologist visit, based on documented history. Always framed as
 * "questions to ask", never as advice.
 */
export default function AppointmentsPage() {
  const { patientId } = useApp();
  const patient = getPatient(patientId);
  const prep = appointmentPrep(patientId);

  if (!patient) return <p className="text-ink-secondary">No patient data found.</p>;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Patient Portal" title="Appointment Prep" />

      {prep.appointment ? (
        <Card>
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <h2 className="text-lg font-heading text-ink-primary">
                {prep.appointment.title}
              </h2>
              <p className="text-sm text-ink-secondary mt-0.5">
                {new Date(prep.appointment.date).toLocaleDateString("en-US", {
                  weekday: "long",
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}{" "}
                · {prep.appointment.clinician} · {prep.appointment.location}
              </p>
            </div>
            <StatusBadge status="review" label="Suggested — not advice" />
          </div>
          {prep.appointment.notes && (
            <p className="text-sm text-ink-secondary mt-3 border-l-2 border-clinical-border pl-3">
              {prep.appointment.notes}
            </p>
          )}
        </Card>
      ) : (
        <Card>
          <p className="text-sm text-ink-secondary">No upcoming appointment in the demo record.</p>
        </Card>
      )}

      <Card>
        <h2 className="text-lg font-heading text-ink-primary mb-1">
          Questions suggested from your documented history
        </h2>
        <p className="text-sm text-ink-secondary mb-4">
          Drafted from your records. Choose the ones that matter to you — your
          care team can only answer what you ask about.
        </p>
        <ul className="space-y-3">
          {prep.suggested_questions.map((q, i) => (
            <li
              key={i}
              className="border-l-2 border-brand-teal pl-3 text-sm text-ink-primary"
            >
              {q}
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <h2 className="text-base font-heading text-ink-primary mb-2">Bring with you</h2>
        <ul className="list-disc list-inside space-y-1 text-sm text-ink-primary">
          {prep.bring_with_you.map((b, i) => (
            <li key={i}>{b}</li>
          ))}
        </ul>
      </Card>

      {prep.citations.length > 0 && (
        <Card>
          <h2 className="text-base font-heading text-ink-primary mb-2">
            Where these suggestions came from
          </h2>
          <ul className="space-y-2">
            {prep.citations.map((c, i) => (
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
        </Card>
      )}
    </div>
  );
}
