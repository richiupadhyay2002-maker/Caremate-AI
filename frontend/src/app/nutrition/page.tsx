"use client";

import { useState } from "react";
import { useApp } from "@/lib/auth-context";
import { nutritionAnswer, detectRedFlag } from "@/lib/ai-engine";
import StructuredResponse from "@/components/ui/StructuredResponse";
import EmergencyBanner from "@/components/EmergencyBanner";
import { PageHeader, Card, Button } from "@/components/ui";

/**
 * Nutrition & Diet Q&A — food and appetite guidance, automatically checked
 * against the patient's recorded medication list before being shown.
 */
export default function NutritionPage() {
  const { patientId } = useApp();
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<ReturnType<typeof nutritionAnswer> | null>(null);
  const [redFlag, setRedFlag] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setRedFlag(null);
    setResponse(null);

    const flag = detectRedFlag(question);
    if (flag) setRedFlag(flag);

    const answer = nutritionAnswer(patientId, question);
    setResponse(answer);
    setLoading(false);
  };

  const examples = [
    "Can I eat grapefruit while on my tablets?",
    "What foods should I avoid during chemotherapy?",
    "Is spinach safe for me?",
  ];

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Patient Portal" title="Nutrition & Diet" />

      <p className="text-sm text-ink-secondary">
        Every food suggestion is automatically checked against your recorded
        medication list before it is shown to you.
      </p>

      {redFlag && <EmergencyBanner message={redFlag} />}

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g., Are there foods I should avoid with my medication?"
            className="w-full px-4 py-3 border border-clinical-border rounded-[10px] bg-clinical-surface text-ink-primary focus:ring-2 focus:ring-brand-teal/30 outline-none resize-y min-h-[70px] font-body"
            required
            disabled={loading}
          />
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={loading || !question.trim()}
          >
            {loading ? "Checking your medications…" : "Ask"}
          </Button>
        </form>
      </Card>

      <Card>
        <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-2">
          Try asking
        </p>
        <div className="flex flex-wrap gap-2">
          {examples.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setQuestion(ex)}
              className="text-xs px-3 py-1.5 border border-clinical-border rounded-full text-ink-secondary hover:text-brand-teal hover:border-brand-teal/40 cursor-pointer"
            >
              {ex}
            </button>
          ))}
        </div>
      </Card>

      {response && (
        <>
          <Card>
            <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">
              You asked
            </p>
            <p className="mt-1 text-sm text-ink-primary italic">&ldquo;{question}&rdquo;</p>
          </Card>
          <StructuredResponse answer={response} />
        </>
      )}
    </div>
  );
}
