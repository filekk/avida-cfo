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
}

/**
 * "Ask your CFO" (docs/API.md → Ask your CFO). App-level, so there is ONE conversation that survives navigation:
 * the same turns show in the Action center card and in the overview's floating chat (components/ask/AskChat).
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
   */
  async function ask(question: string) {
    const q = question.trim().slice(0, 500);
    if (!q || asking.value) return;
    const turn: AskTurn = { id: nextId++, question: q };
    turns.value.push(turn);
    const i = turns.value.length - 1;
    try {
      const a = await askCfo(q);
      turns.value[i] = { ...turn, answer: a };
      suggestions.value = a.suggestions;
      note.value = a.note;
    } catch (e) {
      turns.value[i] = { ...turn, error: message(e) };
    }
  }

  function clear() {
    turns.value = [];
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
