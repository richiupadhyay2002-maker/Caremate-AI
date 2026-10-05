"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useApp } from "@/lib/auth-context";
import { Card, Button, PageHeader } from "@/components/ui";

function SignedInHint() {
  const { isAuthed, user, logout } = useApp();
  if (!isAuthed || !user) return null;

  // A doctor signing in for the Doctor portal doesn't need to log in again —
  // offer a direct entry button instead of just "sign out first".
  if (user.role === "doctor") {
    return (
      <div className="mt-3 flex items-center justify-between text-xs bg-status-safe-bg border border-status-safe/30 rounded-[8px] px-3 py-2">
        <span className="text-ink-secondary">
          Signed in as <strong>{user.email}</strong> (doctor)
        </span>
        <button
          type="button"
          onClick={() => window.location.assign("/doctors/me")}
          className="text-brand-teal font-medium cursor-pointer"
        >
          Open Doctor portal →
        </button>
      </div>
    );
  }

  return (
    <div className="mt-3 flex items-center justify-between text-xs bg-clinical-border/30 border border-clinical-border rounded-[8px] px-3 py-2">
      <span className="text-ink-secondary">
        Currently signed in as <strong>{user.email}</strong> ({user.role})
      </span>
      <button
        type="button"
        onClick={logout}
        className="text-brand-teal font-medium cursor-pointer"
      >
        Sign out first
      </button>
    </div>
  );
}

function LoginInner() {
  const { loginWithPassword } = useApp();
  const params = useSearchParams();
  const wantsDoctor = params.get("portal") === "doctor";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState<string | null>(
    wantsDoctor
      ? "Sign in with a doctor account to open the Doctor portal."
      : null
  );
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
      const role = await loginWithPassword(email, password, remember);
      // Route by role. A patient account cannot open the Doctor portal —
      // keep it on the login page with a clear note instead.
      if (role === "doctor") {
        // Hard navigation: guarantees a clean doctor session regardless of
        // any stale client state.
        window.location.assign("/doctors/me");
      } else if (wantsDoctor) {
        setError(
          "Signed in, but this account has patient access only. To open the Doctor portal, sign out below and sign in with a doctor account (doctor@caremate.ai / doctor123)."
        );
        setNotice(null);
        setLoading(false);
        return;
      } else {
        window.location.assign("/account");
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Login failed. Please try again.";
      setError(
        /401|incorrect/i.test(msg)
          ? "Incorrect email or password."
          : msg.replace(/^API error \d+:\s*/, ""),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-8">
      <PageHeader eyebrow="CareMate AI" title="Sign in" />
      <p className="text-sm text-ink-secondary mt-2">
        Access your uploaded reports, AI analyses, and your care portal.
      </p>
      <SignedInHint />

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
          </div>

          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm text-ink-secondary cursor-pointer">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                className="accent-[var(--color-brand-teal)]"
              />
              Remember me
            </label>
            <Link
              href="/forgot-password"
              className="text-sm text-brand-teal font-medium"
            >
              Forgot password?
            </Link>
          </div>

          {notice && !error && (
            <p className="text-xs text-status-review bg-status-review-bg px-3 py-2 rounded-[8px]">
              {notice}
            </p>
          )}

          {error && <p className="text-sm text-status-urgent">{error}</p>}

          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={loading}
            className="w-full"
          >
            {loading ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </Card>

      <Card className="mt-4">
        <p className="text-sm text-ink-secondary">
          New to CareMate?{" "}
          <Link href="/signup" className="text-brand-teal font-medium">
            Create an account
          </Link>
        </p>
        <p className="text-sm text-ink-secondary mt-2">
          Just exploring?{" "}
          <Link href="/demo" className="text-brand-teal font-medium">
            Try the demo
          </Link>{" "}
          — no account needed. Demo uses sample data only.
        </p>
        <p className="text-xs text-ink-secondary mt-3">
          Demo accounts: patient@caremate.ai / patient123 ·
          doctor@caremate.ai / doctor123
        </p>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<p className="text-center py-12 text-ink-secondary">Loading…</p>}>
      <LoginInner />
    </Suspense>
  );
}
