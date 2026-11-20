import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { ApiError, approveAction, getDashboard, rejectAction, resetDemo, startSync } from "@/api";
import { t } from "@/i18n";
import type { Action, Dashboard, TraceEvent } from "@/types/api";

const message = (e: unknown) => (e instanceof ApiError || e instanceof Error ? e.message : t("Something went wrong."));

/**
 * Single source of truth for the demo flow:
 *   load() → sync() (SSE trace → new dashboard) → decide() per action → reset()
 * Kept at app level so a running sync survives navigation between views.
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

  // --- getters -----------------------------------------------------------------------------------
  const kpis = computed(() => dashboard.value?.kpis ?? null);
  const findings = computed(() => dashboard.value?.findings ?? []);
  const actions = computed(() => dashboard.value?.actions ?? []);
  const pendingActions = computed(() => actions.value.filter((a) => a.status === "pending"));
  const hasSynced = computed(() => !!dashboard.value?.scenarios.recommended);
  const isSafe = computed(() => !!kpis.value && kpis.value.min_balance >= kpis.value.safety_buffer);

  const findingById = (id: string) => findings.value.find((f) => f.id === id);
  const actionById = (id: string) => actions.value.find((a) => a.id === id);

  // --- actions -----------------------------------------------------------------------------------
  async function load(force = false) {
    if (loading.value || (dashboard.value && !force)) return;
    loading.value = true;
    error.value = null;
    try {
      dashboard.value = await getDashboard();
    } catch (e) {
      error.value = message(e);
    } finally {
      loading.value = false;
    }
  }

  function sync() {
    if (syncing.value) return;
    trace.value = [];
    syncError.value = null;
    syncing.value = true;
    closeSync = startSync({
      onTrace: (e) => trace.value.push(e),
      onResult: (d) => {
        dashboard.value = d;
        syncing.value = false;
        closeSync = null;
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
    } catch (e) {
      error.value = message(e);
    } finally {
      deciding.value.delete(id);
    }
  }

  async function reset() {
    cancelSync();
    trace.value = [];
    syncError.value = null;
    error.value = null;
    try {
      dashboard.value = await resetDemo();
    } catch (e) {
      error.value = message(e);
    }
  }

  function replaceAction(action: Action) {
    if (!dashboard.value) return;
    dashboard.value.actions = dashboard.value.actions.map((a) => (a.id === action.id ? action : a));
  }

  return {
    dashboard, loading, error, trace, syncing, syncError, deciding,
    kpis, findings, actions, pendingActions, hasSynced, isSafe,
    findingById, actionById,
    load, sync, cancelSync, decide, reset,
  };
});
