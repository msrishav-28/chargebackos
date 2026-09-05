import { z } from "zod";
import {
  caseSchema, disputeListSchema, evaluationRunSchema, loginSchema,
  overviewSchema, policiesSchema, staffSchema, successSchema, evaluationStatusSchema,
} from "./ops-schemas";
export type { StaffUser, OverviewPayload } from "./ops-schemas";

const TOKEN_KEY = "cbos_token";
export const SESSION_EXPIRED_EVENT = "cbos-session-expired";

export class OpsApiError extends Error {
  status: number;
  waking: boolean;
  constructor(message: string, status: number, waking = false) {
    super(message);
    this.status = status;
    this.waking = waking;
  }
}

function baseUrl() {
  const u = import.meta.env.VITE_API_URL as string | undefined;
  const base = u?.trim() || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");
  if (!base) throw new OpsApiError("The operations server address has not been configured.", 503);
  return base.replace(/\/+$/, "");
}

export function getToken() {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.sessionStorage.setItem(TOKEN_KEY, token);
  else window.sessionStorage.removeItem(TOKEN_KEY);
}

function messageFromBody(status: number, body: string): string {
  try {
    const j = JSON.parse(body) as { detail?: unknown };
    if (typeof j.detail === "string") return j.detail;
    if (j.detail && typeof j.detail === "object") {
      const d = j.detail as { reason?: string; currentState?: string; requestedState?: string };
      if (d.reason === "invalid_transition") {
        return `Cannot move from ${d.currentState ?? "this state"} to ${d.requestedState ?? "the requested state"}.`;
      }
      if (typeof d.reason === "string") return d.reason;
    }
  } catch {
    /* raw body */
  }
  return `The operations server could not complete this request (${status}). Please retry.`;
}

export async function apiFetch<T>(path: string, schema: z.ZodType<T>, init: RequestInit = {}, timeoutMs = 45_000): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let res: Response;
  try {
    const timeout = AbortSignal.timeout(timeoutMs);
    const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
    res = await fetch(`${baseUrl()}${path}`, { ...init, headers, signal });
  } catch (error) {
    if (error instanceof OpsApiError) throw error;
    throw new OpsApiError(
      "Operations server is waking or unreachable. Open the API health URL, wait, then retry.",
      0,
      true,
    );
  }
  if (res.status === 401) {
    setToken(null);
    if (typeof window !== "undefined") window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    throw new OpsApiError("Not signed in.", 401);
  }
  if (!res.ok) {
    const body = await res.text();
    throw new OpsApiError(messageFromBody(res.status, body), res.status, res.status === 502 || res.status === 503);
  }
  let body: unknown;
  try {
    body = res.status === 204 ? undefined : await res.json();
  } catch {
    throw new OpsApiError("The operations server returned an unreadable response.", 502);
  }
  const result = schema.safeParse(body);
  if (!result.success) {
    throw new OpsApiError("The operations server returned incomplete or invalid records. Please report this error to the operator.", 502);
  }
  return result.data;
}

export function loginRequest(email: string, password: string) {
  return apiFetch("/api/v1/auth/login", loginSchema, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logoutRequest() {
  return apiFetch("/api/v1/auth/logout", successSchema, { method: "POST" });
}

export function meRequest() {
  return apiFetch("/api/v1/auth/me", staffSchema);
}

export function overviewRequest() {
  return apiFetch("/api/v1/overview", overviewSchema);
}

export function policiesRequest() {
  return apiFetch("/api/v1/policies", policiesSchema);
}

export function disputesRequest(params: Record<string, string | boolean | undefined>) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === "" || v === false) continue;
    q.set(k, String(v));
  }
  const s = q.toString();
  return apiFetch(`/api/v1/disputes${s ? `?${s}` : ""}`, disputeListSchema);
}

export function disputeRequest(id: string) {
  return apiFetch(`/api/v1/disputes/${encodeURIComponent(id)}`, caseSchema);
}

export function actionRequest(id: string, action: string) {
  return apiFetch(`/api/v1/disputes/${encodeURIComponent(id)}/action`, caseSchema, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}

export function rewriteDraftRequest(id: string) {
  return apiFetch(`/api/v1/disputes/${encodeURIComponent(id)}/rewrite-draft`, caseSchema, {
    method: "POST",
  });
}

export function resetDemoRequest() {
  return apiFetch("/api/v1/demo/reset", successSchema, {
    method: "POST", body: JSON.stringify({ confirmation: "REPLACE_SYNTHETIC_CASES" }),
  }, 300_000);
}

export function runEvaluationRequest(idempotencyKey: string) {
  return apiFetch("/api/v1/evaluations/run", evaluationRunSchema, {
    method: "POST", headers: { "Idempotency-Key": idempotencyKey },
  });
}

export function evaluationStatusRequest(id: string) {
  return apiFetch(`/api/v1/evaluations/${encodeURIComponent(id)}`, evaluationStatusSchema);
}

export function processCaseRequest(id: string, step: "triage" | "assemble-evidence" | "evaluate-policy") {
  return apiFetch(`/api/v1/disputes/${encodeURIComponent(id)}/${step}`, caseSchema, { method: "POST" });
}
