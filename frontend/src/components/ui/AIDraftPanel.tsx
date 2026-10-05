"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import type { GenerationDetail, GenerationSummary } from "@/lib/api";

export interface AIDraftPanelProps {
  /** The generation to display */
  generation: GenerationDetail | GenerationSummary;
  /** Callback when a review action is taken */
  onReview?: (status: "approved" | "rejected" | "edited", notes?: string) => void;
  /** Callback to load source details */
  onViewSources?: () => void;
  /** Optional doctor notes field */
  doctorNotes?: string;
  /** Whether to show the full detail (citations, sources) */
  detailed?: boolean;
  className?: string;
}

/**
 * AI Draft Panel (per design brief):
 *  - Header strip: muted bg, "AI-generated draft · requires review" label
 *      (left), StatusBadge top-right
 *  - Body: response text with bold inline labels + source / citation links
 *  - Footer strip: top border, Approve / Edit / Reject / View sources buttons
 */
export function AIDraftPanel({
  generation,
  onReview,
  onViewSources,
  doctorNotes = "",
  detailed = false,
  className,
}: AIDraftPanelProps) {
  const [notes, setNotes] = useState(doctorNotes);
  const [notesExpanded, setNotesExpanded] = useState(false);

  const isDetail = (g: GenerationDetail | GenerationSummary): g is GenerationDetail =>
    "citations" in g && Array.isArray((g as GenerationDetail).citations);

    const citations = isDetail(generation) ? generation.citations : [];
  const fullJson = isDetail(generation)
    ? (generation.full_response_json ?? {})
    : {};

  // Derive a status for the badge
  const reviewStatus: "safe" | "review" | "urgent" | "pending" =
    generation.status === "approved"
      ? "safe"
      : generation.status === "rejected"
      ? "urgent"
      : "review";

  const confidenceLabel = Math.round((generation.confidence ?? 0) * 100);

  return (
    <Card className={cn("w-full", className)}>
      {/* ── Header strip ── */}
      <header className="bg-clinical-border/20 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-ink-primary">
            AI-generated draft · requires review
          </span>
          <span className="text-xs text-ink-secondary">
            Confidence: {confidenceLabel}%
          </span>
        </div>
        <StatusBadge status={reviewStatus} label={generation.status} dot />
      </header>

      {/* ── Body ── */}
      <div className="px-6 py-5">
        {/* The echoed question / prompt that triggered this draft */}
        {generation.query && (
          <div className="mb-4">
            <span className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">
              Prompt
            </span>
            <p className="mt-1 text-sm text-ink-primary italic">
              &ldquo;{generation.query}&rdquo;
            </p>
          </div>
        )}

        {/* Response with bold inline labels */}
        <div className="space-y-3">
          {renderResponseText(generation.response_text, fullJson)}
        </div>

        {/* Safety flags — always visible, never hidden */}
        {generation.safety_flags && generation.safety_flags.length > 0 && (
          <div className="mt-4 flex items-start gap-2">
            <StatusBadge status="urgent" label="Safety flag" dot />
            <div className="text-sm text-ink-secondary">
                            {generation.safety_flags.map((f, i) => (
                <span key={i} className="block">
                  • {f}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Evidence / sources line */}
        {detailed && citations.length > 0 && (
          <div className="mt-4 border-t border-clinical-border pt-3">
            <span className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">
              Evidence &amp; sources ({citations.length})
            </span>
            <ul className="mt-2 space-y-1.5">
              {citations.map((c, i) => (
                <li key={i} className="text-xs">
                  <span className="text-ink-primary font-medium">
                    {c.source_document}
                  </span>
                  {c.section && (
                    <>
                      {" "}
                      · <span className="text-ink-secondary">{c.section}</span>
                    </>
                  )}
                  {c.page_number && (
                    <>
                      {" "}
                      · p.{c.page_number}
                    </>
                  )}
                  <p className="text-ink-secondary mt-0.5 line-clamp-2">
                    {c.text_snippet}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Doctor notes display */}
        {generation.doctor_notes && (
          <div className="mt-3 border-t border-clinical-border pt-3">
            <span className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">
              Doctor&rsquo;s notes
            </span>
            <p className="mt-1 text-sm text-ink-primary whitespace-pre-wrap">
              {generation.doctor_notes}
            </p>
          </div>
        )}
      </div>

      {/* ── Footer strip with action buttons ── */}
      <footer className="border-t border-clinical-border px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {onReview &&
          generation.status !== "approved" &&
          generation.status !== "rejected" ? (
            <>
              <Button
                variant="primary"
                size="sm"
                onClick={() => onReview("approved")}
              >
                Approve
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setNotesExpanded(!notesExpanded)}
              >
                {notesExpanded ? "Hide" : "Add note"}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onReview("rejected")}
              >
                Reject
              </Button>
            </>
          ) : (
            <Button variant="ghost" size="sm">
              {generation.status === "approved" ? "Approved" : "Rejected"}
            </Button>
          )}
        </div>

        {onViewSources && (
          <Button variant="ghost" size="sm" onClick={onViewSources}>
            {detailed ? "View sources" : "Show sources"}
          </Button>
        )}
      </footer>
    </Card>
  );
}

/**
 * Render the response text, bolding inline labels that follow a
 * "Label: value" pattern (e.g. "Summary:", "Key Findings:").
 */
function renderResponseText(
  text: string | undefined,
  fullJson: Record<string, unknown>,
) {
  const raw = text || (fullJson?.response as string) || "";
  if (!raw) {
    return (
      <p className="text-sm text-ink-secondary">
        No response text available.
      </p>
    );
  }

  const sections = raw.split(/\n\s*\n/).filter(Boolean);

  return sections.map((section, i) => {
    const match = section.match(/^([A-Z][A-Za-z\s]+):\s*\n?(.*)$/s);

    if (match) {
      const label = match[1].trim();
      const content = match[2].trim();
      return (
        <div key={i}>
          <span className="text-xs font-semibold text-ink-secondary uppercase tracking-wider">
            {label}
          </span>
          <p className="mt-1 text-sm text-ink-primary leading-relaxed whitespace-pre-wrap">
            {content}
          </p>
        </div>
      );
    }

    return (
      <p
        key={i}
        className="text-sm text-ink-primary leading-relaxed whitespace-pre-wrap"
      >
        {section}
      </p>
    );
  });
}

