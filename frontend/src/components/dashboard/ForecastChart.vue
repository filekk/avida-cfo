<script setup lang="ts">
import { computed, ref, useId } from "vue";
import type { Forecast } from "@/types/api";
import { eur, fmtDate, fmtDayMonth } from "@/utils/format";
import type { ChartLine } from "./chart";

/**
 * Plain SVG – no chart library, nothing to break during the demo. Colours come from design tokens.
 * Area gradient under the main line + a call-out on its lowest point, so the key number needs no sentence.
 */
const props = defineProps<{ lines: ChartLine[] }>();

const W = 720;
const H = 290;
const PAD = { top: 20, right: 16, bottom: 32, left: 70 };
const gradId = `fc-grad-${useId()}`;

const geo = computed(() => {
  const base = props.lines[0]?.forecast;
  if (!base || base.series.length < 2) return null;

  const values = props.lines.flatMap((l) => l.forecast.series.map((s) => s.balance));
  const buffer = base.buffer;
  const rawMin = Math.min(0, ...values, buffer);
  const rawMax = Math.max(...values, buffer);
  const span = rawMax - rawMin || 1;
  const min = rawMin;
  const max = rawMax + span * 0.08;
  const n = base.series.length;

  const x = (i: number) => PAD.left + (i / (n - 1)) * (W - PAD.left - PAD.right);
  const y = (v: number) => PAD.top + ((max - v) / (max - min)) * (H - PAD.top - PAD.bottom);
  const path = (f: Forecast) => f.series.map((s, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(s.balance).toFixed(1)}`).join(" ");
  const area = (f: Forecast) => `${path(f)} L${x(n - 1).toFixed(1)},${y(min).toFixed(1)} L${x(0).toFixed(1)},${y(min).toFixed(1)} Z`;

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => min + t * (max - min));
  const xTicks = [0, Math.round((n - 1) / 3), Math.round((2 * (n - 1)) / 3), n - 1];

  return { base, n, buffer, min, max, x, y, path, area, ticks, xTicks };
});

const minIndex = (f: Forecast) => Math.max(0, f.series.findIndex((s) => s.date === f.min_date));

/** Call-out box for the lowest point of the main (last = recommended/current) line. */
const CALLOUT = { w: 128, h: 42 };
const callout = computed(() => {
  const g = geo.value;
  const main = props.lines[props.lines.length - 1];
  if (!g || !main) return null;
  const f = main.forecast;
  const px = g.x(minIndex(f));
  const py = g.y(f.min_balance);
  const bx = Math.min(W - PAD.right - CALLOUT.w, Math.max(PAD.left + 4, px - CALLOUT.w / 2));
  const above = py - CALLOUT.h - 14 > PAD.top;
  const by = above ? py - CALLOUT.h - 14 : py + 14;
  return { px, py, bx, by, value: eur(f.min_balance), date: fmtDayMonth(f.min_date) };
});

// --- hover read-out ------------------------------------------------------------------------------
const hover = ref<number | null>(null);
const svgEl = ref<SVGSVGElement | null>(null);

function onMove(ev: PointerEvent) {
  const g = geo.value;
  if (!g || !svgEl.value) return;
  const rect = svgEl.value.getBoundingClientRect();
  const sx = ((ev.clientX - rect.left) / rect.width) * W;
  const i = Math.round(((sx - PAD.left) / (W - PAD.left - PAD.right)) * (g.n - 1));
  hover.value = Math.max(0, Math.min(g.n - 1, i));
}

const STROKE = { primary: "stroke-chart-line", risk: "stroke-chart-alt" };
const FILL = { primary: "fill-chart-line", risk: "fill-chart-alt" };
</script>

<template>
  <div v-if="geo" class="grid gap-3">
    <div class="overflow-x-auto">
      <svg
        ref="svgEl"
        :viewBox="`0 0 ${W} ${H}`"
        class="block w-full min-w-[540px] touch-none select-none"
        role="img"
        :aria-label="`Cash forecast for ${geo.n} days. Lowest balance ${eur(lines[lines.length - 1].forecast.min_balance)} on ${fmtDate(lines[lines.length - 1].forecast.min_date)}.`"
        @pointermove="onMove"
        @pointerleave="hover = null"
      >
        <defs>
          <linearGradient :id="gradId" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" style="stop-color: rgb(var(--c-chart-line)); stop-opacity: 0.26" />
            <stop offset="100%" style="stop-color: rgb(var(--c-chart-line)); stop-opacity: 0" />
          </linearGradient>
        </defs>

        <!-- grid + y labels -->
        <g v-for="t in geo.ticks" :key="t">
          <line :x1="PAD.left" :x2="W - PAD.right" :y1="geo.y(t)" :y2="geo.y(t)" class="stroke-grid" stroke-width="1" />
          <text :x="PAD.left - 10" :y="geo.y(t) + 4" text-anchor="end" class="fill-muted text-[12px] tabular-nums">{{ eur(t) }}</text>
        </g>

        <!-- danger zone below the safety cushion -->
        <rect
          :x="PAD.left"
          :y="geo.y(geo.buffer)"
          :width="W - PAD.left - PAD.right"
          :height="Math.max(0, geo.y(geo.min) - geo.y(geo.buffer))"
          class="fill-negative-soft"
          opacity="0.7"
        />
        <line
          :x1="PAD.left" :x2="W - PAD.right" :y1="geo.y(geo.buffer)" :y2="geo.y(geo.buffer)"
          class="stroke-negative" stroke-dasharray="6 4" stroke-width="1.5"
        />
        <text :x="PAD.left + 8" :y="geo.y(geo.buffer) - 7" class="fill-negative text-[12px] font-semibold">
          Safety cushion {{ eur(geo.buffer) }}
        </text>

        <!-- x labels -->
        <text
          v-for="i in geo.xTicks" :key="i"
          :x="geo.x(i)" :y="H - 10"
          :text-anchor="i === 0 ? 'start' : i === geo.n - 1 ? 'end' : 'middle'"
          class="fill-muted text-[12px]"
        >{{ i === 0 ? "Today" : fmtDayMonth(geo.base.series[i].date) }}</text>

        <!-- area under the main line -->
        <path
          v-for="l in lines.filter((l) => l.tone === 'primary')" :key="`a-${l.label}`"
          :d="geo.area(l.forecast)" :fill="`url(#${gradId})`"
        />

        <!-- scenario lines -->
        <path
          v-for="l in lines" :key="l.label"
          :d="geo.path(l.forecast)"
          fill="none" :class="STROKE[l.tone]" stroke-width="2.5" stroke-linejoin="round"
          :stroke-dasharray="l.tone === 'risk' ? '6 5' : undefined"
        />

        <!-- today + lowest point markers -->
        <circle :cx="geo.x(0)" :cy="geo.y(geo.base.series[0].balance)" r="5" class="fill-chart-line stroke-surface" stroke-width="2.5" />
        <circle
          v-for="l in lines" :key="`min-${l.label}`"
          :cx="geo.x(minIndex(l.forecast))"
          :cy="geo.y(l.forecast.min_balance)"
          r="5.5" :class="FILL[l.tone]" class="stroke-surface" stroke-width="2.5"
        />

        <!-- call-out: lowest point of the main line -->
        <g v-if="callout && hover === null" aria-hidden="true">
          <rect :x="callout.bx" :y="callout.by" :width="CALLOUT.w" :height="CALLOUT.h" rx="8" class="fill-surface stroke-line" stroke-width="1" />
          <text :x="callout.bx + 12" :y="callout.by + 16" class="fill-muted text-[11px]">Lowest · {{ callout.date }}</text>
          <text :x="callout.bx + 12" :y="callout.by + 33" class="fill-fg font-display text-[15px] font-bold tabular-nums">{{ callout.value }}</text>
        </g>

        <!-- hover -->
        <g v-if="hover !== null">
          <line :x1="geo.x(hover)" :x2="geo.x(hover)" :y1="PAD.top" :y2="H - PAD.bottom" class="stroke-muted" stroke-width="1" opacity="0.5" />
          <circle
            v-for="l in lines" :key="`h-${l.label}`"
            :cx="geo.x(hover)" :cy="geo.y(l.forecast.series[hover].balance)" r="4.5" :class="FILL[l.tone]"
          />
        </g>
      </svg>
    </div>

    <div class="flex flex-wrap items-center justify-between gap-3 text-sm">
      <div class="flex flex-wrap gap-x-5 gap-y-1">
        <span v-for="l in lines" :key="l.label" class="flex items-center gap-2">
          <svg width="22" height="6" aria-hidden="true">
            <line x1="0" x2="22" y1="3" y2="3" :class="STROKE[l.tone]" stroke-width="2.5" :stroke-dasharray="l.tone === 'risk' ? '5 4' : undefined" />
          </svg>
          <span>{{ l.label }} <span class="text-muted">· lowest</span> <b class="tabular-nums">{{ eur(l.forecast.min_balance) }}</b></span>
        </span>
      </div>
      <span v-if="hover !== null" class="tabular-nums text-muted">
        {{ fmtDate(geo.base.series[hover].date) }}:
        <template v-for="(l, idx) in lines" :key="`v-${l.label}`">
          <b class="text-fg">{{ eur(l.forecast.series[hover].balance) }}</b><template v-if="idx < lines.length - 1"> · </template>
        </template>
      </span>
    </div>
  </div>
</template>
