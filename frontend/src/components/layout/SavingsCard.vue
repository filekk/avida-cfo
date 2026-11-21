<script setup lang="ts">
import { computed, ref } from "vue";
import { storeToRefs } from "pinia";
import { monthlyBuildUp, pendingSavings12m } from "@/components/dashboard/savings";
import AnimatedNumber from "@/components/ui/AnimatedNumber.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { t } from "@/i18n";
import { useDashboardStore } from "@/stores/dashboard";
import { eur, fmtMonth, fmtMonthYear } from "@/utils/format";

/**
 * Sidebar "Saved by Avida" card with a small savings chart (on navy).
 *
 * The 12-month total builds up month by month → 12 rising bars, like a jar filling up:
 *   mint bars       = saved (you approved it)
 *   pale mint       = could be saved – waiting for your OK (link to the Action center)
 *   faint outlines  = nothing found yet (before the first inbox check)
 * Hover / tap a month → "By March 2027: 4.410 €". Bars grow with a short left-to-right sweep when the amount
 * changes (e.g. right after an approval) – a response, nothing moves at rest.
 */
const store = useDashboardStore();
const { dashboard, kpis, actions, hasSynced } = storeToRefs(store);

const saved = computed(() => kpis.value?.saved_liquidity ?? 0);
const waiting = computed(() => pendingSavings12m(actions.value));
const empty = computed(() => saved.value + waiting.value <= 0);
const start = computed(() => dashboard.value?.scenarios.current.series[0]?.date ?? new Date().toISOString().slice(0, 10));

const bars = computed(() => {
  const scale = Math.max(1, saved.value + waiting.value);
  const s = monthlyBuildUp(saved.value, start.value);
  const w = monthlyBuildUp(waiting.value, start.value);
  return s.map((b, k) => ({
    month: b.month,
    saved: b.value,
    waiting: w[k].value,
    savedH: (b.value / scale) * 100,
    waitingH: (w[k].value / scale) * 100,
    ghostH: ((k + 1) / 12) * 100,
  }));
});

const active = ref<number | null>(null);
const readout = computed(() => {
  if (empty.value) return hasSynced.value ? t("No savings found yet") : t("Check your inbox to find savings");
  const b = active.value === null ? null : bars.value[active.value];
  if (b) {
    const line = t("By {month}: {amount}", { month: fmtMonthYear(b.month), amount: eur(b.saved) });
    return b.waiting > 0 ? `${line} (+${eur(b.waiting)})` : line;
  }
  return saved.value > 0 ? t("about {amount} a month", { amount: eur(saved.value / 12) }) : t("Approve to start saving");
});

const summary = computed(() =>
  t("Savings chart, next 12 months: {saved} saved, {waiting} waiting for your OK.", {
    saved: eur(saved.value),
    waiting: eur(waiting.value),
  }),
);
</script>

<template>
  <div class="grid gap-3 rounded-xl border border-white/10 bg-white/5 p-3.5">
    <div class="flex items-center gap-3">
      <!-- on-navy tile (IconTile tones are for light surfaces): same 40px sm size -->
      <span class="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-mint/15 text-mint" aria-hidden="true">
        <AppIcon name="piggyBank" :size="18" />
      </span>
      <span class="grid min-w-0 gap-0.5 leading-tight">
        <span class="text-label font-semibold text-white/90">{{ t("Saved by Avida") }}</span>
        <span class="text-caption text-white/75">{{ t("next 12 months") }}</span>
      </span>
    </div>

    <AnimatedNumber :value="saved" class="font-display text-2xl font-semibold leading-none tracking-tight tabular-nums text-mint" />

    <!-- the chart: 12 months, cumulative -->
    <div class="grid gap-1.5">
      <div class="flex h-16 items-end gap-[3px]" role="img" :aria-label="summary" @pointerleave="active = null">
        <div
          v-for="(b, k) in bars"
          :key="b.month"
          :class="[
            'relative flex h-full flex-1 cursor-default flex-col justify-end transition-opacity duration-fast',
            active !== null && active !== k ? 'opacity-50' : '',
          ]"
          aria-hidden="true"
          @pointerenter="active = k"
          @click="active = k"
        >
          <!-- nothing yet: faint outline of what a year of savings could look like -->
          <span
            v-if="empty"
            class="w-full border border-white/15 transition-[height] duration-slow"
            :style="{ height: `${b.ghostH}%`, transitionDelay: `${k * 25}ms` }"
          />
          <template v-else>
            <span
              class="w-full bg-mint/25 transition-[height,opacity] duration-slow"
              :style="{ height: `${b.waitingH}%`, opacity: b.waiting > 0 ? 1 : 0, transitionDelay: `${k * 25}ms` }"
            />
            <span
              class="w-full bg-mint transition-[height] duration-slow"
              :style="{ height: `${b.savedH}%`, transitionDelay: `${k * 25}ms` }"
            />
          </template>
        </div>
      </div>
      <div class="flex justify-between text-caption text-white/75" aria-hidden="true">
        <span>{{ fmtMonth(bars[0]?.month) }}</span>
        <span>{{ fmtMonth(bars[bars.length - 1]?.month) }}</span>
      </div>
    </div>

    <p class="min-h-[1.25rem] text-caption leading-snug text-white/90" aria-live="polite">{{ readout }}</p>

    <!-- money that is one click away -->
    <RouterLink
      v-if="waiting > 0"
      :to="{ name: 'decisions' }"
      class="-mx-1.5 -mb-1 flex items-center gap-2 rounded-lg px-1.5 py-1 text-caption text-white/90 hover:bg-white/10"
    >
      <span class="h-3 w-3 shrink-0 bg-mint/25" aria-hidden="true" />
      <span class="min-w-0 flex-1">{{ t("+{amount} waiting for your OK", { amount: eur(waiting) }) }}</span>
      <AppIcon name="chevronRight" :size="14" class="shrink-0 text-white/75" />
    </RouterLink>
  </div>
</template>
