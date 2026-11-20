<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import AskLauncher from "@/components/ask/AskLauncher.vue";
import ForecastChart from "@/components/dashboard/ForecastChart.vue";
import KpiCard from "@/components/dashboard/KpiCard.vue";
import PaymentsDonut from "@/components/dashboard/PaymentsDonut.vue";
import PeriodPicker from "@/components/dashboard/PeriodPicker.vue";
import { scenarioLines } from "@/components/dashboard/chart";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { periodLabel, useForecastPeriod } from "@/composables/useForecastPeriod";
import { t } from "@/i18n";
import { useDashboardStore } from "@/stores/dashboard";
import { fmtDate } from "@/utils/format";

/**
 * Start screen – deliberately short, one question per row:
 *   how am I doing (4 KPIs) → where is my money going (forecast + biggest payments).
 * Decisions and findings live in the Action center (the nav tab pulses while something waits);
 * the inbox check lives in the top bar; "Ask your CFO" is the floating chat bubble (AskLauncher).
 */
const store = useDashboardStore();
const { dashboard, kpis, loading, error } = storeToRefs(store);

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
</script>

<template>
  <AlertBanner v-if="error" dismissible @dismiss="error = null">
    {{ error }}
    <button type="button" class="ml-2 underline" @click="store.load(true)">{{ t("Try again") }}</button>
  </AlertBanner>

  <!-- loading: same shapes as the real content, so nothing jumps when it arrives -->
  <template v-if="!dashboard && loading">
    <div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,9.5rem),1fr))] gap-3">
      <SkeletonBlock v-for="i in 4" :key="i" height="h-32" />
    </div>
    <div class="grid gap-5 lg:grid-cols-3">
      <SkeletonBlock height="h-96" class="lg:col-span-2" />
      <SkeletonBlock height="h-96" />
    </div>
  </template>

  <template v-else-if="dashboard && kpis">
    <!-- 1. how am I doing: green = good for you, red = needs attention.
         auto-fit with a rem minimum: 4 → 2 columns by width, and 1 column on phones at large text sizes -->
    <section class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,9.5rem),1fr))] gap-3" :aria-label="t('Key figures')">
      <KpiCard icon="wallet" :label="t('In the bank today')" :amount="kpis.balance_today" />
      <KpiCard
        icon="trendingDown"
        :label="t('Lowest balance ahead')"
        :amount="kpis.min_balance"
        :sub="fmtDate(kpis.min_date)"
        :tone="lowIsBad ? 'negative' : 'positive'"
        :delta="lowIsBad ? { text: t('below cushion'), tone: 'negative' } : { text: t('above cushion'), tone: 'positive' }"
      />
      <KpiCard icon="shield" :label="t('Your safety cushion')" :amount="kpis.safety_buffer" :sub="t('minimum to keep')" />
      <KpiCard
        icon="piggyBank"
        :label="t('Saved by Avida')"
        :amount="kpis.saved_liquidity"
        :sub="t('next 12 months')"
        :tone="kpis.saved_liquidity > 0 ? 'positive' : 'neutral'"
      />
    </section>

    <!-- 2. where is my money going -->
    <div class="grid gap-5 lg:grid-cols-3">
      <BaseCard
        class="lg:col-span-2"
        :title="t('Your money, next {period}', { period: periodLabel(shownDays) })"
        :eyebrow="t('Forecast')"
      >
        <template #actions>
          <PeriodPicker v-model="requestedDays" :max="horizon" />
        </template>
        <ForecastChart :lines="lines" :days="shownDays" />
      </BaseCard>
      <BaseCard :title="t('Biggest payments ahead')" :eyebrow="t('Next {period}', { period: periodLabel(shownDays) })">
        <PaymentsDonut :outflows="outflowsInPeriod" :period-label="periodLabel(shownDays)" />
      </BaseCard>
    </div>
  </template>

  <!-- floating "Ask your CFO" chat bubble (teleported to <body>; this is only its bottom spacer) -->
  <AskLauncher />
</template>
