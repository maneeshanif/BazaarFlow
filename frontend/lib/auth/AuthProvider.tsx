"use client";

import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { msUntilRefresh } from "@/lib/auth/jwt";
import type { Role } from "@/lib/navigation";

type Status = "loading" | "authenticated" | "anonymous";

export type LoginResult =
  | { ok: true }
  | { ok: false; error: string; tenants?: { tenant_id: string; tenant_name: string }[] };

type AuthValue = {
  status: Status;
  role: Role | null;
  tenantId: string | null;
  error: string | null;
  login: (email: string, password: string, tenantId?: string) => Promise<LoginResult>;
  logout: () => Promise<void>;
};

const ANONYMOUS: AuthValue = {
  status: "anonymous",
  role: null,
  tenantId: null,
  error: null,
  login: async () => ({ ok: false, error: "Sign-in is not available here." }),
  logout: async () => undefined,
};

const AuthContext = createContext<AuthValue>(ANONYMOUS);
export const useAuth = () => useContext(AuthContext);

type Session = { access_token: string; tenant_id: string; role: Role };
type Retriable = InternalAxiosRequestConfig & { _retried?: boolean };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const isApiCall = (url?: string) => !!url && (url.startsWith(API_BASE) || url.startsWith("/api/")) && !url.startsWith("/api/auth/");

/**
 * Holds the signed-in session in memory (never in localStorage) and keeps it alive:
 * the access token is refreshed shortly before it expires and once more if the API answers 401.
 * It also attaches the token to calls made through the default axios instance, so existing pages work unchanged.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);
  const token = useRef<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inflight = useRef<Promise<string | null> | null>(null);

  const clear = useCallback(() => {
    token.current = null;
    if (timer.current) clearTimeout(timer.current);
    setSession(null);
    setStatus("anonymous");
  }, []);

  const adopt = useCallback((s: Session, refresh: () => Promise<string | null>) => {
    token.current = s.access_token;
    setSession(s);
    setStatus("authenticated");
    setError(null);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => void refresh(), msUntilRefresh(s.access_token));
  }, []);

  // single-flight: concurrent 401s and the expiry timer share one refresh call
  const refresh = useCallback((): Promise<string | null> => {
    if (inflight.current) return inflight.current;
    const run = (async () => {
      try {
        const res = await fetch("/api/auth/refresh", { method: "POST", credentials: "same-origin" });
        if (!res.ok) {
          clear();
          return null;
        }
        const s = (await res.json()) as Session;
        adopt(s, refresh);
        return s.access_token;
      } catch {
        clear();
        return null;
      } finally {
        inflight.current = null;
      }
    })();
    inflight.current = run;
    return run;
  }, [adopt, clear]);

  useEffect(() => {
    void refresh(); // restore the session from the httpOnly cookie
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [refresh]);

  useEffect(() => {
    const req = axios.interceptors.request.use((config) => {
      if (token.current && isApiCall(config.url)) config.headers.set("Authorization", `Bearer ${token.current}`);
      return config;
    });
    const res = axios.interceptors.response.use(undefined, async (err: AxiosError) => {
      const config = err.config as Retriable | undefined;
      if (err.response?.status === 401 && config && !config._retried && isApiCall(config.url)) {
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
        });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          const detail = body?.detail;
          if (res.status === 409 && detail?.code === "tenant_required") {
            return { ok: false, error: "Choose a shop to continue.", tenants: detail.tenants };
          }
          const message = typeof detail === "string" ? detail : "Could not sign in. Check your details and try again.";
          setError(message);
          return { ok: false, error: message };
        }
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

  const logout = useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" }).catch(() => undefined);
    clear();
  }, [clear]);

  const value = useMemo<AuthValue>(
    () => ({ status, role: session?.role ?? null, tenantId: session?.tenant_id ?? null, error, login, logout }),
    [status, session, error, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
