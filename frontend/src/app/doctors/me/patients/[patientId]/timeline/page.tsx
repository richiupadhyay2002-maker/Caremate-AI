"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getPatient, getDocuments } from "@/lib/demo-data";
import { PageHeader, Card, StatusBadge } from "@/components/ui";

type TimelineEvent = {
  id: string;
  date: string;
  event: string;
  detail: string;
  status: "ai_detected" | "confirmed" | "corrected";
  corrected_event?: string;
  corrected_detail?: string;
};

const KEY = "caremate_timeline_";

/**
 * Medical Timeline (editable) — the doctor can confirm or correct
 * AI-detected events. Corrections persist in the browser for the demo.
 */
export default function EditableTimelinePage() {
  const params = useParams<{ patientId: string }>();
  const patientId = params.patientId;
  const patient = getPatient(patientId);

  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editEvent, setEditEvent] = useState("");
  const [editDetail, setEditDetail] = useState("");

  useEffect(() => {
    if (!patient) return;
    try {
      const raw = localStorage.getItem(KEY + patientId);
      if (raw) {
        setEvents(JSON.parse(raw));
        return;
      }
    } catch {
      /* ignore */
    }
    // Seed from the demo record — marked AI-detected until confirmed
    setEvents(
      patient.history_events.map((e, i) => ({
        id: `ev-${i}`,
        date: e.date,
        event: e.event,
        detail: e.detail,
        status: "ai_detected" as const,
      })),
    );
  }, [patient]);

  const persist = (next: TimelineEvent[]) => {
    setEvents(next);
    localStorage.setItem(KEY + patientId, JSON.stringify(next));
  };

  const confirm = (id: string) =>
    persist(events.map((e) => (e.id === id ? { ...e, status: "confirmed" } : e)));

  const saveEdit = (id: string) =>
    persist(
      events.map((e) =>
        e.id === id
          ? {
            ...e,
            status: "corrected",
            corrected_event: editEvent,
            corrected_detail: editDetail,
          }
          : e,
      ),
    );

  const addEvent = () => {
    const date = new Date().toISOString().slice(0, 10);
    persist([
      ...events,
      {
        id: `ev-${Date.now()}`,
        date,
        event: "New event",
        detail: "",
        status: "confirmed",
      },
    ]);
  };

  if (!patient) return <p className="text-ink-secondary">Patient not found in demo data.</p>;

  const sorted = [...events].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Doctor Portal"
        title={`Medical Timeline — ${patient.name}`}
        action={
          <Link
            href={`/doctors/me/patients/${patientId}`}
            className="text-sm text-brand-teal font-medium"
          >
            ← Patient brief
          </Link>
        }
      />

      <p className="text-sm text-ink-secondary">
        Events detected from documents are marked{" "}
        <StatusBadge status="pending" label="AI-detected" /> until you confirm
        or correct them. Corrections are kept for this demo session.
      </p>

      <Card>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-base font-heading text-ink-primary">
            Timeline ({sorted.length} events)
          </h2>
          <button
            type="button"
            onClick={addEvent}
            className="text-xs px-3 py-1.5 rounded-[8px] border border-clinical-border text-ink-secondary hover:text-brand-teal cursor-pointer"
          >
            + Add event
          </button>
        </div>

        <ul className="space-y-4">
          {sorted.map((e) => {
            const displayEvent = e.corrected_event ?? e.event;
            const displayDetail = e.corrected_detail ?? e.detail;
            const isEditing = editingId === e.id;

            return (
              <li
                key={e.id}
                className="border-l-2 border-clinical-border pl-4 py-1"
              >
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="flex-1 min-w-[240px]">
                    <p className="text-xs text-ink-secondary font-medium">
                      {e.date} ·{" "}
                      {e.status === "ai_detected" ? (
                        <StatusBadge status="pending" label="AI-detected" />
                      ) : e.status === "confirmed" ? (
                        <StatusBadge status="safe" label="Confirmed" />
                      ) : (
                        <StatusBadge status="review" label="Corrected by doctor" />
                      )}
                    </p>
                    {isEditing ? (
                      <div className="mt-2 space-y-2">
                        <input
                          value={editEvent}
                          onChange={(ev) => setEditEvent(ev.target.value)}
                          className="w-full px-3 py-1.5 border border-clinical-border rounded-[8px] bg-clinical-surface text-sm outline-none"
                        />
                        <textarea
                          value={editDetail}
                          onChange={(ev) => setEditDetail(ev.target.value)}
                          className="w-full px-3 py-1.5 border border-clinical-border rounded-[8px] bg-clinical-surface text-sm outline-none min-h-[60px]"
                        />
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              saveEdit(e.id);
                              setEditingId(null);
                            }}
                            className="text-xs px-3 py-1.5 rounded-[8px] bg-brand-teal text-white cursor-pointer"
                          >
                            Save correction
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingId(null)}
                            className="text-xs px-3 py-1.5 rounded-[8px] border border-clinical-border text-ink-secondary cursor-pointer"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <p className="text-sm font-semibold text-ink-primary mt-1">
                          {displayEvent}
                        </p>
                        <p className="text-sm text-ink-secondary">{displayDetail}</p>
                      </>
                    )}
                  </div>

                  {!isEditing && (
                    <div className="flex gap-2">
                      {e.status === "ai_detected" && (
                        <button
                          type="button"
                          data-testid={`confirm-${e.id}`}
                          onClick={() => confirm(e.id)}
                          className="text-xs px-3 py-1.5 rounded-[8px] bg-status-safe-bg text-status-safe font-medium cursor-pointer"
                        >
                          Confirm
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => {
                          setEditingId(e.id);
                          setEditEvent(displayEvent);
                          setEditDetail(displayDetail);
                        }}
                        className="text-xs px-3 py-1.5 rounded-[8px] bg-status-review-bg text-status-review font-medium cursor-pointer"
                      >
                        Correct
                      </button>
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </Card>

      <Card>
        <h2 className="text-base font-heading text-ink-primary mb-2">Source documents</h2>
        <ul className="text-sm text-ink-secondary space-y-1">
          {getDocuments(patientId).map((d) => (
            <li key={d.id}>
              {d.date} — {d.title} ({d.type})
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
