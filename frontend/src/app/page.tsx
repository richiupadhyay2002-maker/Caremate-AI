"use client";

import Link from "next/link";
import { useApp } from "@/lib/auth-context";
import { Card, Button, StatusBadge } from "@/components/ui";

/**
 * Landing page — makes it immediately clear what CareMate does:
 * upload a medical report and get a cited, safety-checked AI analysis.
 * Buttons: Login | Sign Up | Try Demo | Upload Report.
 */
export default function HomePage() {
  const { isAuthed, user, loading } = useApp();

  return (
    <div className="space-y-10 py-4">
      {/* Hero */}
      <div className="max-w-2xl">
        <div className="flex items-center gap-2 mb-3">
          <StatusBadge status="safe" label="Safety-checked AI" dot />
          <span className="text-[10px] px-2 py-1 bg-status-review-bg text-status-review rounded uppercase font-medium">
            Demo data only
          </span>
        </div>
        <h1 className="text-3xl font-heading text-ink-primary leading-tight">
          Understand your medical reports — with every answer cited.
        </h1>
        <p className="text-sm text-ink-secondary mt-3 leading-relaxed">
          CareMate AI lets you upload a pathology, radiology or lab report and
          ask questions about it. Every answer is grounded strictly in the
          documents you provide, shows its sources, and is labelled with a
          five-category safety status. It never diagnoses and never picks a
          treatment — it explains.
        </p>

        {/* Primary actions */}
        <div className="flex flex-wrap gap-3 mt-6">
          {isAuthed ? (
            <>
              <Link href="/account">
                <Button variant="primary" size="lg">
                  Open my dashboard
                </Button>
              </Link>
              <Link href="/upload">
                <Button variant="secondary" size="lg">
                  Upload Report
                </Button>
              </Link>
            </>
          ) : (
            <>
              <Link href="/login">
                <Button variant="secondary" size="lg">
                  Login
                </Button>
              </Link>
              <Link href="/signup">
                <Button variant="primary" size="lg">
                  Sign Up
                </Button>
              </Link>
              <Link href="/demo">
                <Button variant="secondary" size="lg">
                  Try Demo
                </Button>
              </Link>
              <Link href="/upload">
                <Button variant="ghost" size="lg">
                  Upload Report →
                </Button>
              </Link>
            </>
          )}
        </div>
        {!isAuthed && (
          <p className="text-xs text-ink-secondary mt-3">
            Uploading personal reports requires an account (your files stay
            private). The demo uses synthetic sample files — no signup needed.
          </p>
        )}
      </div>

      {/* How it works */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <p className="text-xs font-semibold text-brand-teal uppercase tracking-wider">
            Step 1
          </p>
          <h2 className="text-base font-heading text-ink-primary mt-1">
            Upload a report
          </h2>
          <p className="text-sm text-ink-secondary mt-1">
            PDF or a clear photo of a report — pathology, radiology, labs or
            biomarkers.
          </p>
        </Card>
        <Card>
          <p className="text-xs font-semibold text-brand-teal uppercase tracking-wider">
            Step 2
          </p>
          <h2 className="text-base font-heading text-ink-primary mt-1">
            Ask questions
          </h2>
          <p className="text-sm text-ink-secondary mt-1">
            Get plain-language explanations in a structured, cited format —
            with sources and what the report does not say.
          </p>
        </Card>
        <Card>
          <p className="text-xs font-semibold text-brand-teal uppercase tracking-wider">
            Step 3
          </p>
          <h2 className="text-base font-heading text-ink-primary mt-1">
            Review anytime
          </h2>
          <p className="text-sm text-ink-secondary mt-1">
            Your files and previous analyses stay in your private dashboard.
          </p>
        </Card>
      </div>

      {/* Explore the full prototype */}
      <Card>
        <h2 className="text-lg font-heading text-ink-primary mb-2">
          Explore the full prototype
        </h2>
        <p className="text-sm text-ink-secondary mb-4">
          The two-sided demo portals (patient &amp; doctor) are open without an
          account — all data is synthetic.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/dashboard">
            <Button variant="secondary" size="md">
              Patient portal demo
            </Button>
          </Link>
          <Link href="/doctors/me">
            <Button variant="ghost" size="md">
              Doctor portal demo
            </Button>
          </Link>
          <Link href="/demo">
            <Button variant="ghost" size="md">
              Sample files
            </Button>
          </Link>
        </div>
      </Card>

      <p className="text-xs text-ink-secondary">
        CareMate AI is a demonstration prototype. It does not provide medical
        advice, diagnosis, or treatment decisions. In an emergency, contact
        your local emergency number.{" "}
        {loading ? "" : isAuthed ? `Signed in as ${user?.email}.` : "You are browsing in demo mode."}
      </p>
    </div>
  );
}
