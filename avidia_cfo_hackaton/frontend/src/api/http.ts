import { locale, t } from "@/i18n";

/**
 * Minimal fetch wrapper. All requests go to same-origin `/api` by default
 * (Vite proxy in dev, FastAPI in production). Override with VITE_API_BASE if ever needed.
 *
 * Every request carries `lang=en|de` (the language chosen in the UI). The backend writes its texts in that
 * language (dashboard, sync, decisions, policy, hints, suggestions); routes without texts simply ignore it.
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

/** The text to show for a failed request or any other thrown value (ApiError messages are already translated). */
export const errorMessage = (e: unknown) => (e instanceof Error && e.message ? e.message : t("Something went wrong."));

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

const NOT_JSON = Symbol("not json");

export async function request<T>(method: Method, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  let res: Response;
  let text: string;
  try {
    // FormData (file upload): the browser sets the multipart Content-Type with its boundary itself.
    const isForm = body instanceof FormData;
    res = await fetch(apiUrl(path), {
      method,
      headers: body !== undefined && !isForm ? { "Content-Type": "application/json" } : undefined,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
      signal,
    });
    text = await res.text(); // inside the try: the connection can also drop while the body arrives
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(t("Cannot reach the server. Check your connection."), 0);
  }

  const data = text ? safeJson(text) : undefined;
  if (!res.ok) {
    // FastAPI: `detail` is a string for our own errors, but a list of objects for 422 validation errors –
    // never show "[object Object]" to the owner.
    const detail = data === NOT_JSON ? undefined : (data as { detail?: unknown } | undefined)?.detail;
    const msg = typeof detail === "string" && detail ? detail : t("Request failed ({status})", { status: res.status });
    throw new ApiError(msg, res.status, data === NOT_JSON ? text : data);
  }
  // A 2xx that is not JSON (e.g. an HTML page from a proxy or an older backend) must not be used as data.
  if (data === NOT_JSON) throw new ApiError(t("Request failed ({status})", { status: res.status }), res.status, text);
  return data as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return NOT_JSON;
  }
}

export const http = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>("GET", path, undefined, signal),
  post: <T>(path: string, body?: unknown, signal?: AbortSignal) => request<T>("POST", path, body, signal),
  del: <T>(path: string, signal?: AbortSignal) => request<T>("DELETE", path, undefined, signal),
};
