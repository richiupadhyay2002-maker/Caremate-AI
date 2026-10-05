"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { getPatientContext, PatientContext } from "@/lib/api";
import { PageHeader, Card, StatusBadge } from "@/components/ui";
import Link from "next/link";

export default function PatientContextPage() {
  const params = useParams() as { patientId: string };
  const { token } = useAuth();
  const [context, setContext] = useState<PatientContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    const fetchContext = async () => {
      try {
        setLoading(true);
        const ctx = await getPatientContext(params.patientId);
        setContext(ctx);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    };
    fetchContext();
  }, [params.patientId, token]);

  if (!token) {
    return (
      <div className="text-center py-12">
        <p className="text-ink-secondary">
          Please <Link href="/login" className="text-brand-teal font-medium">log in</Link>.
        </p>
      </div>
    );
  }

  if (loading)
    return <div className="text-center py-12 text-ink-secondary">Loading…</div>;

  if (error)
    return (
      <Card className="border-status-urgent/30">
        <p className="text-sm text-status-urgent">{error}</p>
      </Card>
    );

  if (!context)
    return <div className="text-center py-12 text-ink-secondary">No data found.</div>;

  const safetyStatus =
    context.allergies?.some((a) =>
      a.severity.toLowerCase().includes("severe"),
    )
      ? "urgent"
      : "safe";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Patient Portal"
        title="Patient Context"
        action={
          <Link href="/dashboard">
            <span className="text-xs text-ink-secondary hover:text-brand-teal cursor-pointer">
              ← Back to dashboard
            </span>
          </Link>
        }
      />

      <Card>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-heading text-ink-primary">
              {context.name || context.patient_id}
            </h1>
            <p className="text-sm text-ink-secondary mt-0.5">
              ID: <span className="font-mono">{context.patient_id}</span>
            </p>
          </div>
          <StatusBadge status={safetyStatus} dot />
        </div>
      </Card>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <h2 className="text-lg font-heading text-ink-primary mb-3">Demographics</h2>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-ink-secondary">Patient ID</dt>
              <dd className="font-mono text-ink-primary">{context.patient_id}</dd>
            </div>
            <div>
              <dt className="text-ink-secondary">Age</dt>
              <dd className="text-ink-primary">{context.age}</dd>
            </div>
            <div>
              <dt className="text-ink-secondary">Sex</dt>
              <dd className="text-ink-primary">{context.sex}</dd>
            </div>
            <div>
              <dt className="text-ink-secondary">Name</dt>
              <dd className="text-ink-primary">{context.name}</dd>
            </div>
          </dl>
        </Card>

        {context.current_medications && context.current_medications.length > 0 && (
          <Card>
            <h2 className="text-lg font-heading text-ink-primary mb-3">Medications</h2>
            <ul className="space-y-2 text-sm">
              {context.current_medications.map((med, i) => (
                <li key={i} className="p-2 bg-clinical-border/20 rounded">
                  <strong className="text-ink-primary">{med.name}</strong>{" "}
                  {med.dosage} ({med.frequency})
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>

      {context.allergies && context.allergies.length > 0 && (
        <Card>
          <h2 className="text-lg font-heading text-ink-primary mb-3">Allergies</h2>
          <div className="flex flex-wrap gap-2">
            {context.allergies.map((a, i) => (
              <StatusBadge key={i} status="urgent" label={`${a.substance} (${a.severity})`} dot />
            ))}
          </div>
        </Card>
      )}

      {context.medical_history && context.medical_history.length > 0 && (
        <Card>
          <h2 className="text-lg font-heading text-ink-primary mb-3">Medical History</h2>
          <ul className="list-disc list-inside space-y-1 text-sm text-ink-secondary">
            {context.medical_history.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        </Card>
      )}

      {context.lab_results && Object.keys(context.lab_results).length > 0 && (
        <Card>
          <h2 className="text-lg font-heading text-ink-primary mb-3">Lab Results</h2>
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left text-ink-secondary">Test</th>
                <th className="text-left text-ink-secondary">Value</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(context.lab_results).map(([k, v]) => (
                <tr key={k}>
                  <td className="py-1 text-ink-primary">{k}</td>
                  <td className="py-1 text-ink-primary">{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}