<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import AgentTrace from "@/components/agent/AgentTrace.vue";
import AutonomyLegend from "@/components/agent/AutonomyLegend.vue";
import ForecastChart from "@/components/dashboard/ForecastChart.vue";
import HeadlineBanner from "@/components/dashboard/HeadlineBanner.vue";
import KpiCard from "@/components/dashboard/KpiCard.vue";
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
const horizon = computed(() => dashboard.value?.scenarios.current.horizon_days ?? 90);
</script>

<template>
  <AlertBanner v-if="error" dismissible @dismiss="error = null">
    {{ error }}
    <button type="button" class="ml-2 underline" @click="store.load(true)">Try again</button>
  </AlertBanner>

  <!-- loading -->
  <template v-if="!dashboard && loading">
    <SkeletonBlock height="h-24" />
    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <SkeletonBlock v-for="i in 4" :key="i" height="h-24" />
    </div>
    <SkeletonBlock height="h-72" />
  </template>

  <template v-else-if="dashboard && kpis">
    <HeadlineBanner :headline="dashboard.headline" :safe="isSafe" />

    <section class="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Key figures">
      <KpiCard label="Money in the bank today" :value="eur(kpis.balance_today)" />
      <KpiCard
        label="Days you are safe"
        :value="String(kpis.days_safe)"
        :sub="`of the next ${horizon} days`"
      />
      <KpiCard
        label="Lowest balance ahead"
        :value="eur(kpis.min_balance)"
        :sub="fmtDate(kpis.min_date)"
        :delta="
          kpis.min_balance < kpis.safety_buffer
            ? { text: `below your ${eur(kpis.safety_buffer)} cushion`, tone: 'negative' }
            : { text: 'above your cushion', tone: 'positive' }
        "
      />
      <KpiCard
        label="Saved by Avida (12 months)"
        :value="eur(kpis.saved_liquidity)"
        :highlight="kpis.saved_liquidity > 0"
      />
    </section>

    <!-- the ONE primary action on this screen -->
    <BaseCard>
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div class="grid gap-1">
          <h2 class="text-base font-bold">
            {{ hasSynced ? "Avida checked your inbox" : "Let Avida check your inbox and contracts" }}
          </h2>
          <p class="text-muted">
            Three agents read new emails, compare price changes with your contracts and update your forecast.
            Nothing is sent without your approval.
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
    </BaseCard>

    <AlertBanner v-if="syncError" dismissible @dismiss="syncError = null">{{ syncError }}</AlertBanner>
    <AgentTrace :events="trace" :running="syncing" />

    <!-- pending decisions callout -->
    <RouterLink
      v-if="pendingActions.length"
      :to="{ name: 'decisions' }"
      class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sun bg-warn-soft px-5 py-4 font-semibold text-warn hover:bg-warn-soft/70"
    >
      <span class="flex items-center gap-2">
        <AppIcon name="approval" :size="18" />
        {{ pendingActions.length }} {{ pendingActions.length === 1 ? "decision is" : "decisions are" }} waiting for you
      </span>
      <span class="flex items-center gap-1">Review <AppIcon name="arrowRight" /></span>
    </RouterLink>

    <BaseCard :title="`Your money over the next ${horizon} days`" eyebrow="Forecast">
      <ForecastChart :lines="lines" />
    </BaseCard>

    <section v-if="findings.length" class="grid gap-3">
      <PageHeader eyebrow="Inbox Agent + Contract Agent" title="What I found" />
      <FindingCard v-for="f in findings" :key="f.id" :finding="f" />
    </section>

    <BaseCard eyebrow="How to read the labels" title="Who decides what">
      <AutonomyLegend detailed />
    </BaseCard>
  </template>
</template>
