"use client";

import { useState } from "react";
import { useApp } from "@/lib/auth-context";
import { askRecord, detectRedFlag } from "@/lib/ai-engine";
import StructuredResponse from "@/components/ui/StructuredResponse";
import EmergencyBanner from "@/components/EmergencyBanner";
import { PageHeader, Card, Button } from "@/components/ui";

export default function AskPage() {
  const { patientId } = useApp();
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<ReturnType<typeof askRecord> | null>(null);
  const [redFlag, setRedFlag] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setRedFlag(null);
    setResponse(null);

    // Emergency Warning System: red-flag symptoms short-circuit everything.
    const flag = detectRedFlag(question);
    if (flag) setRedFlag(flag);

    // Prototype-stage: template logic over the demo record.
    // The production pipeline (retrieval → summarization → citation
    // check → safety check) lives in the Python backend.
    const answer = askRecord(patientId, question);
    setResponse(answer);
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Patient Portal" title="Ask My Record" />

      <p className="text-sm text-ink-secondary">
        Ask about your reports, medications, or what to expect — answers are
        grounded strictly in your own records, never general web knowledge.
      </p>

      {redFlag && <EmergencyBanner message={redFlag} />}

      {/* Question input */}
      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g., What did my last mammogram show?"
            className="w-full px-4 py-3 border border-clinical-border rounded-[10px] bg-clinical-surface text-ink-primary focus:ring-2 focus:ring-brand-teal/30 outline-none resize-y min-h-[80px] font-body"
            required
            disabled={loading}
          />
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={loading || !question.trim()}
          >
            {loading ? "Analyzing your records…" : "Ask AI"}
          </Button>
        </form>
      </Card>

      {/* Structured response — never a plain chat bubble */}
      {response && (
        <>
          <Card>
            <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">
              You asked
            </p>
            <p className="mt-1 text-sm text-ink-primary italic">
              &ldquo;{question}&rdquo;
            </p>
          </Card>
          <StructuredResponse answer={response} />
        </>
      )}
    </div>
  );
}
