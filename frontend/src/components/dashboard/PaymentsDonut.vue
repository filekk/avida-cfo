<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import IconTile from "@/components/ui/IconTile.vue";
import type { Outflow } from "@/types/api";
import { eur, fmtDayMonth, pct } from "@/utils/format";
import { prefersReducedMotion as reducedMotion } from "@/utils/motion";
import { categoryIcon } from "./chart";
import { groupPayments, SLICES } from "./payments";

/**
 * "Biggest payments ahead" as a donut. At rest: total in the centre + a short legend.
 * Hover / focus / tap a slice or a legend row → the slice pushes out, the others dim, the centre crossfades
 * to that payment (amount, share, count) and the row shows its dates. Everything fades/slides – fixed
 * layers in fixed boxes, so nothing changes size and nothing jumps.
 * `outflows` are already limited to the chosen period by the view (amounts arrive negative).
 */
const props = defineProps<{ outflows: Outflow[]; periodLabel: string }>();

const groups = computed(() => groupPayments(props.outflows));
const total = computed(() => groups.value.reduce((s, g) => s + g.total, 0));
const count = computed(() => props.outflows.length);

// --- geometry (viewBox units) -----------------------------------------------------------------
const SIZE = 220;
const MID = SIZE / 2;
const R = 84;
const W = 20;
const W_ACTIVE = 27;
const CIRC = 2 * Math.PI * R;
const GAP = 3; // surface-coloured gap between slices
const PUSH = 5; // active slice moves outward

interface Arc {
  key: string;
  start: number; // 0..1, clockwise from 12 o'clock
  len: number; // 0..1
  color: number;
}
const target = computed<Arc[]>(() => {
  let acc = 0;
  return groups.value.map((g, i) => {
    const a = { key: g.key, start: acc, len: g.share, color: i % SLICES.length };
    acc += g.share;
    return a;
  });
});

// Arcs on screen: tweened in JS (sweep on first draw, morph when the period changes).
const shown = ref<Arc[]>([]);
let frame = 0;
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

function tweenTo(to: Arc[]) {
  cancelAnimationFrame(frame);
  if (reducedMotion()) {
    shown.value = to;
    return;
  }
  const first = shown.value.length === 0;
  const before = new Map(shown.value.map((a) => [a.key, a]));
  const after = new Map(to.map((a) => [a.key, a]));
  const pairs = [...new Set([...before.keys(), ...after.keys()])].map((key) => {
    const a = before.get(key);
    const b = after.get(key);
    // first draw: every arc scales from 0 at the top → one clean clockwise sweep
    const from = a ?? (first ? { key, start: 0, len: 0, color: b!.color } : { ...b!, len: 0 });
    const dest = b ?? { ...a!, len: 0 };
    return { from, dest };
  });
  const t0 = performance.now();
  const duration = first ? 800 : 500;
  const step = (now: number) => {
    const t = Math.min(1, (now - t0) / duration);
    const e = 1 - Math.pow(1 - t, 3);
    shown.value = pairs.map(({ from, dest }) => ({
      key: dest.key,
      color: dest.color,
      start: lerp(from.start, dest.start, e),
      len: lerp(from.len, dest.len, e),
    }));
    if (t < 1) frame = requestAnimationFrame(step);
    else shown.value = to;
  };
  frame = requestAnimationFrame(step);
}
watch(target, tweenTo, { immediate: true });

const gap = computed(() => (target.value.length > 1 ? GAP : 0));
const dash = (a: Arc) => `${Math.max(0, a.len * CIRC - gap.value).toFixed(2)} ${CIRC.toFixed(2)}`;
const offset = (a: Arc) => (-(a.start * CIRC + gap.value / 2)).toFixed(2);
function push(a: Arc) {
  const phi = 2 * Math.PI * (a.start + a.len / 2); // in the rotated group 0 = 12 o'clock on screen
  return `translate(${(Math.cos(phi) * PUSH).toFixed(2)}px, ${(Math.sin(phi) * PUSH).toFixed(2)}px)`;
}

// --- interaction: hover (mouse) · focus (keyboard) · pinned (tap/click, Esc clears) -------------
const hovered = ref<string | null>(null);
const focused = ref<string | null>(null);
const pinned = ref<string | null>(null);
let leaveTimer = 0;

function enter(key: string) {
  window.clearTimeout(leaveTimer);
  hovered.value = key;
}
function leave() {
  // short grace period: crossing the 3px gap between slices must not flash the overview
  window.clearTimeout(leaveTimer);
  leaveTimer = window.setTimeout(() => (hovered.value = null), 90);
}
const togglePin = (key: string) => (pinned.value = pinned.value === key ? null : key);

const activeKey = computed(() => {
  const k = hovered.value ?? focused.value ?? pinned.value;
  return k && groups.value.some((g) => g.key === k) ? k : null;
});
const colorOf = (key: string) => target.value.find((a) => a.key === key)?.color ?? 0;

onBeforeUnmount(() => {
  cancelAnimationFrame(frame);
  window.clearTimeout(leaveTimer);
});

// --- copy ------------------------------------------------------------------------------------
const share = (s: number) => pct(Math.round(s * 100), false);
const paymentsText = (n: number) => `${n} ${n === 1 ? "payment" : "payments"}`;
const datesText = (dates: string[]) => dates.map(fmtDayMonth).join(" · ");
const summary = computed(
  () =>
    `Biggest payments in the next ${props.periodLabel}: ` +
    groups.value.map((g) => `${g.label} ${eur(g.total)} (${share(g.share)})`).join(", ") +
    `. Total ${eur(total.value)}.`,
);
</script>

<template>
  <!-- empty: nothing big due in this window -->
  <div v-if="!groups.length" class="grid min-h-[16rem] place-content-center justify-items-center gap-3 text-center animate-rise">
    <IconTile icon="pieChart" tone="info" size="lg" />
    <p class="font-semibold">No big payments in the next {{ periodLabel }}</p>
    <p class="max-w-[16rem] text-label text-muted">Avida looks at your biggest single payments. None of them falls in this period.</p>
  </div>

  <div v-else class="grid gap-4" @keydown.esc="pinned = null">
    <!-- donut + centre read-out (fixed box → never changes size) -->
    <div class="relative mx-auto h-[13.5rem] w-[13.5rem]">
      <svg
        :viewBox="`0 0 ${SIZE} ${SIZE}`"
        class="absolute inset-0 h-full w-full overflow-visible"
        role="img"
        :aria-label="summary"
      >
        <g :transform="`rotate(-90 ${MID} ${MID})`">
          <circle
            v-for="a in shown"
            :key="a.key"
            :cx="MID"
            :cy="MID"
            :r="R"
            fill="none"
            :stroke-dasharray="dash(a)"
            :stroke-dashoffset="offset(a)"
            :class="[
              SLICES[a.color].stroke,
              'cursor-pointer transition-[stroke,stroke-width,opacity,transform] duration-base',
              activeKey && activeKey !== a.key ? 'opacity-25' : 'opacity-100',
            ]"
            :style="{
              strokeWidth: activeKey === a.key ? W_ACTIVE : W,
              transform: activeKey === a.key ? push(a) : 'translate(0px, 0px)',
            }"
            @pointerenter="enter(a.key)"
            @pointerleave="leave"
            @click="togglePin(a.key)"
          />
        </g>
      </svg>

      <div class="pointer-events-none absolute inset-0 grid place-items-center" aria-hidden="true">
        <div class="grid place-items-center [&>*]:col-start-1 [&>*]:row-start-1">
          <!-- overview -->
          <div
            :class="[
              'grid w-[8.5rem] justify-items-center gap-1 text-center transition-[opacity,transform] duration-base',
              activeKey ? 'scale-95 opacity-0' : 'scale-100 opacity-100',
            ]"
          >
            <span class="text-caption font-semibold text-muted">Total</span>
            <b class="font-display text-2xl font-bold leading-tight tabular-nums">{{ eur(total) }}</b>
            <span class="text-caption text-muted">in {{ paymentsText(count) }}</span>
          </div>
          <!-- one layer per payment, crossfaded -->
          <div
            v-for="g in groups"
            :key="g.key"
            :class="[
              'grid w-[7.5rem] justify-items-center gap-1 text-center transition-[opacity,transform] duration-base',
              activeKey === g.key ? 'scale-100 opacity-100' : 'scale-95 opacity-0',
            ]"
          >
            <span class="line-clamp-2 text-caption font-semibold leading-tight">{{ g.short }}</span>
            <b class="font-display text-xl font-bold leading-tight tabular-nums">{{ eur(g.total) }}</b>
            <span class="text-caption text-muted">{{ share(g.share) }} · {{ paymentsText(g.dates.length) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- legend: always label + amount + share; on hover/focus the second line swaps count → dates -->
    <ul class="grid gap-1" aria-label="Payments">
      <li v-for="g in groups" :key="g.key" class="animate-rise">
        <button
          type="button"
          :class="[
            'grid w-full grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-x-3 rounded-lg px-2.5 py-2 text-left',
            activeKey === g.key ? 'bg-input' : '',
          ]"
          :aria-pressed="pinned === g.key"
          :aria-label="`${g.label}, ${eur(g.total)}, ${share(g.share)}, ${paymentsText(g.dates.length)}: ${datesText(g.dates)}`"
          @pointerenter="enter(g.key)"
          @pointerleave="leave"
          @focus="focused = g.key"
          @blur="focused = null"
          @click="togglePin(g.key)"
        >
          <span
            :class="[
              'mt-1 h-3 w-3 rounded-full transition-transform duration-base',
              SLICES[colorOf(g.key)].bg,
              activeKey === g.key ? 'scale-125' : 'scale-100',
            ]"
            aria-hidden="true"
          />
          <span class="grid min-w-0 gap-0.5" aria-hidden="true" :title="g.label">
            <span class="truncate text-label font-semibold leading-snug">{{ g.short }}</span>
            <span class="grid text-caption text-muted [&>*]:col-start-1 [&>*]:row-start-1">
              <span :class="['truncate transition-opacity duration-base', activeKey === g.key ? 'opacity-0' : 'opacity-100']">
                {{ paymentsText(g.dates.length) }}
              </span>
              <span
                :class="[
                  'flex min-w-0 items-center gap-1.5 transition-opacity duration-base',
                  activeKey === g.key ? 'opacity-100' : 'opacity-0',
                ]"
              >
                <AppIcon :name="categoryIcon(g.category)" :size="14" />
                <span class="truncate">{{ datesText(g.dates) }}</span>
              </span>
            </span>
          </span>
          <span class="grid justify-items-end gap-0.5" aria-hidden="true">
            <b class="font-display text-label font-bold leading-snug tabular-nums">{{ eur(g.total) }}</b>
            <span class="text-caption tabular-nums text-muted">{{ share(g.share) }}</span>
          </span>
        </button>
      </li>
    </ul>

    <p class="flex items-start gap-1.5 text-caption text-muted">
      <AppIcon name="info" :size="14" class="mt-0.5" />
      Your biggest single payments only (top 5 of the forecast). Smaller costs are left out.
    </p>
  </div>
</template>
