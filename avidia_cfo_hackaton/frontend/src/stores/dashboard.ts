import { defineStore } from "pinia";
import { computed, ref } from "vue";
import {
  approveAction,
  errorMessage,
  getAudit,
  getDashboard,
  getRedraftHints,
  redraftAction,
  rejectAction,
  resetDemo,
  reviewDraft,
  startSync,
} from "@/api";
import { locale } from "@/i18n";
import type { Action, Dashboard, DraftReview, RedraftHints, RedraftProposal, TraceEvent } from "@/types/api";

/**
 * Single source of truth for the demo flow:
 *   load() → sync() (SSE trace → new dashboard) → decide() per action → reset()
 * Kept at app level so a running sync survives navigation between views.
 *
 * Several requests can be in flight at once (a language switch while a decision refreshes the plan, two quick
 * decisions, a reset during a load). Every request that replaces or patches the dashboard takes a ticket from
 * `nextTicket()`; its answer is applied only if no newer ticket was taken meanwhile – a late, older answer never
 * overwrites a newer one (wrong language, an action flipping back to "pending", a pre-reset dashboard).
 */
export const useDashboardStore = defineStore("dashboard", () => {
  // --- state -------------------------------------------------------------------------------------
  const dashboard = ref<Dashboard | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const trace = ref<TraceEvent[]>([]);
  const syncing = ref(false);
  const syncError = ref<string | null>(null);
  let closeSync: (() => void) | null = null;

  /** Action ids with a request in flight (disables their buttons). */
  const deciding = ref<Set<string>>(new Set());

  /**
   * When the inbox was last checked (ISO). Set when a check finishes; after a page reload it comes from the
   * history (`sync_finished` in /api/audit), so "5 minutes ago" stays true. null = never / after a reset.
   */
  const checkedAt = ref<string | null>(null);

  // --- getters -----------------------------------------------------------------------------------
  const kpis = computed(() => dashboard.value?.kpis ?? null);
  const findings = computed(() => dashboard.value?.findings ?? []);
  const actions = computed(() => dashboard.value?.actions ?? []);
  const pendingActions = computed(() => actions.value.filter((a) => a.status === "pending"));
  const hasSynced = computed(() => !!dashboard.value?.scenarios.recommended);
  const isSafe = computed(() => !!kpis.value && kpis.value.min_balance >= kpis.value.safety_buffer);

  const findingById = (id: string) => findings.value.find((f) => f.id === id);
  const actionById = (id: string) => actions.value.find((a) => a.id === id);

  // --- request ordering (see the store comment) ----------------------------------------------------
  let ticket = 0;
  const nextTicket = () => ++ticket;
  const isLatest = (mine: number) => mine === ticket;
  let loadsInFlight = 0;
  /** Bumped by reset(): an answer from before the reset must not bring old state back. */
  let resets = 0;

  // --- actions -----------------------------------------------------------------------------------
  /** `force` (language switch, retry) always asks again – even while another load is still running. */
  async function load(force = false) {
    if (!force && (loading.value || dashboard.value)) return;
    const mine = nextTicket();
    loadsInFlight++;
    loading.value = true;
    error.value = null;
    try {
      const d = await getDashboard();
      if (isLatest(mine)) dashboard.value = d;
    } catch (e) {
      if (isLatest(mine)) error.value = errorMessage(e);
    } finally {
      loading.value = --loadsInFlight > 0;
    }
    if (isLatest(mine) && hasSynced.value && !checkedAt.value) loadCheckedAt();
  }

  /** Last finished inbox check from the history (best effort – without it the top bar just shows no time). */
  async function loadCheckedAt() {
    const epoch = resets;
    try {
      const last = (await getAudit()).filter((e) => e.event === "sync_finished").pop();
      if (last && !checkedAt.value && epoch === resets) checkedAt.value = last.time;
    } catch {
      /* history unavailable – no "checked … ago" line */
    }
  }

  function sync() {
    if (syncing.value) return;
    const lang = locale.value;
    trace.value = [];
    syncError.value = null;
    syncing.value = true;
    closeSync = startSync({
      onTrace: (e) => trace.value.push(e),
      onResult: (d) => {
        nextTicket(); // a dashboard request still in flight is older than this result
        dashboard.value = d;
        checkedAt.value = new Date().toISOString();
        syncing.value = false;
        closeSync = null;
        // the language was switched during the check (AppLayout skips reloads while syncing) → texts follow now
        if (locale.value !== lang) load(true);
      },
      onError: (m) => {
        syncError.value = m;
        syncing.value = false;
        closeSync = null;
      },
    });
  }

  function cancelSync() {
    closeSync?.();
    closeSync = null;
    syncing.value = false;
  }

  /** Owner decision – call ONLY from an explicit click (UI rule #1). */
  async function decide(id: string, approve: boolean, editedBody?: string) {
    if (deciding.value.has(id)) return;
    deciding.value.add(id);
    error.value = null;
    try {
      const r = approve ? await approveAction(id, editedBody) : await rejectAction(id);
      replaceAction(r.action);
      if (dashboard.value) dashboard.value.kpis.saved_liquidity = r.saved_liquidity;
      await refreshPlan(); // approve AND "Not now" can change the plan (a declined rejection = the increase is in)
    } catch (e) {
      error.value = errorMessage(e);
    } finally {
      deciding.value.delete(id);
    }
  }

  /**
   * A decision can change the plan (the customer's simulated reply confirms paying on time, an approved overdraft
   * bridges the gap, a declined price rejection lets the increase in → the backend re-runs the forecast). Pull the live parts – KPIs, headline, briefing, scenarios, actions – so the overview
   * shows what the decision achieved (numbers glide via AnimatedNumber). Best effort: on failure the old view stays.
   */
  async function refreshPlan() {
    const mine = nextTicket();
    // A load still running (e.g. after a language switch) is outdated by this ticket and will be dropped –
    // then this answer, the freshest full dashboard, replaces everything instead of patching the live parts.
    const supersedesLoad = loadsInFlight > 0;
    try {
      const d = await getDashboard();
      if (!isLatest(mine) || !dashboard.value) return; // a newer decision / load / sync already answered
      if (supersedesLoad) {
        dashboard.value = d;
        return;
      }
      Object.assign(dashboard.value, {
        kpis: d.kpis,
        headline: d.headline,
        analysis: d.analysis,
        scenarios: d.scenarios,
        actions: d.actions,
      });
    } catch {
      /* keep what we have – the decision itself already succeeded */
    }
  }

  async function reset() {
    cancelSync();
    resets++;
    const mine = nextTicket();
    trace.value = [];
    syncError.value = null;
    error.value = null;
    checkedAt.value = null;
    try {
      const d = await resetDemo();
      if (isLatest(mine)) dashboard.value = d;
    } catch (e) {
      error.value = errorMessage(e);
    }
  }

  /**
   * AV Rewrite = POST /api/actions/{id}/redraft (3–8 s): the Negotiator rewrites, the Legal Agent reviews.
   * Returns a PROPOSAL for the editor – nothing is stored or sent; the owner still clicks "Approve and send".
   * Throws: the caller (view) shows the error next to the rewrite field.
   */
  async function redraft(id: string, body: string, instruction: string): Promise<RedraftProposal> {
    try {
      return await redraftAction(id, { body, instruction: instruction.trim().slice(0, 300) || undefined });
    } catch (e) {
      throw new Error(errorMessage(e));
    }
  }

  /** Chips + placeholder for the Rewrite pop-up; null when the backend has none (the UI uses its own). */
  async function redraftHints(id: string): Promise<RedraftHints | null> {
    try {
      return await getRedraftHints(id);
    } catch {
      return null;
    }
  }

  /** Instant rule check of the edited draft (clause cited, amounts, no placeholder …); null when it failed. */
  async function review(id: string, body: string, signal?: AbortSignal): Promise<DraftReview | null> {
    try {
      return await reviewDraft(id, body, signal);
    } catch {
      return null;
    }
  }

  function replaceAction(action: Action) {
    if (!dashboard.value) return;
    dashboard.value.actions = dashboard.value.actions.map((a) => (a.id === action.id ? action : a));
  }

  return {
    dashboard, loading, error, trace, syncing, syncError, deciding, checkedAt,
    kpis, findings, actions, pendingActions, hasSynced, isSafe,
    findingById, actionById,
    load, sync, cancelSync, decide, redraft, redraftHints, review, reset,
  };
});
