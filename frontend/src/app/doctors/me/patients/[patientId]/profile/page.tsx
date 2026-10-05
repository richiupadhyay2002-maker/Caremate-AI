"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  getPatient,
  getDocuments,
  getLabs,
  getAppointment,
  getWeights,
  weightLossPercent,
} from "@/lib/demo-data";
import { listDocuments, DocumentRef } from "@/lib/api";
import { loadJournal, JournalEntry } from "@/app/journal-storage";
import { PageHeader, Card, StatusBadge, Timeline } from "@/components/ui";

/**
 * Patient Health Profile — everything the doctor needs in one view:
 * health information, medical history, current health details, symptoms
 * reported by the patient (live), patient-entered notes, and all medical
 * reports / documents / uploaded files.
 *
 * Patient-entered symptoms are re-read every few seconds from the same
 * store the patient journal writes to, so new entries appear here
 * automatically without a page refresh.
 */
export default function PatientProfilePage() {
  const params = useParams<{ patientId: string }>();
  const patientId = params.patientId;
  const patient = getPatient(patientId);

  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [uploads, setUploads] = useState<DocumentRef[]>([]);
  const [uploadsError, setUploadsError] = useState("");

  // Live symptom feed: re-read the patient's journal periodically.
  const refreshJournal = useCallback(() => {
    setJournal(loadJournal(patientId));
  }, [patientId]);

  useEffect(() => {
    refreshJournal();
    const t = setInterval(refreshJournal, 4000);
    const onFocus = () => refreshJournal();
    window.addEventListener("focus", onFocus);
    return () => {
      clearInterval(t);
      window.removeEventListener("focus", onFocus);
    };
  }, [refreshJournal]);

  // Uploaded files (backend API — doctor token may list any patient's docs)
  useEffect(() => {
    let cancelled = false;
    listDocuments(patientId)
      .then((docs) => {
        if (cancelled) return;
        setUploads(docs.filter((d) => d.source.startsWith("upload:")));
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setUploadsError(
          e instanceof Error ? "Could not load uploaded files (API offline)." : "Could not load uploaded files."
        );
      });
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  if (!patient) {
    return <p className="text-ink-secondary">Patient not found in demo data.</p>;
  }

  const recordDocs = getDocuments(patientId);
  const labs = getLabs(patientId);
  const latestLab = labs[labs.length - 1];
  const weights = getWeights(patientId);
  const latestWeight = weights[weights.length - 1];
  const wl = weightLossPercent(patientId);
  const appt = getAppointment(patientId);
  const heightM = patient.height_cm / 100;
  const bmi = latestWeight ? (latestWeight.weight_kg / (heightM * heightM)).toFixed(1) : null;

  const sortedJournal = [...journal].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Doctor Portal — Health Profile"
        title={patient.name}
        action={
          <span className="flex gap-3 text-sm">
            <Link href={`/doctors/me/patients/${patientId}`} className="text-brand-teal font-medium">
              AI Patient Brief →
            </Link>
            <Link href={`/doctors/me/patients/${patientId}/timeline`} className="text-brand-teal font-medium">
              Editable Timeline →
            </Link>
          </span>
        }
      />

      {/* ── Health information ── */}
      <Card>
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <p className="text-sm text-ink-secondary">
              <span className="font-mono">{patient.id}</span> · {patient.age}y · {patient.sex} ·{" "}
              {patient.height_cm} cm
              {bmi ? ` · BMI ${bmi}` : ""}
            </p>
            <p className="text-sm font-medium text-ink-primary mt-1">{patient.diagnosis}</p>
            <p className="text-xs text-ink-secondary mt-1">{patient.stage_note}</p>
          </div>
          <div className="flex flex-col items-end gap-1">
            {patient.allergies.map((a, i) => (
              <StatusBadge key={i} status="urgent" label={`${a.substance} (${a.severity})`} dot />
            ))}
          </div>
        </div>

        <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider mt-4 mb-1">
          Clinical summary
        </p>
        <p className="text-sm text-ink-primary leading-relaxed">{patient.diagnosis_details}</p>

        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">Weight</p>
            <p className="text-ink-primary mt-1">
              {latestWeight ? `${latestWeight.weight_kg} kg` : "—"}
              {wl !== null && (
                <span className={wl >= 5 ? "text-status-urgent" : "text-ink-secondary"}>
                  {" "}({wl > 0 ? "−" : "+"}{Math.abs(wl)}%)
                </span>
              )}
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">Appetite</p>
            <p className="text-ink-primary mt-1 capitalize">{patient.appetite}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">Diet notes</p>
            <p className="text-ink-primary mt-1">
              {patient.dietary_restrictions.join(", ") || "None recorded"}
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">Next visit</p>
            <p className="text-ink-primary mt-1">
              {appt ? new Date(appt.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "—"}
            </p>
          </div>
        </div>

        <div className="mt-4">
          <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-2">
            Current medications
          </p>
          <div className="flex flex-wrap gap-1.5">
            {patient.medications.map((m, i) => (
              <span key={i} className="text-xs px-2 py-1 bg-clinical-border/20 text-ink-primary rounded">
                {m.name} {m.dosage} · {m.frequency}
              </span>
            ))}
          </div>
        </div>
      </Card>

      {/* ── Symptoms reported by the patient (live) ── */}
      <Card>
        <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
          <div>
            <h2 className="text-lg font-heading text-ink-primary">
              Symptoms reported by the patient
            </h2>
            <p className="text-xs text-ink-secondary mt-0.5">
              Patient-entered entries — updates appear here automatically
              {journal.length > 0 ? ` · ${journal.length} ent${journal.length === 1 ? "y" : "ries"}` : ""}
            </p>
          </div>
          <span className="w-2 h-2 rounded-full bg-status-safe animate-pulse" title="Live" />
        </div>

        {sortedJournal.length === 0 ? (
          <p className="text-sm text-ink-secondary">
            No symptoms reported yet. Entries the patient logs in their journal
            will appear here automatically.
          </p>
        ) : (
          <ul className="divide-y divide-clinical-border">
            {sortedJournal.map((e) => (
              <li key={e.id} className="py-3">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-medium text-ink-primary">{e.symptom}</p>
                      <StatusBadge
                        status={e.red_flag ? "urgent" : e.severity >= 7 ? "review" : "safe"}
                        label={e.red_flag ? "Red flag" : `Severity ${e.severity}/10`}
                        dot={!!e.red_flag}
                      />
                    </div>
                    <p className="text-xs text-ink-secondary mt-1">
                      {e.date} · duration: {e.duration}
                      {e.notes ? ` · ${e.notes}` : ""}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* ── Medical history ── */}
      <Card>
        <h2 className="text-lg font-heading text-ink-primary mb-4">Medical history</h2>
        <Timeline
          items={patient.history_events.map((e, i) => ({
            id: `h-${i}`,
            date: e.date,
            title: e.event,
            subtitle: e.detail,
          }))}
        />
      </Card>

      {/* ── Test results ── */}
      <Card>
        <h2 className="text-lg font-heading text-ink-primary mb-3">Test results (labs)</h2>
        {labs.length === 0 ? (
          <p className="text-sm text-ink-secondary">No lab results in the record.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="text-left py-2 font-medium text-ink-secondary">Date</th>
                  <th className="text-left py-2 font-medium text-ink-secondary">Albumin</th>
                  <th className="text-left py-2 font-medium text-ink-secondary">Haemoglobin</th>
                  <th className="text-left py-2 font-medium text-ink-secondary">Creatinine</th>
                  <th className="text-left py-2 font-medium text-ink-secondary">CRP</th>
                </tr>
              </thead>
              <tbody>
                {labs.map((l) => (
                  <tr key={l.date} className="border-t border-clinical-border">
                    <td className="py-2 text-ink-primary">{l.date}</td>
                    <td className="py-2 text-ink-primary">
                      {l.albumin_g_dl} g/dL
                      {l.albumin_g_dl < 3.5 && <StatusBadge status="urgent" label="low" />}
                    </td>
                    <td className="py-2 text-ink-primary">{l.hemoglobin_g_dl} g/dL</td>
                    <td className="py-2 text-ink-primary">{l.creatinine_mg_dl} mg/dL</td>
                    <td className="py-2 text-ink-primary">{l.crp_mg_l} mg/L</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* ── Reports, documents & uploaded files ── */}
      <Card>
        <h2 className="text-lg font-heading text-ink-primary mb-1">
          Medical reports, documents &amp; files
        </h2>
        <p className="text-sm text-ink-secondary mb-3">
          Records in the chart plus files uploaded by the patient.
        </p>

        <ul className="divide-y divide-clinical-border">
          {uploads.map((d) => (
            <li key={d.document_id} className="py-3 flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-sm font-medium text-ink-primary">{d.title}</p>
                  <StatusBadge status="review" label="Uploaded by patient" />
                </div>
                <p className="text-xs text-ink-secondary mt-0.5">
                  {d.document_type}
                  {d.created_at ? ` · ${new Date(d.created_at).toLocaleString()}` : ""} · {d.source}
                </p>
              </div>
            </li>
          ))}
          {recordDocs.map((d) => (
            <li key={d.id} className="py-3">
              <p className="text-sm font-medium text-ink-primary">{d.title}</p>
              <p className="text-xs text-ink-secondary mt-0.5">
                {d.date} · {d.type} · {d.source} (chart record)
              </p>
            </li>
          ))}
        </ul>
        {uploads.length === 0 && !uploadsError && (
          <p className="text-xs text-ink-secondary mt-2">
            No files uploaded by the patient yet. Files the patient uploads from
            their dashboard appear here automatically.
          </p>
        )}
        {uploadsError && <p className="text-xs text-status-urgent mt-2">{uploadsError}</p>}
      </Card>
    </div>
  );
}
