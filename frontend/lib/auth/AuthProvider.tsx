"use client";

import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { decodeExp, msUntilRefresh } from "@/lib/auth/jwt";
import type { Role } from "@/lib/navigation";

type Status = "loading" | "authenticated" | "anonymous";

export type LoginResult =
  | { ok: true }
  | { ok: false; error: string; tenants?: { tenant_id: string; tenant_name: string }[] };

export type RegisterInput = {
  full_name: string;
  email: string;
  password: string;
  shop_name: string;
  phone: string;
  city?: string;
  accept_terms: boolean;
};

export type RegisterResult =
  | { ok: true }
  | { ok: false; error: string; fieldErrors: Record<string, string>; code?: string };

type AuthValue = {
  status: Status;
  role: Role | null;
  tenantId: string | null;
  error: string | null;
  login: (email: string, password: string, tenantId?: string) => Promise<LoginResult>;
  register: (input: RegisterInput) => Promise<RegisterResult>;
  logout: () => Promise<void>;
};

const ANONYMOUS: AuthValue = {
  status: "anonymous",
  role: null,
  tenantId: null,
  error: null,
  login: async () => ({ ok: false, error: "Sign-in is not available here." }),
  register: async () => ({ ok: false, error: "Sign-up is not available here.", fieldErrors: {} }),
  logout: async () => undefined,
};

const AuthContext = createContext<AuthValue>(ANONYMOUS);
export const useAuth = () => useContext(AuthContext);

type Session = { access_token: string; tenant_id: string; role: Role };
type Retriable = InternalAxiosRequestConfig & { _retried?: boolean };

/**
 * The provider is mounted per area (sign-in, dashboard, app), so the session is carried across client-side
 * navigation here. Without it, signing in and landing on the dashboard would refresh again immediately, and a
 * reload during that refresh could drop the rotated cookie and trip reuse detection.
 */
let carried: Session | null = null;
export function resetCarriedSession(): void {
  carried = null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 15_000;
const TRANSIENT_RETRY_MS = 30_000;

/** The token goes only to the backend: same origin as API_BASE (a prefix match would also match evil hosts). */
function isBackendCall(url: string | undefined): boolean {
  if (!url) return false;
  try {
    const target = new URL(url, API_BASE);
    return target.origin === new URL(API_BASE).origin && !target.pathname.startsWith("/api/auth/");
  } catch {
    return false;
  }
}

/**
 * Holds the signed-in session in memory (never in localStorage) and keeps it alive:
 * the access token is refreshed shortly before it expires and once more if the API answers 401.
 * It also attaches the token to calls made through the default axios instance, so existing pages work unchanged.
 * Mounted only under the signed-in areas and the sign-in page, so public pages never ask for a session.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);
  const token = useRef<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inflight = useRef<Promise<string | null> | null>(null);
  // bumped by logout/clear: a refresh that started earlier must not bring the session back
  const generation = useRef(0);

  const clear = useCallback(() => {
    generation.current += 1;
    token.current = null;
    carried = null;
    if (timer.current) clearTimeout(timer.current);
    setSession(null);
    setStatus("anonymous");
  }, []);

  const schedule = useCallback((ms: number, refresh: () => Promise<string | null>) => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => void refresh(), ms);
  }, []);

  const adopt = useCallback(
    (s: Session, refresh: () => Promise<string | null>) => {
      token.current = s.access_token;
      carried = s;
      setSession(s);
      setStatus("authenticated");
      setError(null);
      schedule(msUntilRefresh(s.access_token), refresh);
    },
    [schedule],
  );

  // single-flight: concurrent 401s and the expiry timer share one refresh call
  const refresh = useCallback((): Promise<string | null> => {
    if (inflight.current) return inflight.current;
    const started = generation.current;
    const run = (async () => {
      try {
        const res = await fetch("/api/auth/refresh", {
          method: "POST",
          credentials: "same-origin",
          signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        });
        if (started !== generation.current) return null; // signed out or replaced meanwhile: ignore the result
        if (res.status === 401) {
          clear(); // the session is really over
          return null;
        }
        if (!res.ok) throw new Error(`refresh failed: ${res.status}`);
        const s = (await res.json()) as Session;
        if (started !== generation.current) return null;
        adopt(s, refresh);
        return s.access_token;
      } catch {
        if (started !== generation.current) return null;
        // transient (API restarting, network blip, timeout): keep an existing session and try again soon;
        // with no session yet, there is nothing to keep
        if (token.current) schedule(TRANSIENT_RETRY_MS, refresh);
        else {
          setSession(null);
          setStatus("anonymous");
        }
        return null;
      } finally {
        inflight.current = null;
      }
    })();
    inflight.current = run;
    return run;
  }, [adopt, clear, schedule]);

  useEffect(() => {
    const exp = carried ? decodeExp(carried.access_token) : null;
    if (carried && exp !== null && exp * 1000 > Date.now()) {
      adopt(carried, refresh); // arrived by client-side navigation with a live session
    } else {
      void refresh(); // restore the session from the httpOnly cookie
    }
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [refresh, adopt]);

  useEffect(() => {
    const req = axios.interceptors.request.use((config) => {
      if (token.current && isBackendCall(config.url)) config.headers.set("Authorization", `Bearer ${token.current}`);
      return config;
    });
    const res = axios.interceptors.response.use(undefined, async (err: AxiosError) => {
      const config = err.config as Retriable | undefined;
      if (err.response?.status === 401 && config && !config._retried && isBackendCall(config.url)) {
        config._retried = true;
        const fresh = await refresh();
        if (fresh) {
          config.headers.set("Authorization", `Bearer ${fresh}`);
          return axios.request(config);
        }
      }
      return Promise.reject(err);
    });
    return () => {
      axios.interceptors.request.eject(req);
      axios.interceptors.response.eject(res);
    };
  }, [refresh]);

  const login = useCallback<AuthValue["login"]>(
    async (email, password, tenantId) => {
      setError(null);
      try {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "content-type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ email, password, ...(tenantId ? { tenant_id: tenantId } : {}) }),
          signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          const detail = body?.detail;
          if (res.status === 409 && body?.code === "tenant_required") {
            return { ok: false, error: "Choose a shop to continue.", tenants: body.tenants };
          }
          const message = typeof detail === "string" ? detail : "Could not sign in. Check your details and try again.";
          setError(message);
          return { ok: false, error: message };
        }
        generation.current += 1; // supersede any refresh that was already running
        adopt(body as Session, refresh);
        return { ok: true };
      } catch {
        const message = "Could not reach the server. Check your connection and try again.";
        setError(message);
        return { ok: false, error: message };
      }
    },
    [adopt, refresh],
  );

  const register = useCallback<AuthValue["register"]>(
    async (input) => {
      try {
        const res = await fetch("/api/auth/register", {
          method: "POST",
          headers: { "content-type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(input),
          signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          const fieldErrors: Record<string, string> = {};
          for (const item of (body?.errors ?? []) as { field: string; message: string }[]) fieldErrors[item.field] = item.message;
          const message = typeof body?.detail === "string" ? body.detail : "Could not create your account. Try again.";
          return { ok: false, error: message, fieldErrors, code: typeof body?.code === "string" ? body.code : undefined };
        }
        generation.current += 1; // supersede any refresh that was already running
        adopt(body as Session, refresh);
        return { ok: true };
      } catch {
        return {
          ok: false,
          error: "Could not reach the server. Check your connection and try again.",
          fieldErrors: {},
        };
      }
    },
    [adopt, refresh],
  );

  const logout = useCallback(async () => {
    clear(); // first: from this moment no in-flight refresh can restore the session
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "same-origin",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    }).catch(() => undefined);
  }, [clear]);

  const value = useMemo<AuthValue>(
    () => ({ status, role: session?.role ?? null, tenantId: session?.tenant_id ?? null, error, login, register, logout }),
    [status, session, error, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
