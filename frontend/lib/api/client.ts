import axios from "axios";

/**
 * The one place the browser talks to the API (code-standards: API types come from the generated client, errors are
 * RFC 7807 problems). The token is attached by the interceptors that AuthProvider installs on the default axios
 * instance, and only for requests to this origin.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 15_000;

export type FieldErrors = Record<string, string>;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | undefined;
  readonly fieldErrors: FieldErrors;
  readonly requestId: string | null;

  constructor(status: number, message: string, code?: string, fieldErrors: FieldErrors = {}, requestId: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fieldErrors = fieldErrors;
    this.requestId = requestId;
  }
}

type Problem = {
  detail?: unknown;
  code?: string;
  errors?: { field: string; message: string }[];
  request_id?: string | null;
};

/** Turn anything thrown by a request into an ApiError with a message a person can act on. */
export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return new ApiError(0, "Could not reach the server. Check your connection and try again.", "network");
    }
    const problem = (error.response.data ?? {}) as Problem;
    const detail = typeof problem.detail === "string" ? problem.detail : "The request failed. Try again.";
    const fieldErrors: FieldErrors = {};
    for (const item of problem.errors ?? []) fieldErrors[item.field] = item.message;
    return new ApiError(error.response.status, detail, problem.code, fieldErrors, problem.request_id ?? null);
  }
  return new ApiError(0, "Something unexpected happened. Try again.", "unknown");
}

const url = (path: string): string => `${API_BASE}/api/v1${path}`;

type Params = Record<string, string | number | boolean | undefined | null>;

function clean(params?: Params): Record<string, string | number | boolean> | undefined {
  if (!params) return undefined;
  const out: Record<string, string | number | boolean> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") out[key] = value;
  }
  return out;
}

export async function apiGet<T>(path: string, params?: Params): Promise<T> {
  try {
    return (await axios.get<T>(url(path), { params: clean(params), timeout: REQUEST_TIMEOUT_MS })).data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function apiPost<T>(path: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
  try {
    return (await axios.post<T>(url(path), body, { headers, timeout: REQUEST_TIMEOUT_MS })).data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  try {
    return (await axios.patch<T>(url(path), body, { timeout: REQUEST_TIMEOUT_MS })).data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  try {
    return (await axios.put<T>(url(path), body, { timeout: REQUEST_TIMEOUT_MS })).data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function apiDelete(path: string): Promise<void> {
  try {
    await axios.delete(url(path), { timeout: REQUEST_TIMEOUT_MS });
  } catch (error) {
    throw toApiError(error);
  }
}
