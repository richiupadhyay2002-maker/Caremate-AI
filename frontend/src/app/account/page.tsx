"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useApp } from "@/lib/auth-context";
import {
  listDocuments,
  deleteDocument,
  listMyGenerations,
  uploadDocument,
  updateProfile,
  getMyPatientRecord,
  DocumentRef,
  MyGeneration,
} from "@/lib/api";
import { PageHeader, Card, Button, StatusBadge, Timeline } from "@/components/ui";
import Link from "next/link";

export default function AccountDashboard() {
  const { user, isAuthed, loading: authLoading, logout, refreshUser } = useApp();
  const [docs, setDocs] = useState<DocumentRef[]>([]);
  const [analyses, setAnalyses] = useState<MyGeneration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);
  const [uploadPct, setUploadPct] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [profileSaved, setProfileSaved] = useState(false);
  const [profileError, setProfileError] = useState("");
  const patientIdRef = useRef<string | null>(null);

  const getPatientId = useCallback(async (): Promise<string> => {
    if (patientIdRef.current) return patientIdRef.current;
    const rec = await getMyPatientRecord();
    patientIdRef.current = rec.patient_id;
    return rec.patient_id;
  }, []);

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError("");
    try {
      const pid = await getPatientId();
      const [docList, genList] = await Promise.all([
        listDocuments(pid),
        listMyGenerations(pid),
      ]);
      setDocs(docList);
      setAnalyses(genList);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load your data.");
    } finally {
      setLoading(false);
    }
  }, [user, getPatientId]);

  useEffect(() => {
    if (!authLoading && user) {
      setName(user.full_name);
      load();
    } else if (!authLoading && !user) {
      setLoading(false);
    }
  }, [authLoading, user, load]);

  if (authLoading) {
    return <p className="text-center py-12 text-ink-secondary">Loading…</p>;
  }

  if (!isAuthed || !user) {
    return (
      <div className="max-w-lg mx-auto py-12 text-center space-y-4">
        <h1 className="text-2xl font-heading text-ink-primary">Your dashboard</h1>
        <p className="text-sm text-ink-secondary">
          Sign in to view your uploaded files, analyses, and profile.
          <br />
          Want to look around first?{" "}
          <Link href="/demo" className="text-brand-teal font-medium">
            Try the demo
          </Link>{" "}
          instead.
        </p>
        <div className="flex gap-3 justify-center">
          <Link href="/login">
            <Button variant="primary" size="md">Sign in</Button>
          </Link>
          <Link href="/signup">
            <Button variant="secondary" size="md">Sign up</Button>
          </Link>
        </div>
      </div>
    );
  }

  const handleUpload = async (file: File) => {
    setError("");
    setUploadPct(10);
    try {
      const pid = await getPatientId();
      await uploadDocument(pid, file, (pct: number) => setUploadPct(pct));
      setUploadPct(100);
      await load();
      setTimeout(() => setUploadPct(null), 1500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed.";
      setError(
        /tesseract|ocr/i.test(msg)
          ? "Image uploads need OCR, which isn't available on this server. Please upload a text-based PDF."
          : msg.replace(/^API error \d+:\s*/, "")
      );
      setUploadPct(null);
    }
  };

  const handleDelete = async (docId: string) => {
    setDeleting(docId);
    try {
      const pid = await getPatientId();
      await deleteDocument(pid, docId);
      setDocs((prev) => prev.filter((d) => d.document_id !== docId));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    } finally {
      setDeleting(null);
    }
  };

  const handleSaveProfile = async () => {
    setProfileSaved(false);
    setProfileError("");
    try {
      await updateProfile(name);
      await refreshUser();
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 2500);
    } catch (err: unknown) {
      setProfileError(err instanceof Error ? err.message : "Could not save profile.");
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="My Account"
        title={`Welcome back, ${user?.full_name?.split(" ")[0] ?? "there"}`}
        action={
          <button
            type="button"
            onClick={() => {
              logout();
              window.location.href = "/";
            }}
            className="text-sm text-ink-secondary hover:text-status-urgent font-medium cursor-pointer"
          >
            Log out
          </button>
        }
      />

      {error && (
        <Card className="border-status-urgent/30">
          <p className="text-sm text-status-urgent">{error}</p>
        </Card>
      )}

      {/* Upload */}
      <Card>
        <h2 className="text-lg font-heading text-ink-primary mb-2">Upload a report</h2>
        <p className="text-xs text-ink-secondary mb-4">
          PDF, JPG, JPEG, PNG — maximum 10 MB. Files are stored privately under
          your account and processed by the CareMate AI pipeline. We never
          display your documents to other users.
        </p>
        <UploadWidget onUpload={handleUpload} progress={uploadPct} />
      </Card>

      {/* Files */}
      <Card>
        <h2 className="text-lg font-heading text-ink-primary mb-1">My files</h2>
        <p className="text-sm text-ink-secondary mb-3">
          {loading ? "Loading…" : `${docs.length} document${docs.length === 1 ? "" : "s"}`}
        </p>
        {!loading && (
          <ul className="divide-y divide-clinical-border">
            {docs.map((d) => (
              <li key={d.document_id} className="py-3 flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-ink-primary">{d.title}</p>
                  <p className="text-xs text-ink-secondary mt-0.5">
                    {d.document_type} · {d.source}
                    {d.created_at
                      ? ` · ${new Date(d.created_at).toLocaleDateString()}`
                      : ""}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(d.document_id)}
                  disabled={deleting === d.document_id}
                  className="text-xs text-ink-secondary hover:text-status-urgent cursor-pointer disabled:opacity-50"
                >
                  {deleting === d.document_id ? "Deleting…" : "Delete"}
                </button>
              </li>
            ))}
            {docs.length === 0 && (
              <li className="py-3 text-sm text-ink-secondary">
                No files yet — upload your first report above.
              </li>
            )}
          </ul>
        )}
      </Card>

      {/* Analyses */}
      <Card>
        <h2 className="text-lg font-heading text-ink-primary mb-1">Previous analyses</h2>
        <p className="text-sm text-ink-secondary mb-3">
          Results of AI runs on your uploaded documents.
        </p>
        {loading ? (
          <p className="text-sm text-ink-secondary">Loading…</p>
        ) : analyses.length === 0 ? (
          <p className="text-sm text-ink-secondary">
            No analyses yet. Upload a report and ask a question — results appear here.
          </p>
        ) : (
          <Timeline
            items={analyses.slice(0, 12).map((a) => ({
              id: String(a.id),
              date: a.created_at,
              title: a.query.slice(0, 120),
              subtitle:
                (a.response_text || "").slice(0, 160) +
                ((a.response_text || "").length > 160 ? "…" : ""),
            }))}
          />
        )}
      </Card>

      {/* Profile */}
      <Card>
        <h2 className="text-lg font-heading text-ink-primary mb-3">Profile</h2>
        <div className="space-y-3 max-w-sm">
          <div>
            <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
              Display name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-clinical-border rounded-[10px] bg-clinical-surface text-ink-primary outline-none focus:ring-2 focus:ring-brand-teal/30"
            />
          </div>
          <div>
            <span className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
              Email
            </span>
            <p className="text-sm text-ink-primary">{user?.email}</p>
          </div>
          <Button variant="primary" size="sm" onClick={handleSaveProfile}>
            Save profile
          </Button>
          {profileSaved && (
            <StatusBadge status="safe" label="Profile saved" dot />
          )}
          {profileError && (
            <p className="text-xs text-status-urgent">{profileError}</p>
          )}
        </div>
      </Card>
    </div>
  );
}

function UploadWidget({
  onUpload,
  progress,
}: {
  onUpload: (file: File) => void;
  progress: number | null;
}) {
  const [selected, setSelected] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");

  const ACCEPTED = ["pdf", "jpg", "jpeg", "png"];
  const MAX_MB = 10;

  const pick = (file: File | undefined | null) => {
    setFileError("");
    if (!file) return;
    const ext = (file.name.split(".").pop() || "").toLowerCase();
    if (!ACCEPTED.includes(ext)) {
      setFileError(
        `Unsupported format “.${ext}”. Please choose PDF, JPG, JPEG or PNG.`
      );
      setSelected(null);
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setFileError(`File is too large (${(file.size / 1048576).toFixed(1)} MB). Maximum is ${MAX_MB} MB.`);
      setSelected(null);
      return;
    }
    setSelected(file);
  };

  return (
    <div className="space-y-3">
      <label className="block border border-dashed border-clinical-border rounded-[10px] px-4 py-6 text-center cursor-pointer hover:border-brand-teal/50">
        <input
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          className="hidden"
          onChange={(e) => pick(e.target.files?.[0])}
        />
        <p className="text-sm text-ink-primary font-medium">
          Click to choose a file
        </p>
        <p className="text-xs text-ink-secondary mt-1">
          PDF, JPG, JPEG, PNG — up to 10 MB
        </p>
      </label>

      {selected && (
        <div className="flex items-center justify-between border border-clinical-border rounded-[10px] px-3 py-2">
          <div className="min-w-0">
            <p className="text-sm text-ink-primary truncate">{selected.name}</p>
            <p className="text-xs text-ink-secondary">
              {(selected.size / 1024).toFixed(0)} KB · ready to upload
            </p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <Button
              variant="primary"
              size="sm"
              onClick={() => onUpload(selected)}
              disabled={progress !== null}
            >
              {progress !== null ? `Uploading ${progress}%…` : "Upload"}
            </Button>
            <button
              type="button"
              onClick={() => setSelected(null)}
              disabled={progress !== null}
              className="text-xs text-ink-secondary hover:text-status-urgent cursor-pointer disabled:opacity-50"
            >
              Remove
            </button>
          </div>
        </div>
      )}

      {fileError && <p className="text-xs text-status-urgent">{fileError}</p>}
    </div>
  );
}
