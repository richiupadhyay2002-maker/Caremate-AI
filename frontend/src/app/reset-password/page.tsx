"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { resetPassword } from "@/lib/api";
import { Card, Button } from "@/components/ui";

function ResetPasswordInner() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const pwStrong = password.length >= 8 && /\d/.test(password) && /[a-zA-Z]/.test(password);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!token) {
      setError("Missing reset token. Open the reset link from your email first.");
      return;
    }
    if (!pwStrong) {
      setError("Password must be at least 8 characters and include a letter and a number.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await resetPassword(token, password);
      setDone(true);
      setTimeout(() => router.push("/login"), 2500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Reset failed.";
      setError(msg.replace(/^API error \d+:\s*/, ""));
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <Card className="mt-6">
        <p className="text-sm text-status-urgent">
          This page needs a valid reset link (with a token). Start again from
          the forgot-password page.
        </p>
        <Link href="/forgot-password" className="text-sm text-brand-teal font-medium mt-3 inline-block">
          Forgot password →
        </Link>
      </Card>
    );
  }

  if (done) {
    return (
      <Card className="mt-6">
        <p className="text-sm text-status-safe font-medium">
          Password updated successfully.
        </p>
        <p className="text-sm text-ink-secondary mt-1">
          You can now sign in with your new password.
        </p>
        <Link href="/login" className="text-sm text-brand-teal font-medium mt-3 inline-block">
          Go to sign in →
        </Link>
      </Card>
    );
  }

  return (
    <Card className="mt-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
            New password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-2.5 border border-clinical-border rounded-[10px] bg-clinical-surface text-ink-primary focus:ring-2 focus:ring-brand-teal/30 outline-none font-body"
            required
            disabled={loading}
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
            Confirm new password
          </label>
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="w-full px-4 py-2.5 border border-clinical-border rounded-[10px] bg-clinical-surface text-ink-primary focus:ring-2 focus:ring-brand-teal/30 outline-none font-body"
            required
            disabled={loading}
          />
          {confirm && password !== confirm && (
            <p className="text-xs text-status-urgent mt-1">Passwords do not match.</p>
          )}
        </div>
        {error && <p className="text-sm text-status-urgent">{error}</p>}
        <Button
          type="submit"
          variant="primary"
          size="md"
          disabled={loading}
          className="w-full"
        >
          {loading ? "Updating…" : "Reset password"}
        </Button>
      </form>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="max-w-md mx-auto py-8">
      <h1 className="text-2xl font-heading text-ink-primary">Reset password</h1>
      <p className="text-sm text-ink-secondary mt-2">
        Choose a new password for your CareMate account.
      </p>
      <Suspense fallback={<p className="text-sm text-ink-secondary mt-6">Loading…</p>}>
        <ResetPasswordInner />
      </Suspense>
    </div>
  );
}
