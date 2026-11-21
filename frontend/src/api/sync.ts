import { t } from "@/i18n";
import type { Dashboard, SyncErrorEvent, SyncResultEvent, TraceEvent } from "@/types/api";
import { apiUrl } from "./http";

export interface SyncHandlers {
  onTrace: (event: TraceEvent) => void;
  onResult: (dashboard: Dashboard) => void;
  onError: (message: string) => void;
}

/**
 * GET /api/sync – Server-Sent Events, ~20–40 s.
 * Emits `trace` (one per agent step), then `result` (new dashboard) or `error`.
 * Returns a function that closes the stream.
 */
export function startSync({ onTrace, onResult, onError }: SyncHandlers): () => void {
  const es = new EventSource(apiUrl("/sync"));
  let finished = false;
  const close = () => {
    finished = true;
    es.close();
  };
  const parse = <T>(e: Event): T | null => {
    try {
      return JSON.parse((e as MessageEvent<string>).data) as T;
    } catch {
      return null;
    }
  };

  es.addEventListener("trace", (e) => {
    const step = parse<TraceEvent>(e);
    if (step) onTrace(step); // a broken frame (e.g. cut by a proxy) only loses that one step
  });

  es.addEventListener("result", (e) => {
    const payload = parse<SyncResultEvent>(e);
    close();
    if (payload?.dashboard) onResult(payload.dashboard);
    else onError(t("The check finished, but its result could not be read. Please reload the page."));
  });

  // Fires both for a server-sent `event: error` (has data) and for a dropped connection (no data).
  es.addEventListener("error", (e) => {
    if (finished) return;
    const data = (e as MessageEvent<string>).data;
    let message = t("Connection to the assistant was lost.");
    if (data) {
      try {
        message = (JSON.parse(data) as SyncErrorEvent).message;
      } catch {
        /* keep default */
      }
    }
    close();
    onError(message);
  });

  return close;
}
