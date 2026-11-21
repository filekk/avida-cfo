import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";
import { askCfo, errorMessage, getActionContext, getAskSuggestions, getFindingContext } from "@/api";
import { locale } from "@/i18n";
import type { AskAnswer, AskSuggestion, ChatTurn } from "@/types/api";
import { useDashboardStore } from "./dashboard";

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
 * "Ask your CFO" (docs/API.md → Ask your CFO). App-level, so the conversations survive navigation. Two separate
 * histories: the overview's floating chat (components/ask/AskChat → `generalTurns`) and one per Action center
 * decision (components/ask/AskContext → `turnsOf(key)`); neither shows nor clears the other's turns.
 * Suggestions are re-fetched whenever they can change: language switch, sync finished, reset.
 */
export const useAskStore = defineStore("ask", () => {
  const dashboard = useDashboardStore();

  const suggestions = ref<AskSuggestion[]>([]);
  const note = ref<string | null>(null);
  const loadingSuggestions = ref(false);
  const suggestionsError = ref<string | null>(null);

  /** Every turn of both conversations; views read them through `generalTurns` / `turnsOf(context)`. */
  const turns = ref<AskTurn[]>([]);
  const pending = (x: AskTurn) => !x.answer && !x.error;
  /** The overview chat: only questions asked there (not the ones from inside an Action center decision). */
  const generalTurns = computed(() => turns.value.filter((x) => !x.context));
  /** The overview chat is waiting for an answer (the Action center has its own flag: `askingIn`). */
  const asking = computed(() => generalTurns.value.some(pending));
  const turnsOf = (context: string) => turns.value.filter((x) => x.context === context);
  const askingIn = (context: string) => turnsOf(context).some(pending);
  let nextId = 1;

  // Only the newest suggestions request may write: after a quick EN→DE→EN the German answer can arrive last, and
  // a German chip sent with lang=en would miss its instant prepared answer.
  let suggestionsRun = 0;
  async function loadSuggestions() {
    const run = ++suggestionsRun;
    loadingSuggestions.value = true;
    suggestionsError.value = null;
    try {
      const s = await getAskSuggestions();
      if (run !== suggestionsRun) return;
      suggestions.value = s.suggestions;
      note.value = s.note;
    } catch (e) {
      if (run === suggestionsRun) suggestionsError.value = errorMessage(e);
    } finally {
      if (run === suggestionsRun) loadingSuggestions.value = false;
    }
  }

  // --- problem chat (one decision in the Action center) ---------------------------------------------
  /** Chips per problem, from GET /api/{actions|findings}/{id}/context, keyed by the decision key. */
  const contextSuggestions = ref<Record<string, AskSuggestion[]>>({});
  /** The newest request per decision key – an older one (e.g. from before a language switch) is ignored. */
  const contextRequests: Record<string, object> = {};

  async function loadContext(key: string, ref: ProblemRef) {
    const mine = {};
    contextRequests[key] = mine;
    const lang = locale.value;
    try {
      const c = ref.action_id ? await getActionContext(ref.action_id) : ref.finding_id ? await getFindingContext(ref.finding_id) : null;
      if (c && contextRequests[key] === mine && lang === locale.value) contextSuggestions.value[key] = c.suggestions.suggestions;
    } catch {
      // no chips from the backend → the view falls back to its own case questions (components/ask/contextual.ts)
    } finally {
      if (contextRequests[key] === mine) delete contextRequests[key];
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
    // one question at a time per conversation – the overview chat and a decision's chat don't block each other
    if (!q || (opts.context ? askingIn(opts.context) : asking.value)) return;
    const history = opts.context ? historyOf(opts.context) : [];
    const turn: AskTurn = { id: nextId++, question: q, context: opts.context };
    turns.value.push(turn);
    // The array may be rebuilt while we wait (the other chat's "Start a new conversation", a demo reset), so
    // the turn is found again by id – never by its old position. A cleared turn just drops its late answer.
    const settle = (patch: Partial<AskTurn>) => {
      const i = turns.value.findIndex((x) => x.id === turn.id);
      if (i < 0) return false;
      turns.value[i] = { ...turn, ...patch };
      return true;
    };
    try {
      const a = await askCfo(q, {
        action_id: opts.action_id,
        finding_id: opts.finding_id,
        history: history.length ? history : undefined,
      });
      if (!settle({ answer: a })) return;
      // a problem chat refreshes that problem's chips; the general chat its own
      if (opts.context) {
        if (a.suggestions?.length) contextSuggestions.value[opts.context] = a.suggestions;
      } else {
        suggestions.value = a.suggestions;
        note.value = a.note;
      }
    } catch (e) {
      settle({ error: errorMessage(e) });
    }
  }

  /** Without `context`: the overview chat only. With it: only the turns of that decision. */
  function clear(context?: string) {
    turns.value = turns.value.filter((x) => (context ? x.context !== context : !!x.context));
  }

  /** Both conversations (demo reset: old answers talk about numbers that are gone). */
  function clearAll() {
    turns.value = [];
  }

  // What the backend can suggest depends on the language and on whether the inbox was checked.
  watch(locale, () => {
    contextSuggestions.value = {};
    loadSuggestions();
  });
  // Two sources, compared one by one: fires only when "synced" or the number of findings really changes – not on
  // every reload of the dashboard (a getter returning a new tuple would fire each time, fetching twice per switch).
  watch([() => dashboard.hasSynced, () => dashboard.findings.length], ([synced], [wasSynced]) => {
    if (wasSynced && !synced) clearAll(); // demo reset → old answers talk about numbers that are gone
    contextSuggestions.value = {};
    loadSuggestions();
  });

  return {
    suggestions, note, loadingSuggestions, suggestionsError, turns, generalTurns, asking, turnsOf, askingIn,
    contextSuggestions,
    loadSuggestions, loadContext, ask, clear, clearAll,
  };
});
