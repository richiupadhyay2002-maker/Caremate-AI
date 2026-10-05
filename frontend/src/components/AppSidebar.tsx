"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useApp } from "@/lib/auth-context";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * AppSidebar — fixed left sidebar (∼230 px, deep teal #0F2422).
 * Portal switch (Patient/Doctor) is a pure UI toggle — no authentication
 * in this prototype stage. Includes language toggle (EN/हिंदी).
 */
export default function AppSidebar() {
  const { user, portal, setPortal, lang, setLang, isAuthed, canAccessDoctor, logout } = useApp();
  const pathname = usePathname();
  const router = useRouter();
  const t = useT();

  const isPatient = portal === "patient";

  // ── Portal switch (Patient / Doctor pill) ────────────────────────
  const portals = [
    { id: "patient" as const, label: "Patient", active: isPatient },
    { id: "doctor" as const, label: "Doctor", active: !isPatient },
  ];

  // ── Vertical nav items (role-dependent) ─────────────────────────
  type NavItem = {
    href: string;
    label: string;
    exact?: boolean;
  };

  const patientNav: NavItem[] = [
    { href: "/dashboard", label: t("navTimeline"), exact: true },
    { href: "/ask", label: t("navAsk") },
    { href: "/reports", label: t("navReports") },
    { href: "/nutrition", label: t("navNutrition") },
    { href: "/journal", label: t("navJournal") },
    { href: "/appointments", label: t("navPrep") },
  ];

  const commonNav: NavItem[] = [
    { href: "/demo", label: "Sample Files" },
    { href: "/upload", label: isAuthed ? "Upload Report" : "Upload Report (Sign in)" },
  ];

  const accountNav: NavItem[] = isAuthed
    ? [{ href: "/account", label: "My Dashboard" }]
    : [];

  const doctorNav: NavItem[] = [
    { href: "/doctors/me", label: t("navPatients"), exact: true },
    { href: "/doctors/ask", label: t("navDoctorAsk") },
    { href: "/doctors/risk", label: t("navRiskWatch") },
  ];

  const navItems = isPatient
    ? [...patientNav, ...commonNav, ...accountNav]
    : [...doctorNav, ...commonNav, ...accountNav];

  const switchPortal = (p: "patient" | "doctor") => {
    if (p === portal) return;
    // Gate: the Doctor portal requires a doctor/admin account.
    if (p === "doctor" && !canAccessDoctor) {
      // Hard navigation so the sign-in wall shows even if we are already
      // on the login page.
      window.location.assign("/login?portal=doctor");
      return;
    }
    setPortal(p);
    // Hard navigation keeps stale client state out of the way.
    window.location.assign(p === "patient" ? "/dashboard" : "/doctors/me");
  };

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-40 flex flex-col",
        "w-[230px] bg-sidebar-bg text-sidebar-text",
      )}
    >
      {/* ── Wordmark ── */}
      <div className="px-6 py-6">
        <Link href={isPatient ? "/dashboard" : "/doctors/me"}>
          <span className="text-2xl font-heading font-bold text-white cursor-pointer">
            {t("appName")}
          </span>
        </Link>
      </div>

      {/* ── Portal switcher (always visible: Patient / Doctor toggle) ── */}
      <div className="px-6 mb-4">
        <div className="inline-flex items-center gap-0.5 p-0.5 rounded-full bg-sidebar-bg/50 text-xs font-medium">
          {portals.map((p) => (
            <button
              key={p.id}
              type="button"
              data-testid={`portal-${p.id}`}
              aria-current={p.active ? "page" : undefined}
              onClick={() => switchPortal(p.id)}
              className={cn(
                "px-3 py-1.5 rounded-full transition-all text-sm font-medium",
                "whitespace-nowrap cursor-pointer",
                p.active
                  ? "bg-brand-teal text-white"
                  : "text-sidebar-text-inactive hover:text-sidebar-text",
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Language toggle (multilingual scaffold: EN / हिंदी) ── */}
      <div className="px-6 mb-6">
        <div className="inline-flex items-center gap-0.5 p-0.5 rounded-full bg-sidebar-bg/50 text-xs font-medium">
          {(["en", "hi"] as const).map((l) => (
            <button
              key={l}
              type="button"
              onClick={() => setLang(l)}
              className={cn(
                "px-2.5 py-1 rounded-full transition-all text-xs font-medium cursor-pointer",
                lang === l
                  ? "bg-sidebar-pill-hover text-sidebar-text"
                  : "text-sidebar-text-inactive hover:text-sidebar-text",
              )}
            >
              {l === "en" ? "EN" : "हिंदी"}
            </button>
          ))}
        </div>
      </div>

      {/* ── Vertical nav ── */}
      <nav className="flex-1 px-3">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive = item.exact
              ? pathname === item.href
              : pathname.startsWith(item.href);
            return (
              <li key={item.href}>
                <Link href={item.href}>
                  <span
                    className={cn(
                      "flex items-center px-3 py-2 rounded-lg text-sm font-medium cursor-pointer transition-colors",
                      isActive
                        ? "bg-sidebar-pill-hover text-sidebar-text"
                        : "text-sidebar-text-inactive hover:text-sidebar-text hover:bg-sidebar-pill-hover",
                    )}
                  >
                    {item.label}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* ── Identity tag (pinned to bottom) ── */}
      <div className="px-6 py-4 border-t border-sidebar-bg/30">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="text-xs font-medium text-sidebar-text-inactive uppercase tracking-wider">
              {isAuthed
                ? user?.role === "doctor" ? t("doctorPortal") : t("patientPortal")
                : isPatient ? t("patientPortal") + " (demo)" : t("doctorPortal") + " (demo)"}
            </p>
            <p className="text-sm font-bold text-sidebar-text mt-0.5 truncate">
              {user?.full_name}
            </p>
          </div>
          {!isAuthed && (
            <span className="text-[10px] px-1.5 py-0.5 bg-sidebar-text-inactive/20 text-sidebar-text-inactive rounded uppercase flex-shrink-0">
              {t("demoLabel")}
            </span>
          )}
        </div>

        {isAuthed ? (
          <button
            type="button"
            onClick={() => {
              logout();
              window.location.href = "/";
            }}
            className="mt-3 text-xs text-sidebar-text-inactive hover:text-sidebar-text w-full text-left cursor-pointer"
          >
            Sign out
          </button>
        ) : (
          <div className="mt-3 flex gap-2">
            <Link href="/login">
              <span className="text-xs text-sidebar-text hover:text-white cursor-pointer font-medium">
                Sign in
              </span>
            </Link>
            <Link href="/signup">
              <span className="text-xs text-sidebar-text-inactive hover:text-sidebar-text cursor-pointer">
                Sign up
              </span>
            </Link>
          </div>
        )}
      </div>
    </aside>
  );
}
