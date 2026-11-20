<script setup lang="ts">
import { computed, ref } from "vue";
import type { Forecast } from "@/types/api";
import { eur, fmtDate, fmtDayMonth } from "@/utils/format";
import type { ChartLine } from "./chart";

/** Plain SVG – no chart library, nothing to break during the demo. Colours come from design tokens. */
const props = defineProps<{ lines: ChartLine[] }>();

const W = 800;
const H = 280;
const PAD = { top: 16, right: 16, bottom: 32, left: 72 };

const geo = computed(() => {
  const base = props.lines[0]?.forecast;
  if (!base || base.series.length < 2) return null;

  const values = props.lines.flatMap((l) => l.forecast.series.map((s) => s.balance));
  const buffer = base.buffer;
  const rawMin = Math.min(0, ...values, buffer);
  const rawMax = Math.max(...values, buffer);
  const span = rawMax - rawMin || 1;
  const min = rawMin;
  const max = rawMax + span * 0.05;
  const n = base.series.length;

  const x = (i: number) => PAD.left + (i / (n - 1)) * (W - PAD.left - PAD.right);
  const y = (v: number) => PAD.top + ((max - v) / (max - min)) * (H - PAD.top - PAD.bottom);
  const path = (f: Forecast) => f.series.map((s, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(s.balance).toFixed(1)}`).join(" ");

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => min + t * (max - min));
  const xTicks = [0, Math.round((n - 1) / 3), Math.round((2 * (n - 1)) / 3), n - 1];

  return { base, n, buffer, min, max, x, y, path, ticks, xTicks };
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
        class="block w-full min-w-[560px] touch-none select-none"
        role="img"
        :aria-label="`Cash forecast for ${geo.n} days. Lowest balance ${eur(lines[0].forecast.min_balance)} on ${fmtDate(lines[0].forecast.min_date)}.`"
        @pointermove="onMove"
        @pointerleave="hover = null"
      >
        <!-- grid + y labels -->
        <g v-for="t in geo.ticks" :key="t">
          <line :x1="PAD.left" :x2="W - PAD.right" :y1="geo.y(t)" :y2="geo.y(t)" class="stroke-grid" stroke-width="1" />
          <text :x="PAD.left - 8" :y="geo.y(t) + 4" text-anchor="end" class="fill-muted text-[11px] tabular-nums">{{ eur(t) }}</text>
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
        <text :x="W - PAD.right" :y="geo.y(geo.buffer) - 6" text-anchor="end" class="fill-negative text-[11px] font-semibold">
          Safety cushion {{ eur(geo.buffer) }}
        </text>

        <!-- x labels -->
        <text
          v-for="i in geo.xTicks" :key="i"
          :x="geo.x(i)" :y="H - 10"
          :text-anchor="i === 0 ? 'start' : i === geo.n - 1 ? 'end' : 'middle'"
          class="fill-muted text-[11px]"
        >{{ fmtDayMonth(geo.base.series[i].date) }}</text>

        <!-- scenario lines -->
        <path
          v-for="l in lines" :key="l.label"
          :d="geo.path(l.forecast)"
          fill="none" :class="STROKE[l.tone]" stroke-width="2.5" stroke-linejoin="round"
          :stroke-dasharray="l.tone === 'risk' ? '6 5' : undefined"
        />

        <!-- lowest point markers -->
        <g v-for="l in lines" :key="`min-${l.label}`">
          <circle
            :cx="geo.x(l.forecast.series.findIndex((s) => s.date === l.forecast.min_date))"
            :cy="geo.y(l.forecast.min_balance)"
            r="4.5" :class="FILL[l.tone]" class="stroke-surface" stroke-width="2"
          />
        </g>

        <!-- hover -->
        <g v-if="hover !== null">
          <line :x1="geo.x(hover)" :x2="geo.x(hover)" :y1="PAD.top" :y2="H - PAD.bottom" class="stroke-muted" stroke-width="1" opacity="0.5" />
          <circle
            v-for="l in lines" :key="`h-${l.label}`"
            :cx="geo.x(hover)" :cy="geo.y(l.forecast.series[hover].balance)" r="4" :class="FILL[l.tone]"
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
          {{ l.label }} – lowest <b class="tabular-nums">{{ eur(l.forecast.min_balance) }}</b>
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
