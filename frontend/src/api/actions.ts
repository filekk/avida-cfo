import type { DecisionResponse } from "@/types/api";
import { http } from "./http";

/**
 * Owner decisions. UI rule #1: call these ONLY from an explicit user click – never automatically.
 */

/** POST /api/actions/{id}/approve – `editedBody` replaces the email draft (send_email only). */
export const approveAction = (id: string, editedBody?: string | null) =>
  http.post<DecisionResponse>(`/actions/${encodeURIComponent(id)}/approve`, { edited_body: editedBody ?? null });

/** POST /api/actions/{id}/reject – no body. */
export const rejectAction = (id: string) => http.post<DecisionResponse>(`/actions/${encodeURIComponent(id)}/reject`);
