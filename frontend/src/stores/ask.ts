import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";
import { ApiError, askCfo, getActionContext, getAskSuggestions, getFindingContext } from "@/api";
import { locale, t } from "@/i18n";
import type { AskAnswer, AskSuggestion, ChatTurn } from "@/types/api";
import { useDashboardStore } from "./dashboard";

const message = (e: unknown) => (e instanceof ApiError || e instanceof Error ? e.message : t("Something went wrong."));

/** Which problem a question is about (problem chat on the backend). */
export interface ProblemRef {
  action_id?: string;
  finding_id?: string;
}

export interface AskTurn {
  id: number;
  question: string;
  /** set when the answer arrived */
  answer?: AskAnswer;
  error?: string;
  /** set when asked from inside one decision (Action center) – that panel shows only its own turns */
  context?: string;
}

/**
 * "Ask your CFO" (docs/API.md → Ask your CFO). App-level, so there is ONE conversation that survives navigation:
 * the overview's floating chat (components/ask/AskChat) shows every turn; the contextual panel inside one Action
 * center decision (components/ask/AskContext) shows only the turns asked there (`context`).
 * Suggestions are re-fetched whenever they can change: language switch, sync finished, reset.
 */
export const useAskStore = defineStore("ask", () => {
  const dashboard = useDashboardStore();

  const suggestions = ref<AskSuggestion[]>([]);
  const note = ref<string | null>(null);
  const loadingSuggestions = ref(false);
  const suggestionsError = ref<string | null>(null);

  const turns = ref<AskTurn[]>([]);
  const asking = computed(() => turns.value.some((x) => !x.answer && !x.error));
  let nextId = 1;

  async function loadSuggestions() {
    loadingSuggestions.value = true;
    suggestionsError.value = null;
    try {
      const s = await getAskSuggestions();
      suggestions.value = s.suggestions;
      note.value = s.note;
    } catch (e) {
      suggestionsError.value = message(e);
    } finally {
      loadingSuggestions.value = false;
    }
  }

  // --- problem chat (one decision in the Action center) ---------------------------------------------
  /** Chips per problem, from GET /api/{actions|findings}/{id}/context, keyed by the decision key. */
  const contextSuggestions = ref<Record<string, AskSuggestion[]>>({});
  const contextLoading = ref<Record<string, boolean>>({});

  async function loadContext(key: string, ref: ProblemRef) {
    if (contextLoading.value[key]) return;
    contextLoading.value[key] = true;
    try {
      const c = ref.action_id ? await getActionContext(ref.action_id) : ref.finding_id ? await getFindingContext(ref.finding_id) : null;
      if (c) contextSuggestions.value[key] = c.suggestions.suggestions;
    } catch {
      // no chips from the backend → the view falls back to its own case questions (components/ask/contextual.ts)
    } finally {
      contextLoading.value[key] = false;
    }
  }

  /** The last answered turns of one problem as `history` (oldest first, max 6 = 3 question/answer pairs). */
  function historyOf(context: string): ChatTurn[] {
    return turns.value
      .filter((x) => x.context === context && x.answer)
      .flatMap((x) => [
        { role: "owner" as const, text: x.question },
        { role: "agent" as const, text: x.answer!.answer },
      ])
      .slice(-6);
  }

  /**
   * Chip → pass the suggestion's question unchanged (instant prepared answer).
   * Typed → 1–500 characters, answered by the model in 3–7 s. One question at a time.
   * `opts.context` = the decision it was asked from (tags the turn, the panel shows only its own turns);
   * `opts.action_id` / `opts.finding_id` make it a problem chat on the backend (with the turns so far as history).
   */
  async function ask(question: string, opts: { context?: string } & ProblemRef = {}) {
    const q = question.trim().slice(0, 500);
    if (!q || asking.value) return;
    const history = opts.context ? historyOf(opts.context) : [];
    const turn: AskTurn = { id: nextId++, question: q, context: opts.context };
    turns.value.push(turn);
    const i = turns.value.length - 1;
    try {
      const a = await askCfo(q, {
        action_id: opts.action_id,
        finding_id: opts.finding_id,
        history: history.length ? history : undefined,
      });
      turns.value[i] = { ...turn, answer: a };
      // a problem chat refreshes that problem's chips; the general chat its own
      if (opts.context) {
        if (a.suggestions?.length) contextSuggestions.value[opts.context] = a.suggestions;
      } else {
        suggestions.value = a.suggestions;
      }
      note.value = a.note;
    } catch (e) {
      turns.value[i] = { ...turn, error: message(e) };
    }
  }

  /** Without `context`: the whole conversation. With it: only the turns of that decision. */
  function clear(context?: string) {
    turns.value = context ? turns.value.filter((x) => x.context !== context) : [];
  }

  // What the backend can suggest depends on the language and on whether the inbox was checked.
  watch(locale, () => {
    contextSuggestions.value = {};
    loadSuggestions();
  });
  watch(
    () => [dashboard.hasSynced, dashboard.findings.length] as const,
    ([synced], [wasSynced]) => {
      if (wasSynced && !synced) clear(); // demo reset → old answers talk about numbers that are gone
      contextSuggestions.value = {};
      loadSuggestions();
    },
  );

  return {
    suggestions, note, loadingSuggestions, suggestionsError, turns, asking,
    contextSuggestions, contextLoading,
    loadSuggestions, loadContext, ask, clear,
  };
});
