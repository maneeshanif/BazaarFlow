"use client";

import { useCallback, useRef, useState } from "react";
import { ApiError, toApiError, type FieldErrors } from "@/lib/api/client";

export type Submission<A extends unknown[], R> = {
  /** Runs the action once at a time: a second click while one is in flight is ignored (no duplicate record). */
  run: (...args: A) => Promise<R | undefined>;
  pending: boolean;
  error: ApiError | null;
  /** Per-field messages from the server (RFC 7807 `errors`), keyed like the form fields. */
  fieldErrors: FieldErrors;
  clear: () => void;
};

/** The form submit pattern (task 52): one request in flight, server errors surfaced inline, never swallowed. */
export function useSubmit<A extends unknown[], R>(action: (...args: A) => Promise<R>): Submission<A, R> {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const inflight = useRef(false);
  const latest = useRef(action);
  latest.current = action;

  const run = useCallback(async (...args: A): Promise<R | undefined> => {
    if (inflight.current) return undefined;
    inflight.current = true;
    setPending(true);
    setError(null);
    try {
      return await latest.current(...args);
    } catch (e) {
      setError(toApiError(e));
      return undefined;
    } finally {
      inflight.current = false;
      setPending(false);
    }
  }, []);

  const clear = useCallback(() => setError(null), []);
  return { run, pending, error, fieldErrors: error?.fieldErrors ?? {}, clear };
}
