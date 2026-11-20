import { locale, t } from "@/i18n";

/**
 * Minimal fetch wrapper. All requests go to same-origin `/api` by default
 * (Vite proxy in dev, FastAPI in production). Override with VITE_API_BASE if ever needed.
 *
 * Every request carries `lang=en|de` (the language chosen in the UI). PROPOSED contract extension
 * (frontend/CONTRACT_PROPOSALS.md): today only /api/ask* on backend-dev reads it; FastAPI ignores unknown
 * query parameters, so sending it everywhere is harmless and starts working as soon as the backend supports it.
 */
export const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const apiUrl = (path: string) => `${API_BASE}/api${path}${path.includes("?") ? "&" : "?"}lang=${locale.value}`;

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export async function request<T>(method: Method, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(apiUrl(path), {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(t("Cannot reach the server. Check your connection."), 0);
  }

  const text = await res.text();
  const data = text ? safeJson(text) : undefined;
  if (!res.ok) {
    const detail = (data as { detail?: string } | undefined)?.detail;
    throw new ApiError(detail ?? t("Request failed ({status})", { status: res.status }), res.status, data);
  }
  return data as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export const http = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>("GET", path, undefined, signal),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
};
