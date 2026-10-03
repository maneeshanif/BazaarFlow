"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, toApiError } from "@/lib/api/client";

export type ViewState = "loading" | "ready" | "empty" | "error" | "unauthorized";

export type Loaded<T> = {
  state: ViewState;
  data: T | null;
  error: ApiError | null;
  reload: () => void;
};

/**
 * Load data for a view and map the outcome to the four states every list must show (ui-rules.md):
 * loading, empty (no rows), error (with a retry via `reload`) and unauthorized (403).
 * `deps` decide when to load again; the latest loader is always used.
 */
export function useLoad<T>(loader: () => Promise<T>, deps: readonly unknown[], isEmpty?: (data: T) => boolean): Loaded<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [state, setState] = useState<ViewState>("loading");
  const [nonce, setNonce] = useState(0);
  const latest = useRef(loader);
  latest.current = loader;
  const emptyCheck = useRef(isEmpty);
  emptyCheck.current = isEmpty;

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    latest
      .current()
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setError(null);
        setState(emptyCheck.current?.(result) ? "empty" : "ready");
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        const err = toApiError(e);
        setError(err);
        setState(err.status === 403 ? "unauthorized" : "error");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { state, data, error, reload };
}
