"use client";

/**
 * Symptom Journal storage (prototype stage: browser localStorage).
 * Entries are per demo patient and are shown in the Care Timeline feed.
 */
export interface JournalEntry {
  id: string;
  patient_id: string;
  date: string; // ISO date
  symptom: string;
  severity: number; // 1-10
  duration: string;
  notes: string;
  red_flag?: string | null;
}

const KEY_PREFIX = "caremate_journal_";

export function loadJournal(patientId: string): JournalEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY_PREFIX + patientId);
    return raw ? (JSON.parse(raw) as JournalEntry[]) : [];
  } catch {
    return [];
  }
}

export function saveJournal(patientId: string, entries: JournalEntry[]) {
  localStorage.setItem(KEY_PREFIX + patientId, JSON.stringify(entries));
}

export function addEntry(patientId: string, entry: Omit<JournalEntry, "id" | "patient_id">) {
  const entries = loadJournal(patientId);
  const full: JournalEntry = {
    ...entry,
    id: `${Date.now()}`,
    patient_id: patientId,
  };
  entries.push(full);
  saveJournal(patientId, entries);
  return full;
}

export function deleteEntry(patientId: string, id: string) {
  const entries = loadJournal(patientId).filter((e) => e.id !== id);
  saveJournal(patientId, entries);
}
