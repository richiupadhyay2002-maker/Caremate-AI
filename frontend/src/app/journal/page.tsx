"use client";

import { useEffect, useState } from "react";
import { useApp } from "@/lib/auth-context";
import {
  loadJournal,
  addEntry,
  deleteEntry,
  JournalEntry,
} from "../journal-storage";
import { detectRedFlag } from "@/lib/ai-engine";
import EmergencyBanner from "@/components/EmergencyBanner";
import { PageHeader, Card, Button, StatusBadge } from "@/components/ui";

/**
 * Symptom Journal — log symptoms with severity, date, duration and notes.
 * Red-flag symptoms trigger the Emergency Warning System immediately.
 */
export default function JournalPage() {
  const { patientId } = useApp();
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [redFlag, setRedFlag] = useState<string | null>(null);

  // form state
  const [symptom, setSymptom] = useState("");
  const [severity, setSeverity] = useState(5);
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [duration, setDuration] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    setEntries(loadJournal(patientId));
  }, [patientId]);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!symptom.trim()) return;

    const flag = detectRedFlag(symptom + " " + notes);
    addEntry(patientId, {
      date,
      symptom: symptom.trim(),
      severity,
      duration: duration.trim() || "—",
      notes: notes.trim(),
      red_flag: flag,
    });
    setEntries(loadJournal(patientId));
    setSymptom("");
    setSeverity(5);
    setDuration("");
    setNotes("");
    if (flag) setRedFlag(flag);
  };

  const sorted = [...entries].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Patient Portal" title="Symptom Journal" />

      <p className="text-sm text-ink-secondary">
        Track what you feel between visits — severity, date, duration and
        notes. Entries appear in your Care Timeline and can help your care
        team spot patterns.
      </p>

      {redFlag && <EmergencyBanner message={redFlag} />}

      <Card>
        <h2 className="text-base font-heading text-ink-primary mb-3">Log a symptom</h2>
        <form onSubmit={handleAdd} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
                Symptom
              </label>
              <input
                type="text"
                value={symptom}
                onChange={(e) => setSymptom(e.target.value)}
                placeholder="e.g., Nausea after breakfast"
                className="w-full px-3 py-2 border border-clinical-border rounded-[10px] bg-clinical-surface text-ink-primary outline-none focus:ring-2 focus:ring-brand-teal/30"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
                Date
              </label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full px-3 py-2 border border-clinical-border rounded-[10px] bg-clinical-surface text-ink-primary outline-none focus:ring-2 focus:ring-brand-teal/30"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
                Duration
              </label>
              <input
                type="text"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                placeholder="e.g., About 2 hours"
                className="w-full px-3 py-2 border border-clinical-border rounded-[10px] bg-clinical-surface text-ink-primary outline-none focus:ring-2 focus:ring-brand-teal/30"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
                Severity: {severity}/10
              </label>
              <input
                type="range"
                min={1}
                max={10}
                value={severity}
                onChange={(e) => setSeverity(Number(e.target.value))}
                className="w-full accent-[var(--color-brand-teal)]"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
              Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Anything else worth noting (triggers, what helped…)"
              className="w-full px-3 py-2 border border-clinical-border rounded-[10px] bg-clinical-surface text-ink-primary outline-none resize-y min-h-[60px] focus:ring-2 focus:ring-brand-teal/30"
            />
          </div>
          <Button type="submit" variant="primary" size="md">
            Save entry
          </Button>
        </form>
      </Card>

      <Card>
        <h2 className="text-base font-heading text-ink-primary mb-3">
          Your entries over time
        </h2>
        {sorted.length === 0 ? (
          <p className="text-sm text-ink-secondary">No entries yet.</p>
        ) : (
          <ul className="divide-y divide-clinical-border">
            {sorted.map((e) => (
              <li key={e.id} className="py-3 flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm font-medium text-ink-primary">{e.symptom}</p>
                    <StatusBadge
                      status={e.severity >= 7 ? "review" : e.red_flag ? "urgent" : "safe"}
                      label={`Severity ${e.severity}/10`}
                    />
                    {e.red_flag && (
                      <StatusBadge status="urgent" label="Red flag" dot />
                    )}
                  </div>
                  <p className="text-xs text-ink-secondary mt-1">
                    {e.date} · {e.duration}
                    {e.notes ? ` · ${e.notes}` : ""}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    deleteEntry(patientId, e.id);
                    setEntries(loadJournal(patientId));
                  }}
                  className="text-xs text-ink-secondary hover:text-status-urgent cursor-pointer"
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
