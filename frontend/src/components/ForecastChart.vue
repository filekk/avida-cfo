<script setup lang="ts">
import { computed } from "vue";
import { eur, fmtDate } from "../api";
import type { Forecast } from "../types";

export interface ChartLine {
  f: Forecast;
  color: string;
  label: string;
  dashed?: boolean;
}

// Plain SVG – no chart library, nothing to break during the demo.
const props = defineProps<{ lines: ChartLine[] }>();

const W = 800, H = 260, P = 48;

const geo = computed(() => {
  const all = props.lines.flatMap((l) => l.f.series.map((s) => s.balance));
  const buffer = props.lines[0].f.buffer;
  const min = Math.min(0, ...all, buffer);
  const max = Math.max(...all, buffer);
  const n = props.lines[0].f.series.length;
  const x = (i: number) => P + (i / (n - 1)) * (W - 2 * P);
  const y = (v: number) => H - P + ((min - v) / (max - min)) * (H - 2 * P);
  const path = (f: Forecast) =>
    f.series.map((s, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(s.balance).toFixed(1)}`).join(" ");
  return {
    buffer, min, max, y, path,
    first: props.lines[0].f.series[0].date,
    last: props.lines[0].f.series[n - 1].date,
  };
});
</script>

<template>
  <div class="overflow-x-auto">
    <svg :viewBox="`0 0 ${W} ${H}`" class="w-full min-w-[520px]" role="img" aria-label="Cash forecast">
      <rect
        :x="P" :y="geo.y(geo.buffer)" :width="W - 2 * P"
        :height="Math.max(0, geo.y(geo.min) - geo.y(geo.buffer))"
        fill="#fee2e2" opacity="0.6"
      />
      <line :x1="P" :x2="W - P" :y1="geo.y(geo.buffer)" :y2="geo.y(geo.buffer)" stroke="#ef4444" stroke-dasharray="6 4" />
      <text :x="W - P" :y="geo.y(geo.buffer) - 6" text-anchor="end" font-size="12" fill="#b91c1c">
        Safety cushion {{ eur(geo.buffer) }}
      </text>
      <path
        v-for="l in lines" :key="l.label" :d="geo.path(l.f)"
        fill="none" :stroke="l.color" stroke-width="2.5" :stroke-dasharray="l.dashed ? '5 5' : undefined"
      />
      <text :x="P" :y="H - 16" font-size="12" fill="#64748b">{{ fmtDate(geo.first) }}</text>
      <text :x="W - P" :y="H - 16" font-size="12" fill="#64748b" text-anchor="end">{{ fmtDate(geo.last) }}</text>
      <text :x="P - 6" :y="geo.y(geo.max)" font-size="12" fill="#64748b" text-anchor="end">{{ eur(geo.max) }}</text>
      <text :x="P - 6" :y="geo.y(geo.min)" font-size="12" fill="#64748b" text-anchor="end">{{ eur(geo.min) }}</text>
    </svg>
    <div class="mt-2 flex flex-wrap gap-4 text-sm">
      <span v-for="l in lines" :key="l.label" class="flex items-center gap-2">
        <span class="inline-block h-1 w-6 rounded" :style="{ background: l.color }" />
        {{ l.label }} – lowest {{ eur(l.f.min_balance) }}
      </span>
    </div>
  </div>
</template>
