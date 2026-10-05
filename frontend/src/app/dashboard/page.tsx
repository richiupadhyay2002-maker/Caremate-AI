"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "@/lib/auth-context";
import {
  getPatient,
  getDocuments,
  getLabs,
  getAppointment,
  getWeights,
  weightLossPercent,
} from "@/lib/demo-data";
import { riskAssessment } from "@/lib/ai-engine";
import { loadJournal, JournalEntry } from "../journal-storage";
import { PageHeader, Card, Timeline, StatusBadge } from "@/components/ui";

export default function DashboardPage() {
  const { patientId } = useApp();
  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setJournal(loadJournal(patientId));
    setReady(true);
  }, [patientId]);

  const patient = getPatient(patientId);
  const docs = getDocuments(patientId);
  const labs = getLabs(patientId);
  const appt = getAppointment(patientId);
  const weights = getWeights(patientId);
  const wl = weightLossPercent(patientId);
  const risk = riskAssessment(patientId);

  if (!patient) {
    return <p className="text-ink-secondary">No patient data found.</p>;
  }

  const feed = [
    ...docs.map((d) => ({
      id: d.id,
      date: d.date,
      title: d.title,
      subtitle: `${d.type} · ${d.source}`,
    })),
    ...labs.map((l) => ({
      id: `lab-${l.date}`,
      date: l.date,
      title: "Lab results",
      subtitle: `Albumin ${l.albumin_g_dl} g/dL · Hb ${l.hemoglobin_g_dl} g/dL · Creatinine ${l.creatinine_mg_dl} mg/dL`,
    })),
    ...(appt
      ? [
          {
            id: appt.id,
            date: appt.date,
            title: appt.title,
            subtitle: `${appt.clinician} · ${appt.location}`,
          },
        ]
      : []),
    ...journal.map((j) => ({
      id: `journal-${j.id}`,
      date: j.date,
      title: `Symptom logged: ${j.symptom}`,
      subtitle: `Severity ${j.severity}/10 · ${j.duration}`,
    })),
  ].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );

  const latestWeight = weights[weights.length - 1];

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Patient Portal" title="My Care Timeline" />

      {/* Patient summary */}
      <Card>
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-xl font-heading text-ink-primary">{patient.name}</h2>
            <p className="text-sm text-ink-secondary mt-0.5">
              Age: {patient.age} · {patient.sex} · ID:{" "}
              <span className="font-mono">{patient.id}</span>
            </p>
            <p className="text-sm text-ink-secondary mt-1">{patient.diagnosis}</p>
          </div>
          <span className="text-[10px] px-2 py-1 bg-status-urgent-bg text-status-urgent rounded uppercase font-medium">
            Demo data — not real medical records
          </span>
        </div>

        <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">
              Latest weight
            </p>
            <p className="text-ink-primary mt-1">
              {latestWeight ? `${latestWeight.weight_kg} kg` : "—"}
              {wl !== null && <span className="text-ink-secondary"> · {wl}% change</span>}
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">
              Appetite (documented)
            </p>
            <p className="text-ink-primary mt-1 capitalize">{patient.appetite}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">
              Allergies
            </p>
            <p className="text-ink-primary mt-1">
              {patient.allergies.map((a) => a.substance).join(", ") || "None recorded"}
            </p>
          </div>
        </div>

        <div className="mt-4">
          <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">
            Current medications
          </p>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {patient.medications.map((m, i) => (
              <span
                key={i}
                className="text-xs px-2 py-1 bg-clinical-border/20 text-ink-primary rounded"
              >
                {m.name} {m.dosage}
              </span>
            ))}
          </div>
        </div>
      </Card>

      {/* Silent risk watcher — surfaces only when thresholds are crossed */}
      {!risk.silent && risk.alert && (
        <Card className="border-status-review/40">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <StatusBadge
                status={risk.alert.level === "high" ? "urgent" : "review"}
                label="Nutrition risk flag"
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

      {/* The merged feed */}
      <Card>
        <h2 className="text-lg font-heading text-ink-primary mb-1">
          Everything in one feed
        </h2>
        <p className="text-sm text-ink-secondary mb-4">
          Documents, lab results, appointments and symptom-journal entries,
          newest first.
        </p>
        <Timeline items={feed} />
      </Card>

      {/* Quick links */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <h3 className="text-base font-heading text-ink-primary">Ask My Record</h3>
          <p className="text-sm text-ink-secondary mt-1">
            Grounded answers from your own records only.
          </p>
          <Link href="/ask" className="text-sm text-brand-teal font-medium mt-2 inline-block">
            Open →
          </Link>
        </Card>
        <Card>
          <h3 className="text-base font-heading text-ink-primary">Symptom Journal</h3>
          <p className="text-sm text-ink-secondary mt-1">
            Log symptoms with severity over time.
          </p>
          <Link href="/journal" className="text-sm text-brand-teal font-medium mt-2 inline-block">
            Open →
          </Link>
        </Card>
        <Card>
          <h3 className="text-base font-heading text-ink-primary">Appointment Prep</h3>
          <p className="text-sm text-ink-secondary mt-1">
            Suggested questions for your next visit.
          </p>
          <Link href="/appointments" className="text-sm text-brand-teal font-medium mt-2 inline-block">
            Open →
          </Link>
        </Card>
      </div>
      {ready && null}
    </div>
  );
}
