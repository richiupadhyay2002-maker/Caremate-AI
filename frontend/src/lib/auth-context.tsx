"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
  useCallback,
  useRef,
} from "react";
import {
  login as apiLogin,
  getMe,
  getMyPatientRecord,
  register as apiRegister,
} from "@/lib/api";

/**
 * Hybrid auth context.
 *
 * - Real accounts: JWT token from the FastAPI backend (login / signup /
 *   logout / password reset). Uploaded files belong to the logged-in user.
 * - Guest ("Try Demo"): no account — full access to demo portals and the
 *   bundled sample files, clearly labeled as DEMO DATA.
 *
 * Existing pages keep using the same fields (user, token, loading, portal,
 * patientId, lang); new fields (isAuthed, loginWithPassword, signUp,
 * logout, refreshUser, updateUserName) power the real authentication flows.
 */

export type Portal = "patient" | "doctor";
export type Lang = "en" | "hi";

export interface DemoUser {
  id: number;
  email: string;
  full_name: string;
  role: "patient" | "doctor";
  patient_id?: number;
  doctor_id?: number;
}

interface AppContextType {
  user: DemoUser | null;
  token: string | null; // real JWT when logged in; "guest-demo" marker otherwise
  loading: boolean;
  isAuthed: boolean;
  /** True only when the signed-in account has doctor/admin access. */
  canAccessDoctor: boolean;
  portal: Portal;
  setPortal: (p: Portal) => void;
  patientId: string;
  lang: Lang;
  setLang: (l: Lang) => void;
  loginWithPassword: (email: string, password: string, remember?: boolean) => Promise<"patient" | "doctor">;
  signUp: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  updateUserName: (name: string) => void;
}

const GUEST_TOKEN = "guest-demo";

const AppContext = createContext<AppContextType | undefined>(undefined);

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<DemoUser | null>(null);
  const [portal, setPortalState] = useState<Portal>("patient");
  const [lang, setLangState] = useState<Lang>("en");
  const [loading, setLoading] = useState(true);
  const [patientIdOverride, setPatientIdOverride] = useState<string | null>(null);
  const booted = useRef(false);

  // Boot: restore session (real token) or fall back to guest demo mode.
  useEffect(() => {
    if (booted.current) return;
    booted.current = true;
    const p = (localStorage.getItem("caremate_portal") as Portal) || "patient";
    const l = (localStorage.getItem("caremate_lang") as Lang) || "en";
    setPortalState(p);
    setLangState(l);

    const stored = localStorage.getItem("caremate_token");
    if (stored && stored !== GUEST_TOKEN) {
      setToken(stored);
      getMe()
        .then(async (u) => {
          setUser({
            id: u.id,
            email: u.email,
            full_name: u.full_name,
            role: u.role === "doctor" || u.role === "admin" ? "doctor" : "patient",
          });
          if (u.role === "patient") {
            try {
              const rec = await getMyPatientRecord();
              setPatientIdOverride(rec.patient_id);
            } catch {
              setPatientIdOverride("P0001");
            }
          }
        })
        .catch(() => {
          // Stale/expired token — revert to guest mode.
          localStorage.removeItem("caremate_token");
          setToken(null);
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const setPortal = useCallback((p: Portal) => {
    setPortalState(p);
    localStorage.setItem("caremate_portal", p);
  }, []);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    localStorage.setItem("caremate_lang", l);
  }, []);

  const adoptToken = useCallback(async (newToken: string): Promise<"patient" | "doctor"> => {
    localStorage.setItem("caremate_token", newToken);
    setToken(newToken);
    const u = await getMe();
    const role: "patient" | "doctor" =
      u.role === "doctor" || u.role === "admin" ? "doctor" : "patient";
    setUser({
      id: u.id,
      email: u.email,
      full_name: u.full_name,
      role,
    });
    setPortalState(role);
    if (u.role === "patient") {
      try {
        const rec = await getMyPatientRecord();
        setPatientIdOverride(rec.patient_id);
      } catch {
        setPatientIdOverride("P0001");
      }
    }
    return role;
  }, []);

  const loginWithPassword = useCallback(
    async (email: string, password: string, _remember = true) => {
      const resp = await apiLogin(email, password);
      return adoptToken(resp.access_token);
    },
    [adoptToken]
  );

  const signUp = useCallback(
    async (name: string, email: string, password: string) => {
      await apiRegister(email, password, name);
      // Auto-login after successful signup.
      const resp = await apiLogin(email, password);
      await adoptToken(resp.access_token);
    },
    [adoptToken]
  );

  const logout = useCallback(() => {
    localStorage.removeItem("caremate_token");
    sessionStorage.removeItem("caremate_session_token");
    setToken(null);
    setUser(null);
    setPatientIdOverride(null);
    setPortalState("patient");
  }, []);

  const refreshUser = useCallback(async () => {
    if (!token || token === GUEST_TOKEN) return;
    try {
      const u = await getMe();
      setUser((prev) =>
        prev ? { ...prev, full_name: u.full_name, email: u.email } : prev
      );
    } catch {
      /* ignore */
    }
  }, [token]);

  const updateUserName = useCallback((name: string) => {
    setUser((prev) => (prev ? { ...prev, full_name: name } : prev));
  }, []);

  const isAuthed = !!token && token !== GUEST_TOKEN;
  const canAccessDoctor = isAuthed && user?.role === "doctor";

  const effectiveToken = isAuthed ? token : GUEST_TOKEN;
  const effectiveUser: DemoUser = isAuthed
    ? (user as DemoUser)
    : portal === "patient"
      ? {
          id: 1,
          email: "patient@caremate.ai",
          full_name: "Asha Verma",
          role: "patient",
          patient_id: 1,
        }
      : {
          id: 2,
          email: "doctor@caremate.ai",
          full_name: "Dr. K. Sharma",
          role: "doctor",
          doctor_id: 1,
        };

  const patientId =
    isAuthed && user?.role === "patient" ? (patientIdOverride ?? "P0001") : "P0001";

  return (
    <AppContext.Provider
      value={{
        user: effectiveUser,
        token: effectiveToken,
        loading,
        isAuthed,
        canAccessDoctor,
        portal,
        setPortal,
        patientId,
        lang,
        setLang,
        loginWithPassword,
        signUp,
        logout,
        refreshUser,
        updateUserName,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

/** Backwards-compatible alias used by existing pages. */
export const useAuth = useApp;
export const AuthProvider = AppProvider;
export function TokenToLoginResponse(token: string) {
  return { access_token: token, token_type: "bearer" };
}