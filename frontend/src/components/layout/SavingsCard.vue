<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { monotonePath } from "@/components/dashboard/chart";
import { savingsForPeriod, savingsStatus, type SavingsStatus } from "@/components/dashboard/savings";
import AnimatedNumber from "@/components/ui/AnimatedNumber.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import CollapseTransition from "@/components/ui/CollapseTransition.vue";
import { periodLabel } from "@/composables/useForecastPeriod";
import { t } from "@/i18n";
import { useDashboardStore } from "@/stores/dashboard";
import type { Forecast } from "@/types/api";
import { eur, fmtDayMonth } from "@/utils/format";
import { prefersReducedMotion } from "@/utils/motion";

/**
 * Sidebar "Saved by Avida" card (on navy). ONE period for everything in it: the next 90 days, whatever period the
 * big chart shows – the amount, its label, the note ("Starts 5 Jan"), the waiting link and the mini chart.
 * Mini chart = the overview forecast chart over those 90 days:
 *   mint line + faint area = your money if you follow Avida (the big chart's main line)
 *   coral dashed line      = if you accept every price increase (appears after the inbox check, like on the big chart)
 * Calm by design: nothing blinks or pops in – after a check the line glides to its new shape; the hover dot glides
 * between days; the read-out below has its own fixed space, hovering only changes its words.
 */
const store = useDashboardStore();
const { dashboard } = storeToRefs(store);

/**
 * The card's one period: the next 90 days (= the whole forecast, "3 months" on the overview chart). Not 30: the first
 * saving usually starts weeks ahead (e.g. a price increase from 1 Jan), so a 30-day card stayed at 0 € right after
 * the owner approved – the demo's "Saved by Avida goes up" moment was invisible in the sidebar. 90 days matches the
 * overview's KPI card, so both show the same amount.
 */
const N = 90;

// --- "Saved by Avida" for these 90 days + what to say about it (same period, never a yearly figure) --------------
const period = computed(() => (dashboard.value ? savingsForPeriod(dashboard.value, N) : { saved: 0, waiting: 0 }));
const status = computed<SavingsStatus>(() => (dashboard.value ? savingsStatus(dashboard.value, N) : { kind: "unchecked" }));
const startsOn = (from: string | null) => (from ? t("Savings start on {date}", { date: fmtDayMonth(from) }) : t("Savings start later"));
const note = computed(() => {
  const s = status.value;
  if (s.kind === "later") return startsOn(s.from);
  if (s.kind === "none") return t("No savings found yet");
  if (s.kind === "unchecked") return t("Check your inbox to find savings");
  return "";
});
const waitingText = computed(() => {
  const s = status.value;
  if (s.kind !== "waiting") return "";
  if (s.amount > 0.5) return t("+{amount} waiting for your OK", { amount: eur(s.amount) });
  return s.from ? t("Waiting for your OK · starts {date}", { date: fmtDayMonth(s.from) }) : t("Waiting for your OK");
});

// --- data: the first 90 days of the same forecast the overview chart draws -------------------------------
const mainF = computed(() => dashboard.value?.scenarios.recommended ?? dashboard.value?.scenarios.current ?? null);
const riskF = computed(() => dashboard.value?.scenarios.if_accepted ?? null);
const dateAt = (k: number) => mainF.value?.series[k]?.date ?? null;
const balance = (f: Forecast | null, k: number) => f?.series[Math.min(k, f.series.length - 1)]?.balance ?? 0;

type Series = { main: number[]; risk: number[]; min: number; max: number; hasRisk: number };
const target = computed<Series>(() => {
  const main = Array.from({ length: N }, (_, k) => balance(mainF.value, k));
  const risk = riskF.value ? Array.from({ length: N }, (_, k) => balance(riskF.value, k)) : [...main];
  const lo = Math.min(...main, ...risk);
  const hi = Math.max(...main, ...risk);
  const pad = (hi - lo || 1) * 0.12;
  return { main, risk, min: lo - pad, max: hi + pad, hasRisk: riskF.value ? 1 : 0 };
});

const copy = (s: Series): Series => ({ ...s, main: [...s.main], risk: [...s.risk] });
const shown = ref<Series>(copy(target.value));
let frame = 0;
watch(target, (to, from) => {
  cancelAnimationFrame(frame);
  // first data (page load) is simply there; later changes (inbox check, reset) glide
  if (prefersReducedMotion() || !from || from.main.every((v) => v === 0)) {
    shown.value = copy(to);
    return;
  }
  const start = copy(shown.value);
  const t0 = performance.now();
  const mix = (a: number, b: number, e: number) => a + (b - a) * e;
  const step = (now: number) => {
    const e = 1 - Math.pow(1 - Math.min(1, (now - t0) / 600), 3);
    shown.value = {
      main: to.main.map((v, k) => mix(start.main[k], v, e)),
      risk: to.risk.map((v, k) => mix(start.risk[k], v, e)),
      min: mix(start.min, to.min, e),
      max: mix(start.max, to.max, e),
      hasRisk: mix(start.hasRisk, to.hasRisk, e),
    };
    if (e < 1) frame = requestAnimationFrame(step);
  };
  frame = requestAnimationFrame(step);
});
onBeforeUnmount(() => cancelAnimationFrame(frame));

// --- geometry (the sidebar has a fixed width → a fixed viewBox, drawn 1:1) ----------------------------------
const W = 178;
const H = 60;
const PAD = { x: 5, top: 6, bottom: 4 };
const sx = (k: number) => PAD.x + (k * (W - 2 * PAD.x)) / (N - 1);
const sy = (v: number) =>
  PAD.top + ((shown.value.max - v) / (shown.value.max - shown.value.min || 1)) * (H - PAD.top - PAD.bottom);
const pathOf = (vals: number[]) => monotonePath(vals.map((v, k) => [sx(k), sy(v)] as const));
const mainPath = computed(() => pathOf(shown.value.main));
const mainArea = computed(() => `${mainPath.value}L${sx(N - 1)},${H - PAD.bottom}L${sx(0)},${H - PAD.bottom}Z`);
const riskPath = computed(() => pathOf(shown.value.risk));

// --- hover / tap: a day of the period (default: the last one) ------------------------------------------------
const svgEl = ref<SVGSVGElement | null>(null);
const hover = ref<number | null>(null);
const focusK = computed(() => hover.value ?? N - 1);
function onMove(e: PointerEvent) {
  const r = svgEl.value?.getBoundingClientRect();
  if (!r) return;
  const x = ((e.clientX - r.left) / (r.width || 1)) * W;
  hover.value = Math.min(N - 1, Math.max(0, Math.round(((x - PAD.x) / (W - 2 * PAD.x)) * (N - 1))));
}

const read = computed(() => {
  const k = focusK.value;
  const value = target.value.main[k] ?? 0;
  const gain = riskF.value ? Math.max(0, value - (target.value.risk[k] ?? value)) : 0;
  return { date: k === 0 ? t("Today") : fmtDayMonth(dateAt(k)), value, gain };
});
const summary = computed(() =>
  t("Your money on {date}: {amount}.", { amount: eur(target.value.main[N - 1] ?? 0), date: fmtDayMonth(dateAt(N - 1)) }),
);
</script>

<template>
  <div class="grid gap-3 rounded-xl border border-white/10 bg-white/5 p-3.5">
    <!-- ONE period for the whole card: the next 90 days (amount, its label, the note, the link and the chart) -->
    <div class="flex items-center gap-3">
      <!-- on-navy tile (IconTile tones are for light surfaces): same 40px sm size -->
      <span class="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-mint/15 text-mint" aria-hidden="true">
        <AppIcon name="piggyBank" :size="18" />
      </span>
      <span class="grid min-w-0 gap-0.5 leading-tight">
        <span class="text-label font-semibold text-white/90">{{ t("Saved by Avida") }}</span>
        <span class="text-caption text-white/75">{{ t("next {period}", { period: periodLabel(N) }) }}</span>
      </span>
    </div>

    <div class="grid gap-1">
      <AnimatedNumber :value="period.saved" class="font-display text-2xl font-semibold leading-none tracking-tight tabular-nums text-mint" />
      <!-- why the amount is what it is (only when it needs explaining) -->
      <CollapseTransition>
        <span v-if="note" class="block pt-1 text-caption text-white/75">{{ note }}</span>
      </CollapseTransition>
    </div>

    <!-- mini forecast: the overview chart over the same 90 days -->
    <div class="grid gap-1">
      <span class="text-caption text-white/75">{{ t("Your money") }}</span>
      <svg
        ref="svgEl"
        :viewBox="`0 0 ${W} ${H}`"
        class="block w-full cursor-crosshair overflow-visible [touch-action:pan-y]"
        role="img"
        :aria-label="summary"
        @pointermove="onMove"
        @pointerdown="onMove"
        @pointerleave="hover = null"
      >
        <path :d="mainArea" class="fill-mint" fill-opacity="0.1" />
        <path
          :d="riskPath" fill="none" class="stroke-chart-alt" stroke-width="1.5" stroke-dasharray="4 3" stroke-linecap="round"
          :opacity="shown.hasRisk * 0.85"
        />
        <path :d="mainPath" fill="none" class="stroke-mint" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
        <!-- hover guide + the day in focus (always there → never pops in, it glides) -->
        <line
          x1="0" x2="0" :y1="PAD.top - 2" :y2="H - PAD.bottom"
          class="stroke-white/40 transition-[transform,opacity] duration-fast" stroke-width="1" stroke-dasharray="2 2"
          :style="{ transform: `translateX(${sx(focusK)}px)` }" :opacity="hover !== null ? 1 : 0"
        />
        <circle
          cx="0" cy="0" r="3.5" stroke-width="2" class="fill-mint stroke-side transition-transform duration-fast"
          :style="{ transform: `translate(${sx(focusK)}px, ${sy(shown.main[focusK] ?? 0)}px)` }"
        />
      </svg>
      <div class="flex justify-between text-caption tabular-nums text-white/75" aria-hidden="true">
        <span>{{ t("Today") }}</span>
        <span>{{ fmtDayMonth(dateAt(N - 1)) }}</span>
      </div>
    </div>

    <!-- read-out: fixed two-line space (hovering only changes the words, nothing moves) -->
    <div class="grid h-[2.6rem] content-start leading-tight" aria-live="polite">
      <span class="text-caption text-white/75">{{ read.date }}</span>
      <span class="flex items-baseline gap-x-1.5 whitespace-nowrap">
        <b class="font-display text-base font-semibold tabular-nums text-white">{{ eur(read.value) }}</b>
        <!-- what following Avida adds on that day (space kept, fades in/out) -->
        <span
          :class="['text-caption tabular-nums text-mint/80 transition-opacity duration-fast', read.gain > 0.5 ? '' : 'opacity-0']"
          :aria-hidden="read.gain > 0.5 ? undefined : 'true'"
        >+{{ eur(read.gain) }}</span>
      </span>
    </div>

    <!-- money that is one click away (collapses smoothly once approved) -->
    <CollapseTransition>
      <div v-if="status.kind === 'waiting'">
        <RouterLink
          :to="{ name: 'decisions' }"
          class="-mx-1.5 flex items-center gap-2 rounded-lg px-1.5 py-1 text-caption text-white/90 hover:bg-white/10"
        >
          <AppIcon name="clock" :size="14" class="shrink-0 text-white/75" />
          <span class="min-w-0 flex-1">{{ waitingText }}</span>
          <AppIcon name="chevronRight" :size="14" class="shrink-0 text-white/75" />
        </RouterLink>
      </div>
    </CollapseTransition>
  </div>
</template>
