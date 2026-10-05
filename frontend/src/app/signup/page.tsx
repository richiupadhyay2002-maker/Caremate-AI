"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useApp } from "@/lib/auth-context";
import { Card, Button } from "@/components/ui";

/**
 * Real sign-up page (creates a patient account on the FastAPI backend).
 * Validation: invalid email, weak password, password mismatch, existing email.
 */
export default function SignUpPage() {
  const { signUp } = useApp();
  const router = useRouter();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const emailValid = /.+@.+\..+/.test(email);
  const pwChecks = {
    length: password.length >= 8,
    number: /\d/.test(password),
    letter: /[a-zA-Z]/.test(password),
  };
  const pwStrong = pwChecks.length && pwChecks.number && pwChecks.letter;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!emailValid) {
      setError("Please enter a valid email address.");
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
    if (!consent) {
      setError("Please review and accept the privacy notice to continue.");
      return;
    }
    setLoading(true);
    try {
      await signUp(name.trim() || email.split("@")[0], email, password);
      router.push("/account");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Sign up failed.";
      setError(
        /409|already/i.test(msg)
          ? "This email is already registered. Try signing in instead."
          : msg.replace(/^API error \d+:\s*/, ""),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-8">
      <h1 className="text-2xl font-heading text-ink-primary">Create your account</h1>
      <p className="text-sm text-ink-secondary mt-2">
        Upload your own reports, run AI analysis, and keep your results in one
        private place.
      </p>

      <Card className="mt-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2.5 border border-clinical-border rounded-[10px] bg-clinical-surface text-ink-primary focus:ring-2 focus:ring-brand-teal/30 outline-none font-body"
              required
              disabled={loading}
            />
          </div>

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

          <div>
            <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 border border-clinical-border rounded-[10px] bg-clinical-surface text-ink-primary focus:ring-2 focus:ring-brand-teal/30 outline-none font-body"
              required
              disabled={loading}
            />
            {password && (
              <ul className="text-xs mt-1 space-y-0.5">
                <li className={pwChecks.length ? "text-status-safe" : "text-ink-secondary"}>
                  At least 8 characters {pwChecks.length ? "✓" : ""}
                </li>
                <li className={pwChecks.number ? "text-status-safe" : "text-ink-secondary"}>
                  Contains a number {pwChecks.number ? "✓" : ""}
                </li>
                <li className={pwChecks.letter ? "text-status-safe" : "text-ink-secondary"}>
                  Contains a letter {pwChecks.letter ? "✓" : ""}
                </li>
              </ul>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-ink-secondary uppercase tracking-wider mb-1">
              Confirm password
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
              <p className="text-xs text-status-urgent mt-1">
                Passwords do not match.
              </p>
            )}
          </div>

          <label className="flex items-start gap-2 text-xs text-ink-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-0.5 accent-[var(--color-brand-teal)]"
            />
            <span>
              I understand CareMate AI provides information, not medical advice,
              and never diagnoses or selects treatments. Uploaded documents are
              stored privately under my account and are not shown to other
              users.
            </span>
          </label>

          {error && <p className="text-sm text-status-urgent">{error}</p>}

          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={loading}
            className="w-full"
          >
            {loading ? "Creating account…" : "Sign up"}
          </Button>
        </form>
      </Card>

      <Card className="mt-4">
        <p className="text-sm text-ink-secondary">
          Already have an account?{" "}
          <Link href="/login" className="text-brand-teal font-medium">
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
