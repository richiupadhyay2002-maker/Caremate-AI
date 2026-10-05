"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import {
  listPatientGenerations,
  getGenerationDetail,
  reviewGeneration,
  getPatientContext,
  PatientContext,
  GenerationSummary,
  GenerationDetail,
} from "@/lib/api";
import { PageHeader, Card, StatusBadge } from "@/components/ui";
import { AIDraftPanel } from "@/components/ui/AIDraftPanel";

export default function PatientBriefPage() {
  const params = useParams();
  const { token } = useAuth();
  const [context, setContext] = useState<PatientContext | null>(null);
  const [generations, setGenerations] = useState<GenerationSummary[]>([]);
  const [details, setDetails] = useState<Record<number, GenerationDetail>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const patientId = params.patientId as string;

  useEffect(() => {
    if (!token) return;
    const fetchData = async () => {
      try {
        setLoading(true);
        const [ctx, gens] = await Promise.all([
          getPatientContext(patientId).catch(() => null),
          listPatientGenerations(patientId),
        ]);
        setContext(ctx);
        setGenerations(gens || []);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token, patientId]);

  const handleExpand = async (genId: number) => {
    if (!details[genId]) {
      try {
        const detail = await getGenerationDetail(genId);
        setDetails((prev) => ({ ...prev, [genId]: detail }));
      } catch (err) {
        console.error("Failed to fetch detail:", err);
      }
    }
  };

  const handleReview = (genId: number) => (
    status: "approved" | "rejected" | "edited",
    notes?: string,
  ) => {
    reviewGeneration(genId, status, notes)
      .then((updated) => {
        setGenerations((prev) =>
          prev.map((g) =>
            g.id === genId
              ? { ...g, status: updated.status, reviewed_at: updated.reviewed_at }
              : g,
          ),
        );
        setDetails((prev) => ({ ...prev, [genId]: updated }));
      })
      .catch((err) => console.error("Review failed:", err));
  };

  if (loading)
    return <div className="text-center py-12 text-ink-secondary">Loading…</div>;
  if (!token)
    return (
      <div className="text-center py-12">
        <p className="text-ink-secondary">
          Please{" "}
          <Link href="/login" className="text-brand-teal font-medium">
            log in
          </Link>
          .
        </p>
      </div>
    );

  return (
    <div className="space-y-6">
      <div className="mb-2">
        <Link href="/doctors/me">
          <span className="text-xs text-ink-secondary hover:text-brand-teal cursor-pointer">
            ← Back to patient list
          </span>
        </Link>
      </div>

      <PageHeader
        eyebrow="Doctor Portal"
        title={context?.name || patientId}
        action={
          <StatusBadge status="safe" label="Active record" dot />
        }
      />

      {error && (
        <Card className="border-status-urgent/30">
          <p className="text-sm text-status-urgent">{error}</p>
        </Card>
      )}

      {context && (
        <Card>
          <h2 className="text-lg font-heading text-ink-primary mb-3">
            Patient Summary
          </h2>
          <p className="text-sm text-ink-secondary mb-2">
            Age: {context.age} · {context.sex} · ID:{" "}
            <span className="font-mono">{context.patient_id}</span>
          </p>
          {context.medical_history && context.medical_history.length > 0 && (
            <p className="text-sm text-ink-secondary">
              Diagnosis: {context.medical_history.join(", ")}
            </p>
          )}
        </Card>
      )}

      {generations.length === 0 ? (
        <Card>
          <p className="text-ink-secondary">
            No AI-generated drafts for this patient.
          </p>
        </Card>
      ) : (
        <div className="space-y-4">
          {generations.map((gen) => (
            <Card key={gen.id}>
              <AIDraftPanel
                generation={details[gen.id] || gen}
                detailed={!!details[gen.id]}
                onReview={handleReview(gen.id)}
                onViewSources={() => handleExpand(gen.id)}
              />
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
