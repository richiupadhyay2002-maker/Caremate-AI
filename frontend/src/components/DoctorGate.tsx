"use client";

import Link from "next/link";
import { useApp } from "@/lib/auth-context";
import { Card, Button } from "@/components/ui";

/**
 * Access gate for the Doctor portal.
 *
 * Switching to the Doctor portal requires signing in with a doctor (or
 * admin) account. Guests and patient-account users see an access card with
 * sign-in options instead of the doctor pages.
 */
export default function DoctorGate({ children }: { children: React.ReactNode }) {
  const { isAuthed, canAccessDoctor, loading, user } = useApp();

  if (loading) {
    return <p className="text-center py-12 text-ink-secondary">Loading…</p>;
  }

  if (canAccessDoctor) return <>{children}</>;

  const isPatientAccount = isAuthed;

  return (
    <div className="max-w-lg mx-auto py-10 space-y-5">
      <Card className="border-status-review/40">
        <h1 className="text-2xl font-heading text-ink-primary">
          Doctor portal — sign-in required
        </h1>
        <p className="text-sm text-ink-secondary mt-2">
          {isPatientAccount
            ? `You are signed in as ${user?.email}, a patient account. The Doctor portal is restricted to doctor and admin accounts.`
            : "The Doctor portal is restricted. Please sign in with a doctor account to access patient lists, briefs and reviews."}
        </p>
        <p className="text-xs text-ink-secondary mt-2">
          Demo doctor account: doctor@caremate.ai / doctor123
        </p>
      </Card>

      <div className="flex flex-wrap gap-3">
        <Link href="/login?portal=doctor">
          <Button variant="primary" size="md">
            Sign in as doctor
          </Button>
        </Link>
        <Link href="/signup">
          <Button variant="secondary" size="md">
            Create account
          </Button>
        </Link>
        <Link href="/dashboard">
          <Button variant="ghost" size="md">
            Back to patient portal
          </Button>
        </Link>
      </div>
    </div>
  );
}
