import type { DecisionResponse, RewriteRequest, RewriteResult } from "@/types/api";
import { http } from "./http";

/**
 * Owner decisions. UI rule #1: call these ONLY from an explicit user click – never automatically.
 */

/** POST /api/actions/{id}/approve – `editedBody` replaces the email draft (send_email only). */
export const approveAction = (id: string, editedBody?: string | null) =>
  http.post<DecisionResponse>(`/actions/${encodeURIComponent(id)}/approve`, { edited_body: editedBody ?? null });

/** POST /api/actions/{id}/reject – no body. */
export const rejectAction = (id: string) => http.post<DecisionResponse>(`/actions/${encodeURIComponent(id)}/reject`);

/**
 * POST /api/actions/{id}/rewrite – PROPOSED (CONTRACT_PROPOSALS.md §4). Rewrites a send_email draft along the
 * owner's wish. Does NOT change or send anything on the backend: the new text only lands in the editor, and the
 * owner still has to click "Approve and send".
 */
export const rewriteDraft = (id: string, req: RewriteRequest) =>
  http.post<RewriteResult>(`/actions/${encodeURIComponent(id)}/rewrite`, req);
