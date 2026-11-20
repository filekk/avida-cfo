<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import AgentPipeline from "@/components/agent/AgentPipeline.vue";
import AgentTrace from "@/components/agent/AgentTrace.vue";
import AutonomyLegend from "@/components/agent/AutonomyLegend.vue";
import ForecastChart from "@/components/dashboard/ForecastChart.vue";
import HeadlineBanner from "@/components/dashboard/HeadlineBanner.vue";
import KpiCard from "@/components/dashboard/KpiCard.vue";
import PaymentsDonut from "@/components/dashboard/PaymentsDonut.vue";
import PeriodPicker from "@/components/dashboard/PeriodPicker.vue";
import { scenarioLines } from "@/components/dashboard/chart";
import FindingCard from "@/components/findings/FindingCard.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import CollapseTransition from "@/components/ui/CollapseTransition.vue";
import IconTile from "@/components/ui/IconTile.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { periodLabel, useForecastPeriod } from "@/composables/useForecastPeriod";
import { useDashboardStore } from "@/stores/dashboard";
import { fmtDate } from "@/utils/format";

/**
 * Start screen, top → bottom: how am I doing (headline + KPIs) → where is my money going (forecast + payments)
 * → let Avida check the inbox (pipeline, trace, waiting decisions) → what it found → who decides what.
 */
const store = useDashboardStore();
const { dashboard, kpis, loading, error, trace, syncing, syncError, findings, pendingActions, hasSynced, isSafe } =
  storeToRefs(store);

const lines = computed(() => (dashboard.value ? scenarioLines(dashboard.value.scenarios) : []));
const mainForecast = computed(() => (dashboard.value ? dashboard.value.scenarios.recommended ?? dashboard.value.scenarios.current : null));
const horizon = computed(() => dashboard.value?.scenarios.current.horizon_days ?? 90);

// --- period window (the backend forecast covers `horizon` days; the UI shows the first `shownDays`) ---
const { days: requestedDays } = useForecastPeriod();
const shownDays = computed(() => Math.min(requestedDays.value, horizon.value));
const periodEnd = computed(() => mainForecast.value?.series[shownDays.value - 1]?.date ?? null);
const outflowsInPeriod = computed(() =>
  (mainForecast.value?.largest_outflows ?? []).filter((o) => !periodEnd.value || o.date <= periodEnd.value),
);

const lowIsBad = computed(() => !!kpis.value && kpis.value.min_balance < kpis.value.safety_buffer);
const pipelineState = computed(() => (syncing.value ? "running" : hasSynced.value ? "done" : "idle"));
const activeAgent = computed(() => trace.value[trace.value.length - 1]?.agent ?? null);
</script>

<template>
  <AlertBanner v-if="error" dismissible @dismiss="error = null">
    {{ error }}
    <button type="button" class="ml-2 underline" @click="store.load(true)">Try again</button>
  </AlertBanner>

  <!-- loading -->
  <template v-if="!dashboard && loading">
    <SkeletonBlock height="h-32" />
    <div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,9.5rem),1fr))] gap-3">
      <SkeletonBlock v-for="i in 4" :key="i" height="h-32" />
    </div>
    <SkeletonBlock height="h-80" />
  </template>

  <template v-else-if="dashboard && kpis">
    <HeadlineBanner :headline="dashboard.headline" :safe="isSafe" :days-safe="kpis.days_safe" :horizon="horizon" />

    <!-- 1. how am I doing: green = good for you, red = needs attention.
         auto-fit with a rem minimum: 4 → 2 columns by width, and 1 column on phones at large text sizes -->
    <section class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,9.5rem),1fr))] gap-3" aria-label="Key figures">
      <KpiCard icon="wallet" label="In the bank today" :amount="kpis.balance_today" />
      <KpiCard
        icon="trendingDown"
        label="Lowest balance ahead"
        :amount="kpis.min_balance"
        :sub="fmtDate(kpis.min_date)"
        :tone="lowIsBad ? 'negative' : 'positive'"
        :delta="lowIsBad ? { text: 'below cushion', tone: 'negative' } : { text: 'above cushion', tone: 'positive' }"
      />
      <KpiCard icon="shield" label="Your safety cushion" :amount="kpis.safety_buffer" sub="minimum to keep" />
      <KpiCard
        icon="piggyBank"
        label="Saved by Avida"
        :amount="kpis.saved_liquidity"
        sub="next 12 months"
        :tone="kpis.saved_liquidity > 0 ? 'positive' : 'neutral'"
      />
    </section>

    <!-- 2. where is my money going -->
    <div class="grid gap-5 lg:grid-cols-3">
      <BaseCard class="lg:col-span-2" :title="`Your money, next ${periodLabel(shownDays)}`" eyebrow="Forecast">
        <template #actions>
          <PeriodPicker v-model="requestedDays" :max="horizon" />
        </template>
        <ForecastChart :lines="lines" :days="shownDays" />
      </BaseCard>
      <BaseCard title="Biggest payments ahead" :eyebrow="`Next ${periodLabel(shownDays)}`">
        <PaymentsDonut :outflows="outflowsInPeriod" :period-label="periodLabel(shownDays)" />
      </BaseCard>
    </div>

    <!-- 3. the ONE primary action on this screen + what the assistant did -->
    <BaseCard>
      <div class="grid gap-6">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="grid gap-1">
            <h2 class="text-xl font-bold">
              {{ hasSynced ? "Avida checked your inbox" : "Let Avida check your inbox" }}
            </h2>
            <p class="flex items-center gap-1.5 text-label text-muted">
              <AppIcon name="shield" :size="16" /> Nothing is sent without your OK.
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <BaseButton v-if="hasSynced" variant="ghost" icon="reset" :disabled="syncing" @click="store.reset()">
              Start over
            </BaseButton>
            <BaseButton size="lg" icon="inbox" :loading="syncing" @click="store.sync()">
              {{ syncing ? "Checking…" : hasSynced ? "Check again" : "Check my inbox" }}
            </BaseButton>
          </div>
        </div>
        <AgentPipeline :state="pipelineState" :active-agent="activeAgent" :pending="pendingActions.length" />
      </div>
    </BaseCard>

    <CollapseTransition>
      <AlertBanner v-if="syncError" dismissible @dismiss="syncError = null">{{ syncError }}</AlertBanner>
    </CollapseTransition>
    <AgentTrace :events="trace" :running="syncing" />

    <!-- waiting decisions -->
    <CollapseTransition>
      <RouterLink
        v-if="pendingActions.length"
        :to="{ name: 'decisions' }"
        class="group flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sun bg-warn-soft px-5 py-4 font-semibold text-warn hover:shadow-lift"
      >
        <span class="flex items-center gap-3">
          <IconTile icon="approval" tone="accent" />
          {{ pendingActions.length }} {{ pendingActions.length === 1 ? "decision is" : "decisions are" }} waiting for you
        </span>
        <span class="flex items-center gap-1.5">
          Review <AppIcon name="arrowRight" :size="18" class="transition-transform group-hover:translate-x-1" />
        </span>
      </RouterLink>
    </CollapseTransition>

    <!-- 4. what it found – half-width cards read better than full-width bands -->
    <section v-if="findings.length" class="grid gap-3">
      <PageHeader eyebrow="Analyst Agent + Legal Agent" title="What I found" />
      <div class="grid gap-4 md:grid-cols-2">
        <FindingCard v-for="f in findings" :key="f.id" :finding="f" />
      </div>
    </section>

    <BaseCard eyebrow="You stay in control" title="Who decides what">
      <AutonomyLegend detailed />
    </BaseCard>
  </template>
</template>
