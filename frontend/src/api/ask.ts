import type { AskAnswer, AskRequest, AskSuggestions } from "@/types/api";
import { locale } from "@/i18n";
import { http } from "./http";

/**
 * "Ask your CFO" – the owner asks in plain language, the backend routes the question to the right agent.
 * See docs/API.md → "Ask your CFO".
 *
 * - Chip clicked → send the suggestion's `question` UNCHANGED: the backend recognises it and answers instantly
 *   with a prepared answer (`source: "rules"`).
 * - Typed question → the model answers in 3–7 s (`source: "llm"`), or a cached answer if it can't (`"fallback"`).
 * - Re-fetch suggestions after every sync, reset and language switch.
 */

/** GET /api/ask/suggestions – clickable questions for the current situation, in the UI language. */
export const getAskSuggestions = (signal?: AbortSignal) => http.get<AskSuggestions>("/ask/suggestions", signal);

/**
 * POST /api/ask – 422 if the question is empty or longer than 500 characters.
 * Problem chat: pass `action_id` or `finding_id` (+ the last turns as `history`, oldest first, max 6) – the backend
 * keeps no chat state. Chips of the problem (`ProblemContext.suggestions`) are answered instantly.
 */
export const askCfo = (
  question: string,
  ctx: Pick<AskRequest, "action_id" | "finding_id" | "history"> = {},
  signal?: AbortSignal,
) => http.post<AskAnswer>("/ask", { question, lang: locale.value, ...ctx } satisfies AskRequest, signal);
