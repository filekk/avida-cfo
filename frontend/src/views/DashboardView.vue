<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import AgentPipeline from "@/components/agent/AgentPipeline.vue";
import AgentTrace from "@/components/agent/AgentTrace.vue";
import AutonomyLegend from "@/components/agent/AutonomyLegend.vue";
import ForecastChart from "@/components/dashboard/ForecastChart.vue";
import HeadlineBanner from "@/components/dashboard/HeadlineBanner.vue";
import KpiCard from "@/components/dashboard/KpiCard.vue";
import OutflowBars from "@/components/dashboard/OutflowBars.vue";
import { scenarioLines } from "@/components/dashboard/chart";
import FindingCard from "@/components/findings/FindingCard.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { useDashboardStore } from "@/stores/dashboard";
import { eur, fmtDate } from "@/utils/format";

/**
 * Start screen. Demo flow step 1–2: forecast → "Check my inbox" (SSE trace) → findings + pending decisions.
 */
const store = useDashboardStore();
const { dashboard, kpis, loading, error, trace, syncing, syncError, findings, pendingActions, hasSynced, isSafe } =
  storeToRefs(store);

const lines = computed(() => (dashboard.value ? scenarioLines(dashboard.value.scenarios) : []));
const mainForecast = computed(() => (dashboard.value ? dashboard.value.scenarios.recommended ?? dashboard.value.scenarios.current : null));
const horizon = computed(() => dashboard.value?.scenarios.current.horizon_days ?? 90);

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
    <SkeletonBlock height="h-28" />
    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <SkeletonBlock v-for="i in 4" :key="i" height="h-28" />
    </div>
    <SkeletonBlock height="h-72" />
  </template>

  <template v-else-if="dashboard && kpis">
    <HeadlineBanner :headline="dashboard.headline" :safe="isSafe" :days-safe="kpis.days_safe" :horizon="horizon" />

    <section class="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Key figures">
      <KpiCard icon="wallet" label="In the bank today" :value="eur(kpis.balance_today)" />
      <KpiCard
        icon="trendingDown"
        label="Lowest balance ahead"
        :value="eur(kpis.min_balance)"
        :sub="fmtDate(kpis.min_date)"
        :delta="
          kpis.min_balance < kpis.safety_buffer
            ? { text: 'below cushion', tone: 'negative' }
            : { text: 'above cushion', tone: 'positive' }
        "
      />
      <KpiCard icon="shield" label="Your safety cushion" :value="eur(kpis.safety_buffer)" sub="minimum you want to keep" />
      <KpiCard
        icon="piggyBank"
        label="Saved by Avida"
        :value="eur(kpis.saved_liquidity)"
        sub="next 12 months"
        :highlight="kpis.saved_liquidity > 0"
      />
    </section>

    <!-- the ONE primary action on this screen + how it works -->
    <BaseCard>
      <div class="grid gap-6">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="grid gap-1">
            <h2 class="text-lg font-bold">
              {{ hasSynced ? "Avida checked your inbox" : "Let Avida check your inbox" }}
            </h2>
            <p class="flex items-center gap-1.5 text-sm text-muted">
              <AppIcon name="shield" :size="15" /> Nothing is sent without your OK.
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

    <AlertBanner v-if="syncError" dismissible @dismiss="syncError = null">{{ syncError }}</AlertBanner>
    <AgentTrace :events="trace" :running="syncing" />

    <!-- pending decisions callout -->
    <RouterLink
      v-if="pendingActions.length"
      :to="{ name: 'decisions' }"
      class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sun bg-warn-soft px-5 py-4 font-semibold text-warn hover:bg-warn-soft/70"
    >
      <span class="flex items-center gap-3">
        <span class="grid h-9 w-9 place-items-center rounded-lg bg-sun text-sun-on"><AppIcon name="approval" :size="18" /></span>
        {{ pendingActions.length }} {{ pendingActions.length === 1 ? "decision is" : "decisions are" }} waiting for you
      </span>
      <span class="flex items-center gap-1">Review <AppIcon name="arrowRight" /></span>
    </RouterLink>

    <div class="grid gap-5 lg:grid-cols-3">
      <BaseCard class="lg:col-span-2" :title="`Your money, next ${horizon} days`" eyebrow="Forecast">
        <ForecastChart :lines="lines" />
      </BaseCard>
      <BaseCard title="Biggest payments ahead" :eyebrow="`Next ${horizon} days`">
        <OutflowBars :outflows="mainForecast?.largest_outflows ?? []" />
      </BaseCard>
    </div>

    <section v-if="findings.length" class="grid gap-3">
      <PageHeader eyebrow="Inbox Agent + Contract Agent" title="What I found" />
      <FindingCard v-for="f in findings" :key="f.id" :finding="f" />
    </section>

    <BaseCard eyebrow="You stay in control" title="Who decides what">
      <AutonomyLegend detailed />
    </BaseCard>
  </template>
</template>
