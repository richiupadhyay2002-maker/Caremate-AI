"use client";

import { useState } from "react";
import Link from "next/link";
import { useApp } from "@/lib/auth-context";
import { forgotPassword } from "@/lib/api";
import { Card, Button } from "@/components/ui";

/**
 * Forgot password — starts the recovery flow. In this prototype no SMTP
 * server is configured, so the backend returns the reset token and the UI
 * presents it as a reset link (clearly labeled as prototype behaviour).
 */
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const emailValid = /.+@.+\..+/.test(email);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!emailValid) {
      setError("Please enter a valid email address.");
      return;
    }
    setLoading(true);
    try {
      const resp = await forgotPassword(email);
      setSent(true);
      setResetToken(resp.reset_token);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Request failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-8">
      <h1 className="text-2xl font-heading text-ink-primary">Forgot password</h1>
      <p className="text-sm text-ink-secondary mt-2">
        Enter the email you registered with and we&apos;ll start the password
        recovery flow.
      </p>

      {sent ? (
        <Card className="mt-6">
          <p className="text-sm text-ink-primary">
            If that email is registered, a reset link has been generated.
          </p>
          {resetToken ? (
            <div className="mt-4">
              <p className="text-xs text-ink-secondary">
                Prototype note: no email server is configured in this demo, so
                the reset link is shown here instead of being emailed.
              </p>
              <Link
                href={`/reset-password?token=${encodeURIComponent(resetToken)}`}
                className="text-sm text-brand-teal font-medium mt-2 inline-block"
              >
                Open reset link →
              </Link>
            </div>
          ) : (
            <p className="text-xs text-ink-secondary mt-3">
              This email is not registered here.
            </p>
          )}
          <Link href="/login" className="text-sm text-brand-teal font-medium mt-4 inline-block">
            ← Back to sign in
          </Link>
        </Card>
      ) : (
        <Card className="mt-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 border border-clinical-border rounded-[10px] bg-clinical-surface text-ink-primary focus:ring-2 focus:ring-brand-teal/30 outline-none font-body"
                required
                disabled={loading}
              />
              {email && !emailValid && (
                <p className="text-xs text-status-urgent mt-1">
                  Please enter a valid email address.
                </p>
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
              {loading ? "Requesting…" : "Send reset request"}
            </Button>
          </form>
        </Card>
      )}
    </div>
  );
}
