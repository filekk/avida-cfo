<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import ForecastChart from "@/components/dashboard/ForecastChart.vue";
import HeadlineBanner from "@/components/dashboard/HeadlineBanner.vue";
import KpiCard from "@/components/dashboard/KpiCard.vue";
import PaymentsDonut from "@/components/dashboard/PaymentsDonut.vue";
import PeriodPicker from "@/components/dashboard/PeriodPicker.vue";
import { scenarioLines } from "@/components/dashboard/chart";
import { localHeadline } from "@/components/dashboard/headline";
import FindingCard from "@/components/findings/FindingCard.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import CollapseTransition from "@/components/ui/CollapseTransition.vue";
import IconTile from "@/components/ui/IconTile.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { periodLabel, useForecastPeriod } from "@/composables/useForecastPeriod";
import { locale, t, tn } from "@/i18n";
import { useDashboardStore } from "@/stores/dashboard";
import { fmtDate } from "@/utils/format";

/**
 * Start screen, top → bottom: how am I doing (headline + KPIs) → where is my money going (forecast + payments)
 * → what is waiting for me (decisions) → what Avida found. The inbox check itself lives in the top bar
 * (InboxCheck), so it can be started – and followed – from every page.
 */
const store = useDashboardStore();
const { dashboard, kpis, loading, error, findings, pendingActions, isSafe } = storeToRefs(store);

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

/** Backend sentence when it is already in the UI language (EN today, or when it echoes `lang`), else built here. */
const headline = computed(() => {
  const d = dashboard.value;
  if (!d || !mainForecast.value) return "";
  const backendLang = d.lang ?? "en";
  return backendLang === locale.value ? d.headline : localHeadline(mainForecast.value);
});
</script>

<template>
  <AlertBanner v-if="error" dismissible @dismiss="error = null">
    {{ error }}
    <button type="button" class="ml-2 underline" @click="store.load(true)">{{ t("Try again") }}</button>
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
    <HeadlineBanner :headline="headline" :safe="isSafe" :days-safe="kpis.days_safe" :horizon="horizon" />

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

    <!-- 3. what is waiting for the owner -->
    <CollapseTransition>
      <RouterLink
        v-if="pendingActions.length"
        :to="{ name: 'decisions' }"
        class="group flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sun bg-warn-soft px-5 py-4 font-semibold text-warn hover:shadow-lift"
      >
        <span class="flex items-center gap-3">
          <IconTile icon="approval" tone="accent" />
          {{ tn(pendingActions.length, "1 decision is waiting for you", "{n} decisions are waiting for you") }}
        </span>
        <span class="flex items-center gap-1.5">
          {{ t("Review") }} <AppIcon name="arrowRight" :size="18" class="transition-transform group-hover:translate-x-1" />
        </span>
      </RouterLink>
    </CollapseTransition>

    <!-- 4. what it found – half-width cards read better than full-width bands -->
    <section v-if="findings.length" class="grid gap-3">
      <PageHeader :eyebrow="t('From your inbox')" :title="t('What I found')" />
      <div class="grid gap-4 md:grid-cols-2">
        <FindingCard v-for="f in findings" :key="f.id" :finding="f" />
      </div>
    </section>
  </template>
</template>
