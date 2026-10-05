"use client";

import { useState } from "react";
import { askRecord, detectRedFlag } from "@/lib/ai-engine";
import { DEMO_PATIENTS } from "@/lib/demo-data";
import StructuredResponse from "@/components/ui/StructuredResponse";
import { PageHeader, Card, Button } from "@/components/ui";

/**
 * Ask the Patient Record — doctor-facing version of the grounded Q&A
 * interface. Same retrieval, same citation-first output, same five-category
 * safety labeling.
 */
export default function DoctorAskPage() {
  const [patientId, setPatientId] = useState(DEMO_PATIENTS[0].id);
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<ReturnType<typeof askRecord> | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setResponse(null);
    // The same engine backs both portals; in production the doctor-side
    // query goes through the Python RAG pipeline with clinician scope.
    setResponse(askRecord(patientId, question));
    setLoading(false);
  };

  const redFlag = question ? detectRedFlag(question) : null;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Doctor Portal" title="Ask the Patient Record" />

      <p className="text-sm text-ink-secondary">
        Grounded strictly in the selected patient&apos;s own records, with
        citations for every claim. Same safety rules as the patient portal —
        no diagnosis and no treatment decisions are generated.
      </p>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
              Patient
            </label>
            <select
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              className="w-full px-3 py-2 border border-clinical-border rounded-[10px] bg-clinical-surface text-sm text-ink-primary outline-none focus:ring-2 focus:ring-brand-teal/30"
            >
              {DEMO_PATIENTS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.id}) — {p.diagnosis}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
              Question
            </label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g., What did the colectomy pathology report say about margins?"
              className="w-full px-3 py-3 border border-clinical-border rounded-[10px] bg-clinical-surface text-ink-primary outline-none resize-y min-h-[80px] font-body"
              required
              disabled={loading}
            />
          </div>
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={loading || !question.trim()}
          >
            {loading ? "Searching the record…" : "Ask"}
          </Button>
        </form>
        {redFlag && (
          <p className="mt-3 text-xs text-status-urgent">
            Note: your question mentions a red-flag pattern — the answer will
            carry an urgent safety label.
          </p>
        )}
      </Card>

      {response && (
        <>
          <Card>
            <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">
              Asked about {patientId}
            </p>
            <p className="mt-1 text-sm text-ink-primary italic">&ldquo;{question}&rdquo;</p>
          </Card>
          <StructuredResponse answer={response} />
        </>
      )}
    </div>
  );
}
