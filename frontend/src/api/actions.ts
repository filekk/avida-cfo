import { locale } from "@/i18n";
import type {
  DecisionResponse,
  DraftReview,
  ProblemContext,
  RedraftHints,
  RedraftProposal,
  RedraftRequest,
} from "@/types/api";
import { http } from "./http";

/**
 * Owner decisions. UI rule #1: call these ONLY from an explicit user click – never automatically.
 */

/** POST /api/actions/{id}/approve – `editedBody` replaces the email draft (send_email only). */
export const approveAction = (id: string, editedBody?: string | null) =>
  http.post<DecisionResponse>(`/actions/${encodeURIComponent(id)}/approve`, { edited_body: editedBody ?? null });

/** POST /api/actions/{id}/reject – no body. */
export const rejectAction = (id: string) => http.post<DecisionResponse>(`/actions/${encodeURIComponent(id)}/reject`);

/** GET /api/actions/{id}/context · GET /api/findings/{id}/context – everything for the problem view + chat chips. */
export const getActionContext = (id: string, signal?: AbortSignal) =>
  http.get<ProblemContext>(`/actions/${encodeURIComponent(id)}/context`, signal);
export const getFindingContext = (id: string, signal?: AbortSignal) =>
  http.get<ProblemContext>(`/findings/${encodeURIComponent(id)}/context`, signal);

/** POST /api/actions/{id}/review – instant rule check of the edited draft (call debounced while typing). */
export const reviewDraft = (id: string, body: string, signal?: AbortSignal) =>
  http.post<DraftReview>(`/actions/${encodeURIComponent(id)}/review`, { body, lang: locale.value }, signal);

/**
 * POST /api/actions/{id}/redraft – the Rewrite button (3–8 s). Returns a PROPOSAL for the editor: nothing is stored
 * or sent; the owner still has to click "Approve and send" (`edited_body`). Empty instruction = "write it again".
 */
export const redraftAction = (id: string, req: { instruction?: string; body?: string }) =>
  http.post<RedraftProposal>(`/actions/${encodeURIComponent(id)}/redraft`, { ...req, lang: locale.value } satisfies RedraftRequest);

/** GET /api/actions/{id}/redraft/hints – chips + placeholder for the Rewrite pop-up, in the UI language. */
export const getRedraftHints = (id: string, signal?: AbortSignal) =>
  http.get<RedraftHints>(`/actions/${encodeURIComponent(id)}/redraft/hints`, signal);
