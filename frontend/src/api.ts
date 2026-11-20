import type { Action, Dashboard, TraceEvent } from "./types";

export const eur = (n: number) =>
  new Intl.NumberFormat("en-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);

export const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

export async function getDashboard(): Promise<Dashboard> {
  const r = await fetch("/api/dashboard");
  return r.json();
}

export async function decide(id: string, approve: boolean, editedBody?: string) {
  const r = await fetch(`/api/actions/${id}/${approve ? "approve" : "reject"}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(approve ? { edited_body: editedBody ?? null } : {}),
  });
  return (await r.json()) as { action: Action; saved_liquidity: number };
}

/** Starts the agent pipeline and streams trace events (Server-Sent Events). */
export function sync(onTrace: (e: TraceEvent) => void, onDone: (d: Dashboard) => void, onError: (m: string) => void) {
  const es = new EventSource("/api/sync");
  es.addEventListener("trace", (e) => onTrace(JSON.parse((e as MessageEvent).data)));
  es.addEventListener("result", (e) => {
    onDone(JSON.parse((e as MessageEvent).data).dashboard);
    es.close();
  });
  es.addEventListener("error", (e) => {
    const data = (e as MessageEvent).data;
    onError(data ? JSON.parse(data).message : "Connection lost");
    es.close();
  });
  return () => es.close();
}
