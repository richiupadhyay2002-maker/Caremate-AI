"use client";

import { useState } from "react";
import Link from "next/link";
import { useApp } from "@/lib/auth-context";

import { Card, Button, PageHeader, StatusBadge } from "@/components/ui";
import { uploadDocument, UploadResult, getMyPatientRecord } from "@/lib/api";

/**
 * Upload File — real upload to the FastAPI backend with a privacy notice,
 * validation (type + size), progress feedback, and post-upload AI analysis.
 * Uploaded files belong to the signed-in user's private record only.
 */
export default function UploadPage() {
  const { isAuthed, loading: authLoading } = useApp();

  const [selected, setSelected] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");
  const [consent, setConsent] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState("");

  const ACCEPTED = ["pdf", "jpg", "jpeg", "png"];
  const MAX_MB = 10;

  const pick = (file: File | undefined | null) => {
    setFileError("");
    setError("");
    setResult(null);
    if (!file) return;
    const ext = (file.name.split(".").pop() || "").toLowerCase();
    if (!ACCEPTED.includes(ext)) {
      setFileError(
        `Unsupported format ".${ext}". Please choose PDF, JPG, JPEG or PNG. (DOC/DOCX are not supported by the processing pipeline yet.)`
      );
      setSelected(null);
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setFileError(
        `File is too large (${(file.size / 1048576).toFixed(1)} MB). Maximum is ${MAX_MB} MB.`
      );
      setSelected(null);
      return;
    }
    if (file.size === 0) {
      setFileError("This file is empty.");
      setSelected(null);
      return;
    }
    setSelected(file);
  };

  const doUpload = async () => {
    if (!selected) return;
    setProgress(5);
    setError("");
    setResult(null);
    try {
      const rec = await getMyPatientRecord();
      const res = await uploadDocument(rec.patient_id, selected, (p) =>
        setProgress(Math.max(p, 5))
      );
      setProgress(100);
      setResult(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Upload failed.";
      setError(
        /tesseract|ocr/i.test(msg)
          ? "Image uploads need OCR, which isn't available on this server. Please upload a text-based PDF, or ask the administrator to install Tesseract."
          : msg.replace(/^API error \d+:\s*/, "")
      );
    } finally {
      setTimeout(() => setProgress(null), 1200);
    }
  };

  if (authLoading) {
    return <p className="text-center py-12 text-ink-secondary">Loading…</p>;
  }

  if (!isAuthed) {
    return (
      <div className="max-w-lg mx-auto py-12 text-center space-y-4">
        <PageHeader eyebrow="Upload Report" title="Sign in to upload" />
        <p className="text-sm text-ink-secondary">
          Uploaded personal medical documents are private, so uploading
          requires an account. Just want to see how it works?{" "}
          <Link href="/demo" className="text-brand-teal font-medium">
            Try the demo
          </Link>{" "}
          with sample files instead.
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

  return (
    <div className="max-w-2xl space-y-6">
      <PageHeader eyebrow="My Account" title="Upload Report" />

      {/* Privacy notice / consent */}
      <Card className="border-status-review/40">
        <div className="flex items-start gap-3">
          <StatusBadge status="review" label="Privacy notice" />
        </div>
        <p className="text-xs text-ink-secondary mt-3 leading-relaxed">
          Your file is transmitted over an authenticated connection and stored
          privately under your account — never in a publicly accessible
          folder. Only you can view or process it. Uploaded documents are used
          to answer your questions and are not shared with other users. Care
          Mate AI provides information only — it never diagnoses or recommends
          treatments. Avoid uploading documents of others unless you are their
          authorized representative.
        </p>
        <label className="flex items-start gap-2 text-xs text-ink-secondary cursor-pointer mt-3">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-0.5 accent-[var(--color-brand-teal)]"
          />
          <span>I have read and accept the privacy notice above.</span>
        </label>
      </Card>

      {/* File picker */}
      <Card>
        <label className="block border border-dashed border-clinical-border rounded-[10px] px-4 py-8 text-center cursor-pointer hover:border-brand-teal/50">
          <input
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            className="hidden"
            onChange={(e) => pick(e.target.files?.[0])}
            disabled={!consent || progress !== null}
          />
          <p className="text-sm text-ink-primary font-medium">
            {consent ? "Click to choose a file" : "Accept the privacy notice to continue"}
          </p>
          <p className="text-xs text-ink-secondary mt-1">
            PDF, JPG, JPEG, PNG — up to 10 MB
          </p>
        </label>

        {selected && (
          <div className="flex items-center justify-between border border-clinical-border rounded-[10px] px-3 py-3 mt-4">
            <div className="min-w-0">
              <p className="text-sm text-ink-primary truncate">{selected.name}</p>
              <p className="text-xs text-ink-secondary">
                {(selected.size / 1024).toFixed(0)} KB
              </p>
            </div>
            <div className="flex gap-2 flex-shrink-0">
              <Button
                variant="primary"
                size="sm"
                onClick={doUpload}
                disabled={progress !== null}
              >
                {progress !== null ? `Uploading ${progress}%` : "Upload & process"}
              </Button>
              <button
                type="button"
                onClick={() => {
                  setSelected(null);
                  setFileError("");
                }}
                disabled={progress !== null}
                className="text-xs text-ink-secondary hover:text-status-urgent cursor-pointer disabled:opacity-50"
              >
                Remove
              </button>
            </div>
          </div>
        )}

        {progress !== null && progress < 100 && (
          <div className="mt-4">
            <div className="h-1 bg-clinical-border rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-teal transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-ink-secondary mt-2">
              Uploading and extracting text (OCR runs automatically for scanned
              pages)…
            </p>
          </div>
        )}

        {fileError && <p className="text-xs text-status-urgent mt-3">{fileError}</p>}
        {error && <p className="text-xs text-status-urgent mt-3">{error}</p>}

        {result && (
          <div className="mt-5 pt-4 border-t border-clinical-border space-y-3">
            <StatusBadge
              status="safe"
              label={`Processed as ${result.document_type.replace(/_/g, " ")}`}
              dot
            />
            <p className="text-xs text-ink-secondary">
              {result.num_chunks} text sections indexed
              {result.pages_extracted ? ` · ${result.pages_extracted} page(s)` : ""}
              {result.ocr_used ? " · OCR used" : ""}.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/ask">
                <Button variant="primary" size="md">
                  Ask about this document
                </Button>
              </Link>
              <Link href="/account">
                <Button variant="secondary" size="md">
                  View in my dashboard
                </Button>
              </Link>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
