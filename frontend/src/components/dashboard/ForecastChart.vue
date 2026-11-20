<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { eur, fmtDate, fmtDayMonth } from "@/utils/format";
import { prefersReducedMotion as reducedMotion } from "@/utils/motion";
import { monotonePath, niceTicks, windowMin, type ChartLine } from "./chart";

/**
 * Cash forecast – plain SVG drawn at the real pixel width (no library, no horizontal scroll).
 * - smooth monotone curve: rounded corners, but the lowest point stays exactly on the line
 * - `days` = window of the backend forecast; changing it zooms smoothly (scales are tweened)
 * - hover / drag / arrow keys: guide + dots glide, a bubble follows; the read-out below keeps the
 *   last day (fixed space → no layout shift) so the owner can read or copy it
 */
const props = defineProps<{ lines: ChartLine[]; days?: number }>();

const uid = useId();
const gradId = `fc-grad-${uid}`;
const clipId = `fc-clip-${uid}`;

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const ease = (t: number) => 1 - Math.pow(1 - t, 3);

// --- size: measured, so text is real-size and the chart fits any width ---------------------------
const wrap = ref<HTMLDivElement | null>(null);
const svgEl = ref<SVGSVGElement | null>(null);
const tipEl = ref<HTMLDivElement | null>(null);
const W = ref(720);
const remPx = ref(16); // root font size – follows the accessibility text-size setting
const tipSize = ref({ w: 150, h: 64 });

const fontPx = computed(() => remPx.value * 0.8125); // = text-caption
const H = computed(() => Math.round((W.value < 520 ? 240 : 300) * (1 + (remPx.value / 16 - 1) * 0.6)));

// --- data window ----------------------------------------------------------------------------------
const base = computed(() => props.lines[0]?.forecast ?? null);
const total = computed(() => base.value?.series.length ?? 0);
const n = computed(() => clamp(Math.round(props.days ?? total.value), 2, Math.max(2, total.value)));
const main = computed(() => props.lines[props.lines.length - 1] ?? null);
const mainMin = computed(() => (main.value ? windowMin(main.value.forecast, n.value) : { index: 0, value: 0 }));
const buffer = computed(() => base.value?.buffer ?? 0);

/** Where the scales should end up (x = days shown, y = value range incl. 0 and the cushion). */
const target = computed(() => {
  const values = props.lines.flatMap((l) => l.forecast.series.slice(0, n.value).map((s) => s.balance));
  if (!values.length) return { span: 1, yMin: 0, yMax: 1 };
  const lo = Math.min(0, buffer.value, ...values);
  const hi = Math.max(buffer.value, ...values);
  return { span: n.value - 1, yMin: lo, yMax: hi + (hi - lo || 1) * 0.07 };
});

// Scales on screen glide to the target (zoom when the period changes, rescale after a sync).
const view = ref({ ...target.value });
let viewFrame = 0;
watch(target, (to) => {
  cancelAnimationFrame(viewFrame);
  if (reducedMotion()) {
    view.value = { ...to };
    return;
  }
  const from = { ...view.value };
  const t0 = performance.now();
  const step = (now: number) => {
    const e = ease(Math.min(1, (now - t0) / 500));
    view.value = {
      span: from.span + (to.span - from.span) * e,
      yMin: from.yMin + (to.yMin - from.yMin) * e,
      yMax: from.yMax + (to.yMax - from.yMax) * e,
    };
    if (e < 1) viewFrame = requestAnimationFrame(step);
  };
  viewFrame = requestAnimationFrame(step);
});

// First paint: the lines draw in from the left.
const reveal = ref(1);
let revealFrame = 0;

// --- layout & scales --------------------------------------------------------------------------------
const yTicks = computed(() =>
  niceTicks(target.value.yMin, target.value.yMax, W.value < 520 ? 3 : 4).filter(
    (t) => t >= target.value.yMin && t <= target.value.yMax,
  ),
);
const pad = computed(() => {
  const f = fontPx.value;
  const longest = Math.max(4, ...yTicks.value.map((t) => eur(t).length));
  return { top: Math.round(f + 8), right: 14, bottom: Math.round(f * 2 + 10), left: Math.round(longest * f * 0.6 + 14) };
});
const plot = computed(() => ({
  x0: pad.value.left,
  x1: W.value - pad.value.right,
  y0: pad.value.top,
  y1: H.value - pad.value.bottom,
}));
const sx = (i: number) => plot.value.x0 + (i / (view.value.span || 1)) * (plot.value.x1 - plot.value.x0);
const sy = (v: number) =>
  plot.value.y0 + ((view.value.yMax - v) / (view.value.yMax - view.value.yMin || 1)) * (plot.value.y1 - plot.value.y0);

const xTicks = computed(() => {
  const count = W.value < 480 ? 3 : W.value < 760 ? 4 : 5;
  const last = n.value - 1;
  return [...new Set(Array.from({ length: count }, (_, k) => Math.round((k * last) / (count - 1))))];
});

/** Paths include a few points past the window so a zoom slides them in/out under the clip. */
const drawn = computed(() => {
  const last = Math.min(total.value - 1, Math.ceil(view.value.span) + 1);
  return props.lines.map((l) => {
    const pts = l.forecast.series.slice(0, last + 1).map((s, i) => [sx(i), sy(s.balance)] as const);
    const d = monotonePath(pts);
    const end = pts[pts.length - 1]?.[0] ?? plot.value.x0;
    return {
      line: l,
      d,
      area: `${d}L${end.toFixed(1)},${plot.value.y1}L${plot.value.x0},${plot.value.y1}Z`,
      min: windowMin(l.forecast, n.value),
    };
  });
});
const revealX = computed(() => plot.value.x0 + (plot.value.x1 - plot.value.x0) * reveal.value);

/**
 * Cushion label: inside the red zone when it fits (clear of the "Lowest" call-out above), and on the right
 * when the lowest point would sit on top of it at the left.
 */
const cushionLabel = computed(() => {
  const { x0, x1, y1 } = plot.value;
  const yb = sy(buffer.value);
  const mx = sx(mainMin.value.index);
  const widthOf = (s: string) => s.length * fontPx.value * 0.56;
  const free = (from: number, to: number) => to <= x1 - 4 && (mx + 9 < from || mx - 9 > to);
  // try: full text left → right, then the short text left → right (narrow phones, big text size)
  const candidates = [`Safety cushion ${eur(buffer.value)}`, `Cushion ${eur(buffer.value)}`].flatMap((text) => [
    { text, x: x0 + 8, anchor: "start", from: x0 + 8, to: x0 + 8 + widthOf(text) },
    { text, x: x1 - 8, anchor: "end", from: x1 - 8 - widthOf(text), to: x1 - 8 },
  ]);
  const pick =
    candidates.find((c) => c.from >= x0 && free(c.from, c.to)) ??
    candidates.find((c) => c.from >= x0 && c.to <= x1) ??
    candidates[3];
  return { ...pick, y: y1 - yb >= fontPx.value + 5 ? yb + fontPx.value + 1.5 : yb - 7 };
});
const shownAt = (i: number) => sx(i) <= revealX.value + 1;

/** "Lowest" call-out above (or below) the main line's lowest point. */
const callout = computed(() => {
  const m = main.value;
  if (!m) return null;
  const f = fontPx.value;
  const date = fmtDayMonth(m.forecast.series[mainMin.value.index].date);
  const value = eur(mainMin.value.value);
  const w = Math.round(Math.max(`Lowest · ${date}`.length * f * 0.56, value.length * remPx.value * 0.62) + 24);
  const h = Math.round(f * 1.25 + remPx.value * 1.25 + 14);
  const px = sx(mainMin.value.index);
  const py = sy(mainMin.value.value);
  const x = clamp(px - w / 2, plot.value.x0 + 4, W.value - pad.value.right - w);
  const above = py - h - 14 > plot.value.y0 - 6;
  return { w, h, x, y: above ? py - h - 14 : py + 14, date, value, f };
});

// --- hover / scrub / keyboard ---------------------------------------------------------------------
const active = ref<number | null>(null); // the day under the pointer / keyboard focus right now
const pinned = ref<number | null>(null); // the last day looked at – the read-out keeps it
watch(n, (len) => {
  if (pinned.value !== null && pinned.value >= len) pinned.value = null;
  if (active.value !== null && active.value >= len) active.value = len - 1;
});

const focusIndex = computed(() => clamp(active.value ?? pinned.value ?? mainMin.value.index, 0, n.value - 1));
const guideX = computed(() => sx(focusIndex.value));
const dots = computed(() =>
  props.lines.map((l) => ({ line: l, y: sy(l.forecast.series[focusIndex.value]?.balance ?? 0) })),
);

const tip = computed(() => {
  const { w, h } = tipSize.value;
  const mainY = dots.value[dots.value.length - 1]?.y ?? plot.value.y0;
  let left = guideX.value + 16;
  if (left + w > W.value - 4) left = guideX.value - 16 - w;
  return {
    left: clamp(left, 4, Math.max(4, W.value - w - 4)),
    top: clamp(mainY - h / 2, plot.value.y0 - 4, Math.max(plot.value.y0, plot.value.y1 - h)),
  };
});

function indexAt(ev: PointerEvent): number {
  const r = svgEl.value!.getBoundingClientRect();
  const px = ((ev.clientX - r.left) / (r.width || 1)) * W.value;
  return clamp(Math.round(((px - plot.value.x0) / (plot.value.x1 - plot.value.x0)) * view.value.span), 0, n.value - 1);
}
function onPointer(ev: PointerEvent) {
  if (!svgEl.value) return;
  const i = indexAt(ev);
  active.value = i;
  pinned.value = i;
}
function onKey(ev: KeyboardEvent) {
  const cur = focusIndex.value;
  const stepBy = ev.shiftKey ? 7 : 1;
  const next =
    ev.key === "ArrowRight" ? cur + stepBy
    : ev.key === "ArrowLeft" ? cur - stepBy
    : ev.key === "Home" ? 0
    : ev.key === "End" ? n.value - 1
    : null;
  if (next === null) return;
  ev.preventDefault();
  active.value = pinned.value = clamp(next, 0, n.value - 1);
}
function onFocus() {
  if (wrap.value?.matches(":focus-visible")) active.value = focusIndex.value;
}

// --- read-out (always there, keeps the last day) ---------------------------------------------------
const readIndex = computed(() => clamp(pinned.value ?? mainMin.value.index, 0, n.value - 1));
const readDate = computed(() => base.value?.series[readIndex.value]?.date ?? null);
const isLowest = computed(() => readIndex.value === mainMin.value.index);
const rows = computed(() =>
  [...props.lines].reverse().map((l) => {
    const m = windowMin(l.forecast, n.value);
    return {
      line: l,
      value: l.forecast.series[readIndex.value]?.balance ?? 0,
      min: m.value,
      minDate: l.forecast.series[m.index]?.date ?? null,
    };
  }),
);

const copied = ref(false);
let copyTimer = 0;
async function copy() {
  const text = `${fmtDate(readDate.value)} – ${rows.value.map((r) => `${r.line.label}: ${eur(r.value)}`).join("; ")}`;
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = Object.assign(document.createElement("textarea"), { value: text });
    ta.style.cssText = "position:fixed;opacity:0";
    document.body.append(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
  copied.value = true;
  window.clearTimeout(copyTimer);
  copyTimer = window.setTimeout(() => (copied.value = false), 1800);
}

// --- lifecycle ----------------------------------------------------------------------------------------
let ro: ResizeObserver | null = null;
let mo: MutationObserver | null = null;
const readRem = () => (remPx.value = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16);

onMounted(() => {
  readRem();
  ro = new ResizeObserver((entries) => {
    for (const e of entries) {
      if (e.target === wrap.value) W.value = Math.max(260, Math.round(e.contentRect.width));
      else if (e.target === tipEl.value) tipSize.value = { w: e.target.clientWidth, h: e.target.clientHeight };
    }
  });
  if (wrap.value) ro.observe(wrap.value);
  if (tipEl.value) ro.observe(tipEl.value);
  mo = new MutationObserver(readRem);
  mo.observe(document.documentElement, { attributes: true });

  if (!reducedMotion()) {
    reveal.value = 0;
    const t0 = performance.now();
    const step = (now: number) => {
      reveal.value = ease(Math.min(1, (now - t0) / 900));
      if (reveal.value < 1) revealFrame = requestAnimationFrame(step);
    };
    revealFrame = requestAnimationFrame(step);
  }
});
onBeforeUnmount(() => {
  ro?.disconnect();
  mo?.disconnect();
  cancelAnimationFrame(viewFrame);
  cancelAnimationFrame(revealFrame);
  window.clearTimeout(copyTimer);
});

const STROKE = { primary: "stroke-chart-line", risk: "stroke-chart-alt" };
const FILL = { primary: "fill-chart-line", risk: "fill-chart-alt" };
const DOT = { primary: "bg-chart-line", risk: "bg-chart-alt" };
</script>

<template>
  <div v-if="base && total >= 2 && main" class="grid gap-4">
    <!-- chart -->
    <div
      ref="wrap"
      class="relative -mx-1 rounded-lg px-1"
      tabindex="0"
      role="group"
      aria-label="Forecast chart. Use the left and right arrow keys to move between days."
      @keydown="onKey"
      @focus="onFocus"
      @blur="active = null"
    >
      <svg
        ref="svgEl"
        :width="W"
        :height="H"
        :viewBox="`0 0 ${W} ${H}`"
        class="block w-full cursor-crosshair select-none overflow-visible [touch-action:pan-y]"
        role="img"
        :aria-label="`Cash forecast for the next ${n} days. Lowest balance ${eur(mainMin.value)} on ${fmtDate(main.forecast.series[mainMin.index].date)}.`"
        @pointermove="onPointer"
        @pointerdown="onPointer"
        @pointerleave="active = null"
        @pointercancel="active = null"
      >
        <defs>
          <linearGradient :id="gradId" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" style="stop-color: rgb(var(--c-chart-line)); stop-opacity: 0.28" />
            <stop offset="100%" style="stop-color: rgb(var(--c-chart-line)); stop-opacity: 0" />
          </linearGradient>
          <clipPath :id="clipId">
            <rect :x="plot.x0 - 2" :y="0" :width="Math.max(0, revealX - plot.x0 + 4)" :height="H" />
          </clipPath>
        </defs>

        <!-- grid + y labels (fade in/out when the range changes, slide with the scale) -->
        <TransitionGroup name="fade" tag="g">
          <g v-for="t in yTicks" :key="t">
            <line :x1="plot.x0" :x2="plot.x1" :y1="sy(t)" :y2="sy(t)" class="stroke-grid" stroke-width="1" />
            <text :x="plot.x0 - 10" :y="sy(t) + fontPx * 0.35" text-anchor="end" class="fill-muted text-caption tabular-nums">
              {{ eur(t) }}
            </text>
          </g>
        </TransitionGroup>

        <!-- danger zone below the safety cushion -->
        <rect
          :x="plot.x0"
          :y="sy(buffer)"
          :width="plot.x1 - plot.x0"
          :height="Math.max(0, plot.y1 - sy(buffer))"
          class="fill-negative-soft"
          opacity="0.7"
        />
        <line
          :x1="plot.x0" :x2="plot.x1" :y1="sy(buffer)" :y2="sy(buffer)"
          class="stroke-negative" stroke-dasharray="6 4" stroke-width="1.5"
        />
        <text :x="cushionLabel.x" :y="cushionLabel.y" :text-anchor="cushionLabel.anchor" class="fill-negative text-caption font-semibold">
          {{ cushionLabel.text }}
        </text>

        <!-- x labels -->
        <text
          v-for="(i, k) in xTicks" :key="k"
          :x="sx(i)" :y="H - 10"
          :text-anchor="k === 0 ? 'start' : k === xTicks.length - 1 ? 'end' : 'middle'"
          class="fill-muted text-caption"
        >{{ i === 0 ? "Today" : fmtDayMonth(base.series[i].date) }}</text>

        <!-- lines + area (clipped to the plot; draw in from the left on first paint) -->
        <g :clip-path="`url(#${clipId})`">
          <TransitionGroup name="fade" tag="g">
            <path
              v-for="p in drawn.filter((p) => p.line.tone === 'primary')" :key="`a-${p.line.label}`"
              :d="p.area" :fill="`url(#${gradId})`"
            />
            <path
              v-for="p in drawn" :key="p.line.label"
              :d="p.d"
              fill="none" :class="STROKE[p.line.tone]" stroke-width="2.75" stroke-linejoin="round" stroke-linecap="round"
              :stroke-dasharray="p.line.tone === 'risk' ? '7 6' : undefined"
            />
          </TransitionGroup>
          <!-- everything right of the cursor steps back a little -->
          <rect
            :x="0" :y="plot.y0 - 4" :width="plot.x1 - plot.x0 + 8" :height="plot.y1 - plot.y0 + 8"
            class="pointer-events-none fill-surface transition-[transform,opacity] duration-fast"
            :style="{ transform: `translateX(${guideX}px)`, opacity: active !== null ? 0.5 : 0 }"
          />
        </g>

        <!-- today + lowest point markers -->
        <circle :cx="plot.x0" :cy="sy(base.series[0].balance)" r="5" class="fill-chart-line stroke-surface" stroke-width="2.5" />
        <circle
          v-for="p in drawn" :key="`min-${p.line.label}`"
          :cx="sx(p.min.index)" :cy="sy(p.min.value)"
          r="5.5" :class="[FILL[p.line.tone], 'stroke-surface transition-opacity duration-base']" stroke-width="2.5"
          :opacity="shownAt(p.min.index) ? 1 : 0"
        />

        <!-- call-out: lowest point of the main line (fades away while you explore) -->
        <g
          v-if="callout"
          class="pointer-events-none transition-opacity duration-base"
          :opacity="active === null && reveal > 0.98 ? 1 : 0"
          aria-hidden="true"
        >
          <rect :x="callout.x" :y="callout.y" :width="callout.w" :height="callout.h" rx="8" class="fill-surface stroke-line" stroke-width="1" />
          <text :x="callout.x + 12" :y="callout.y + callout.f + 5" class="fill-muted text-caption">Lowest · {{ callout.date }}</text>
          <text :x="callout.x + 12" :y="callout.y + callout.h - 9" class="fill-fg font-display text-base font-bold tabular-nums">{{ callout.value }}</text>
        </g>

        <!-- hover guide + dots: glide between days -->
        <g
          class="pointer-events-none transition-opacity duration-base"
          :opacity="active !== null ? 1 : 0"
          aria-hidden="true"
        >
          <line
            x1="0" x2="0" :y1="plot.y0 - 4" :y2="plot.y1"
            class="stroke-muted transition-transform duration-fast" stroke-width="1" stroke-dasharray="3 3"
            :style="{ transform: `translateX(${guideX}px)` }"
          />
          <circle
            v-for="d in dots" :key="`h-${d.line.label}`"
            cx="0" cy="0" r="6" :class="[FILL[d.line.tone], 'stroke-surface transition-transform duration-fast']" stroke-width="3"
            :style="{ transform: `translate(${guideX}px, ${d.y}px)` }"
          />
        </g>
      </svg>

      <!-- floating bubble -->
      <div
        ref="tipEl"
        class="pointer-events-none absolute left-0 top-0 z-10 grid min-w-[9.5rem] gap-1 rounded-lg border border-line bg-surface px-3 py-2 shadow-lift transition-[transform,opacity] duration-fast"
        :style="{ transform: `translate(${tip.left}px, ${tip.top}px)`, opacity: active !== null ? 1 : 0 }"
        aria-hidden="true"
      >
        <b class="text-caption font-semibold text-muted">{{ fmtDate(base.series[focusIndex].date) }}</b>
        <span v-for="l in [...lines].reverse()" :key="`t-${l.label}`" class="flex items-center justify-between gap-3 text-label">
          <span class="flex items-center gap-1.5 text-muted">
            <span :class="['h-2 w-2 rounded-full', DOT[l.tone]]" />{{ l.short }}
          </span>
          <b class="font-semibold tabular-nums" :class="l.forecast.series[focusIndex].balance < buffer ? 'text-negative' : 'text-fg'">
            {{ eur(l.forecast.series[focusIndex].balance) }}
          </b>
        </span>
      </div>
    </div>

    <!-- read-out + legend: fixed rows, keeps the last day you looked at (select or copy it) -->
    <div class="grid gap-3 rounded-xl bg-input px-4 py-3 sm:px-5" aria-live="polite">
      <div class="flex items-center justify-between gap-3">
        <span class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5">
          <AppIcon :name="isLowest ? 'trendingDown' : 'calendar'" :size="17" class="text-muted" />
          <b class="min-w-[6.5em] whitespace-nowrap font-semibold tabular-nums">{{ fmtDate(readDate) }}</b>
          <!-- both captions share one cell → switching never changes the width -->
          <span class="grid whitespace-nowrap text-label text-muted [&>*]:col-start-1 [&>*]:row-start-1">
            <span :class="isLowest ? '' : 'invisible'">· lowest point</span>
            <span :class="isLowest ? 'invisible' : ''">· selected day</span>
          </span>
        </span>
        <button
          type="button"
          class="inline-flex min-h-10 min-w-10 shrink-0 items-center justify-center rounded-lg border border-line bg-surface px-2.5 text-label font-semibold text-fg hover:border-fg/40 hover:shadow-lift sm:min-h-9 sm:px-3"
          :aria-label="copied ? 'Copied' : 'Copy this day'"
          @click="copy"
        >
          <!-- both states stacked in one cell → the button never changes size -->
          <span class="grid [&>*]:col-start-1 [&>*]:row-start-1">
            <span :class="['flex items-center gap-1.5 transition-opacity duration-base', copied ? 'opacity-0' : 'opacity-100']">
              <AppIcon name="copy" :size="16" /><span class="hidden sm:inline">Copy</span>
            </span>
            <span :class="['flex items-center gap-1.5 text-positive transition-opacity duration-base', copied ? 'opacity-100' : 'opacity-0']">
              <AppIcon name="check" :size="16" /><span class="hidden sm:inline">Copied</span>
            </span>
          </span>
          <span class="sr-only" role="status">{{ copied ? "Copied to clipboard" : "" }}</span>
        </button>
      </div>
      <!-- per line: name + value on the selected day, its lowest underneath (short names on phones) -->
      <ul class="grid gap-3">
        <li
          v-for="r in rows"
          :key="r.line.label"
          class="grid grid-cols-[1.75rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-0.5"
        >
          <svg width="28" height="8" class="col-start-1 row-start-1" aria-hidden="true">
            <line
              x1="1" x2="27" y1="4" y2="4" :class="STROKE[r.line.tone]" stroke-width="3" stroke-linecap="round"
              :stroke-dasharray="r.line.tone === 'risk' ? '6 5' : undefined"
            />
          </svg>
          <span class="col-start-2 row-start-1 text-label font-medium leading-snug">
            <span class="sm:hidden">{{ r.line.short }}</span><span class="hidden sm:inline">{{ r.line.label }}</span>
          </span>
          <span class="col-span-2 col-start-2 row-start-2 text-caption text-muted sm:col-span-1 sm:col-start-2">
            Lowest {{ eur(r.min) }} · {{ fmtDayMonth(r.minDate) }}
          </span>
          <b
            :class="[
              'col-start-3 row-start-1 min-w-[6.5rem] text-right font-display text-lg font-bold leading-tight tabular-nums sm:row-span-2 sm:row-start-1',
              r.value < buffer ? 'text-negative' : 'text-fg',
            ]"
          >{{ eur(r.value) }}</b>
        </li>
      </ul>
    </div>
  </div>
</template>
