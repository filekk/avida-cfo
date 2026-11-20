<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { decide, eur, fmtDate, getDashboard, sync } from "./api";
import ActionCard from "./components/ActionCard.vue";
import AgentTrace from "./components/AgentTrace.vue";
import AutonomyLegend from "./components/AutonomyLegend.vue";
import FindingCard from "./components/FindingCard.vue";
import ForecastChart, { type ChartLine } from "./components/ForecastChart.vue";
import KpiCard from "./components/KpiCard.vue";
import type { Dashboard, TraceEvent } from "./types";

const dash = ref<Dashboard | null>(null);
const trace = ref<TraceEvent[]>([]);
const running = ref(false);
const error = ref<string | null>(null);

onMounted(async () => {
  try {
    dash.value = await getDashboard();
  } catch {
    error.value = "Cannot reach the backend.";
  }
});

function startSync() {
  trace.value = [];
  error.value = null;
  running.value = true;
  sync(
    (e) => trace.value.push(e),
    (d) => { dash.value = d; running.value = false; },
    (m) => { error.value = m; running.value = false; },
  );
}

async function onDecide(id: string, approve: boolean, body?: string) {
  const r = await decide(id, approve, body);
  if (!dash.value) return;
  dash.value.kpis.saved_liquidity = r.saved_liquidity;
  dash.value.actions = dash.value.actions.map((a) => (a.id === id ? r.action : a));
}

const safe = computed(() => !!dash.value && dash.value.kpis.min_balance >= dash.value.kpis.safety_buffer);

const lines = computed<ChartLine[]>(() => {
  if (!dash.value) return [];
  const s = dash.value.scenarios;
  const out: ChartLine[] = [];
  if (s.if_accepted) out.push({ f: s.if_accepted, color: "#e11d48", label: "If you accept every price increase", dashed: true });
  out.push({
    f: s.recommended ?? s.current,
    color: "#0f766e",
    label: s.recommended ? "If you follow the recommendations" : "Your forecast",
  });
  return out;
});
</script>

<template>
  <p v-if="!dash" class="p-10 text-xl">{{ error ?? "Loading…" }}</p>

  <div v-else class="mx-auto max-w-6xl space-y-6 px-4 py-6">
    <header class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-3xl font-extrabold">Avida CFO</h1>
        <p class="text-slate-500">{{ dash.company.name }} · {{ fmtDate(dash.today) }}</p>
      </div>
      <button
        :disabled="running"
        class="rounded-xl bg-slate-900 px-6 py-3 text-lg font-bold text-white hover:bg-slate-700 disabled:opacity-50"
        @click="startSync"
      >
        {{ running ? "Checking…" : "📥 Check my inbox" }}
      </button>
    </header>

    <!-- One sentence the owner understands at a glance -->
    <section :class="['rounded-2xl p-6 text-white', safe ? 'bg-emerald-600' : 'bg-amber-500']">
      <p class="text-2xl font-bold leading-snug">{{ dash.headline }}</p>
    </section>

    <section class="grid grid-cols-2 gap-4 md:grid-cols-4">
      <KpiCard label="Money in the bank today" :value="eur(dash.kpis.balance_today)" />
      <KpiCard label="Days you are safe" :value="String(dash.kpis.days_safe)" />
      <KpiCard label="Lowest balance ahead" :value="eur(dash.kpis.min_balance)" :sub="fmtDate(dash.kpis.min_date)" />
      <KpiCard label="Saved by Avida (12 months)" :value="eur(dash.kpis.saved_liquidity)" highlight />
    </section>

    <p v-if="error" class="rounded-lg bg-rose-100 p-3 text-rose-800">{{ error }}</p>

    <AgentTrace :events="trace" :running="running" />

    <section class="rounded-2xl bg-white p-5 shadow-sm">
      <h2 class="mb-3 text-lg font-bold">Your money over the next {{ dash.scenarios.current.horizon_days }} days</h2>
      <ForecastChart :lines="lines" />
    </section>

    <section v-if="dash.findings.length" class="space-y-4">
      <h2 class="text-2xl font-bold">What I found</h2>
      <FindingCard v-for="f in dash.findings" :key="f.id" :f="f" />
    </section>

    <section v-if="dash.actions.length" class="space-y-4">
      <h2 class="text-2xl font-bold">Your decision</h2>
      <ActionCard v-for="a in dash.actions" :key="a.id" :a="a" @decide="onDecide" />
    </section>

    <footer class="space-y-2 pb-10 text-sm text-slate-500">
      <AutonomyLegend />
      <p>All actions are simulated. Contract checks are not legal advice. Powered by an open-weights model on Red Hat OpenShift AI.</p>
    </footer>
  </div>
</template>
