"use client";

import { useEffect, useState } from "react";
import {
  listDemoSamples,
  processDemoSample,
  API_BASE_URL,
  SampleListResponse,
  StructuredAIResponse,
} from "@/lib/api";
import StructuredResponse from "@/components/ui/StructuredResponse";
import { PageHeader, Card, Button, StatusBadge } from "@/components/ui";

/**
 * Try Demo — explore CareMate without an account: pick a bundled sample
 * file (synthetic, open-format style) and see the real AI pipeline process
 * it. Clearly labeled as demo/sample data.
 */
export default function DemoPage() {
  const [data, setData] = useState<SampleListResponse | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [preview, setPreview] = useState<string>("");
  const [result, setResult] = useState<StructuredAIResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listDemoSamples()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load samples."));
  }, []);

  const select = async (sampleId: string) => {
    setSelected(sampleId);
    setResult(null);
    setPreview("");
    setError("");
    try {
      const resp = await fetch(
        `${API_BASE_URL}/demo/samples/${sampleId}/content`
      );
      if (resp.ok) {
        const json = await resp.json();
        setPreview(json.content || "");
      }
    } catch {
      /* preview is optional */
    }
  };

  const runProcessing = async () => {
    if (!selected) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const resp = await processDemoSample(selected);
      setResult(resp);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Processing failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Try Demo" title="Sample Files" />

      <Card className="border-status-review/40">
        <div className="flex items-start gap-3">
          <StatusBadge status="review" label="Demo / Sample Data" dot />
          <p className="text-xs text-ink-secondary">
            {data?.notice ??
              "These files are synthetic and contain no real patient information."}
          </p>
        </div>
        {data && (
          <p className="text-xs text-ink-secondary mt-2">{data.sources_note}</p>
        )}
      </Card>

      <Card className="p-0">
        <div className="divide-y divide-clinical-border">
          {(data?.samples ?? []).map((s) => (
            <button
              key={s.sample_id}
              type="button"
              onClick={() => select(s.sample_id)}
              className={`w-full text-left px-4 py-3 flex items-center justify-between gap-4 cursor-pointer hover:bg-clinical-border/10 ${
                selected === s.sample_id ? "bg-clinical-border/10" : ""
              }`}
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-ink-primary truncate">{s.title}</p>
                <p className="text-xs text-ink-secondary mt-0.5">
                  {s.filename} · {s.kind.replace(/_/g, " ")} ·{" "}
                  {(s.size_bytes / 1024).toFixed(1)} KB
                </p>
              </div>
              <span className="text-xs text-brand-teal font-medium whitespace-nowrap">
                {selected === s.sample_id ? "Selected" : "Select"}
              </span>
            </button>
          ))}
          {!data && <div className="px-4 py-3 text-sm text-ink-secondary">Loading samples…</div>}
        </div>
      </Card>

      {selected && (
        <>
          {preview && (
            <Card>
              <h2 className="text-base font-heading text-ink-primary mb-2">
                File preview
              </h2>
              <pre className="text-xs text-ink-secondary whitespace-pre-wrap font-body max-h-56 overflow-y-auto">
                {preview.slice(0, 1500)}
                {preview.length > 1500 ? "\n…" : ""}
              </pre>
            </Card>
          )}

          <Card>
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <h2 className="text-base font-heading text-ink-primary">
                  Process with CareMate AI
                </h2>
                <p className="text-xs text-ink-secondary mt-0.5">
                  Runs the same six-agent pipeline used for uploaded reports.
                </p>
              </div>
              <Button
                variant="primary"
                size="md"
                onClick={runProcessing}
                disabled={busy}
              >
                {busy ? "Processing…" : "Process sample"}
              </Button>
            </div>
          </Card>
        </>
      )}

      {error && (
        <Card className="border-status-urgent/30">
          <p className="text-sm text-status-urgent">{error}</p>
        </Card>
      )}

      {result && (
        <>
          <Card>
            <p className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">
              AI analysis of the selected sample
            </p>
          </Card>
          <StructuredResponse
            answer={{
              question: "Summarize this report in plain language.",
              summary: result.response,
              key_findings:
                (result.citations || []).map(
                  (c: { section: string; text_snippet: string }) =>
                    `${c.section}: ${c.text_snippet}`
                ),
              citations: (result.citations || []).map(
                (c: {
                  chunk_id: string;
                  source_document: string;
                  section: string;
                  text_snippet: string;
                }) => ({
                  document_id: c.chunk_id,
                  document_title: c.source_document,
                  section: c.section,
                  snippet: c.text_snippet,
                })
              ),
              missing_info: [
                "The care team's interpretation of this report.",
                "Any prior reports not included in this sample.",
              ],
              safety:
                result.safety_flags && result.safety_flags.length > 0
                  ? "needs_clinician_review"
                  : "safe_information",
              safety_note:
                "This analysis comes from a synthetic demo file. Always confirm with a clinician for real reports.",
              generator: "backend-rag",
            }}
          />
        </>
      )}
    </div>
  );
}
