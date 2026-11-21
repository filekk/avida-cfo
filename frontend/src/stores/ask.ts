import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";
import { ApiError, askCfo, getAskSuggestions } from "@/api";
import { locale, t } from "@/i18n";
import type { AskAnswer, AskSuggestion } from "@/types/api";
import { useDashboardStore } from "./dashboard";

const message = (e: unknown) => (e instanceof ApiError || e instanceof Error ? e.message : t("Something went wrong."));

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

  /**
   * Chip → pass the suggestion's question unchanged (instant prepared answer).
   * Typed → 1–500 characters, answered by the model in 3–7 s. One question at a time.
   * `opts.context`: the decision it was asked from (tags the turn). `opts.subject`: put in front of the question
   * the backend gets ("CloudHost GmbH: price change – is this fair?") so short follow-ups make sense; the owner
   * still sees their own words. Never pass a subject for a chip – it must arrive unchanged.
   */
  async function ask(question: string, opts: { context?: string; subject?: string } = {}) {
    const q = question.trim().slice(0, 500);
    if (!q || asking.value) return;
    const turn: AskTurn = { id: nextId++, question: q, context: opts.context };
    turns.value.push(turn);
    const i = turns.value.length - 1;
    const sent = opts.subject ? `${opts.subject} – ${q}`.slice(0, 500) : q;
    try {
      const a = await askCfo(sent);
      turns.value[i] = { ...turn, answer: a };
      // a contextual question must not replace the general suggestions with ones about this case only
      if (!opts.context) suggestions.value = a.suggestions;
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
  watch(locale, () => loadSuggestions());
  watch(
    () => [dashboard.hasSynced, dashboard.findings.length] as const,
    ([synced], [wasSynced]) => {
      if (wasSynced && !synced) clear(); // demo reset → old answers talk about numbers that are gone
      loadSuggestions();
    },
  );

  return { suggestions, note, loadingSuggestions, suggestionsError, turns, asking, loadSuggestions, ask, clear };
});
