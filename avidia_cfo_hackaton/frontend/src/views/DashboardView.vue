<script setup lang="ts">
import { computed, ref, type ComponentPublicInstance } from "vue";
import { storeToRefs } from "pinia";
import AskLauncher from "@/components/ask/AskLauncher.vue";
import ForecastChart from "@/components/dashboard/ForecastChart.vue";
import KpiCard from "@/components/dashboard/KpiCard.vue";
import PaymentsDonut from "@/components/dashboard/PaymentsDonut.vue";
import PeriodPicker from "@/components/dashboard/PeriodPicker.vue";
import { scenarioLines } from "@/components/dashboard/chart";
import { savingsForPeriod, savingsStatus, type SavingsStatus } from "@/components/dashboard/savings";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import type { IconName } from "@/components/ui/icons";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { periodLabel, useForecastPeriod } from "@/composables/useForecastPeriod";
import { t } from "@/i18n";
import { useDashboardStore } from "@/stores/dashboard";
import { eur, fmtDate, fmtDayMonth } from "@/utils/format";
import { prefersReducedMotion } from "@/utils/motion";

/**
 * Start screen – deliberately short, one question per row:
 *   how am I doing (4 KPIs) → where is my money going (forecast + biggest payments).
 * Decisions and findings live in the Action center (the nav tab shows a count while something waits);
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

// --- "Saved by Avida" follows the chart period (7 days … 12 months) ---------------------------------
const savings = computed(() => (dashboard.value ? savingsForPeriod(dashboard.value, shownDays.value) : { saved: 0, waiting: 0 }));
/** The coloured box under the amount: what to do next – always for the SAME period as the amount above it. */
const savingsPill = computed<{ tone: "positive" | "warn" | "neutral"; icon: IconName; text: string }>(() => {
  const s: SavingsStatus = dashboard.value ? savingsStatus(dashboard.value, shownDays.value) : { kind: "unchecked" };
  switch (s.kind) {
    case "waiting":
      return {
        tone: "warn",
        icon: "clock",
        text:
          s.amount > 0.5
            ? t("+{amount} if you approve", { amount: eur(s.amount) })
            : s.from
              ? t("Waiting for your OK · starts {date}", { date: fmtDayMonth(s.from) })
              : t("Waiting for your OK"),
      };
    case "approved":
      return { tone: "positive", icon: "check", text: t("Approved by you") };
    case "later":
      return {
        tone: "positive",
        icon: "calendar",
        text: s.from ? t("Savings start on {date}", { date: fmtDayMonth(s.from) }) : t("Savings start later"),
      };
    case "none":
      return { tone: "neutral", icon: "check", text: t("No savings found yet") };
    default:
      return { tone: "neutral", icon: "inbox", text: t("Check your inbox to find savings") };
  }
});

/** The period chip: jumps to the period picker of the chart (same period, change it there). */
const forecastCard = ref<ComponentPublicInstance | null>(null);
function goToPeriod() {
  const el = forecastCard.value?.$el as HTMLElement | undefined;
  if (!el) return;
  el.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "nearest" });
  el.querySelector<HTMLElement>('[role="group"] [aria-pressed="true"]')?.focus({ preventScroll: true });
}
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
      <!-- follows the chart: "next 90 days" ↔ "next 12 months" – the chip leads to the period picker -->
      <KpiCard
        icon="piggyBank"
        :label="t('Saved by Avida')"
        :amount="savings.saved"
        :tone="savings.saved > 0.5 ? 'positive' : 'neutral'"
        :delta="savingsPill"
      >
        <template #sub>
          <button
            type="button"
            class="-ml-1 inline-flex w-fit items-center gap-1.5 rounded-md px-1 py-0.5 text-label text-muted transition-colors duration-fast hover:bg-input hover:text-fg"
            :title="t('Same period as the chart – change it there')"
            @click="goToPeriod"
          >
            <AppIcon name="calendar" :size="14" class="shrink-0" />
            <Transition name="fade" mode="out-in">
              <span :key="shownDays" class="border-b border-dashed border-muted/60">
                {{ t("next {period}", { period: periodLabel(shownDays) }) }}
              </span>
            </Transition>
          </button>
        </template>
      </KpiCard>
    </section>

    <!-- 2. where is my money going -->
    <div class="grid gap-5 lg:grid-cols-3">
      <BaseCard
        ref="forecastCard"
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
