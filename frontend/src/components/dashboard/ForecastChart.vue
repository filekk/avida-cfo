<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import CollapseTransition from "@/components/ui/CollapseTransition.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { TONE_TEXT } from "@/components/ui/tones";
import { t, tn } from "@/i18n";
import { eur, eurSigned, fmtDate, fmtDayMonth } from "@/utils/format";
import { prefersReducedMotion as reducedMotion } from "@/utils/motion";
import { categoryIcon, monotonePath, niceTicks, windowMin, type ChartLine } from "./chart";

/**
 * Cash forecast – plain SVG drawn at the real pixel width (no library, no horizontal scroll).
 *
 * Reading it:  hover = light preview (guide + bubble) · CLICK / tap = select a day ·
 *              DRAG / swipe sideways (or Shift+click) = select a period · Esc / "Back to today" = clear.
 * The read-out below always answers "what does that mean for me": today by default, the chosen day
 * (balance, change vs today, cushion) or the chosen period (start → end, lowest, days below the cushion,
 * big payments inside). It animates its height between modes – nothing jumps.
 * Keyboard: ←/→ move the day (Shift extends the period), PageUp/PageDown ±7 days, Home/End, Enter, Esc.
 */
const props = defineProps<{ lines: ChartLine[]; days?: number }>();

const uid = useId();
const clipId = `fc-clip-${uid}`;

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const ease = (x: number) => 1 - Math.pow(1 - x, 3);

// --- size: measured, so text is real-size and the chart fits any width ---------------------------
const wrap = ref<HTMLDivElement | null>(null);
const svgEl = ref<SVGSVGElement | null>(null);
const tipEl = ref<HTMLDivElement | null>(null);
const W = ref(720);
const remPx = ref(16); // root font size – follows the accessibility text-size setting
const tipSize = ref({ w: 150, h: 64 });

const fontPx = computed(() => remPx.value * 0.8125); // = text-caption
const tagH = computed(() => Math.round(fontPx.value * 1.5 + 6));
const H = computed(() => Math.round((W.value < 520 ? 250 : 310) * (1 + (remPx.value / 16 - 1) * 0.6)));

// --- data window ----------------------------------------------------------------------------------
const base = computed(() => props.lines[0]?.forecast ?? null);
const total = computed(() => base.value?.series.length ?? 0);
const n = computed(() => clamp(Math.round(props.days ?? total.value), 2, Math.max(2, total.value)));
const main = computed(() => props.lines[props.lines.length - 1] ?? null);
const mainMin = computed(() => (main.value ? windowMin(main.value.forecast, n.value) : { index: 0, value: 0 }));
const buffer = computed(() => base.value?.buffer ?? 0);
const bal = (l: ChartLine, i: number) => l.forecast.series[i]?.balance ?? 0;
const dateAt = (i: number) => base.value?.series[i]?.date ?? null;
/** The main line first in read-outs and the bubble. */
const ordered = computed(() => [...props.lines].reverse());

// --- "without Avida" loss: main line (follow Avida) minus the risk line (accept every increase) ------
// The gap is tiny next to the balance (≈ 1–3 k€ on a 130 k€ axis), so it gets its own strip under the
// chart with its own scale – same x axis, so hover / selection line up with the days above.
const risk = computed(() => props.lines.find((l) => l.tone === "risk") ?? null);
const lossAt = (i: number) => (risk.value && main.value ? Math.max(0, bal(main.value, i) - bal(risk.value, i)) : 0);
const hasLoss = computed(() => !!risk.value && (base.value?.series ?? []).some((_, i) => lossAt(i) > 0));
const lossMaxIn = (len: number) => Math.max(0, ...Array.from({ length: len }, (_, i) => lossAt(i)));

/** Where the scales should end up (x = days shown, y = value range incl. 0 and the cushion, loss strip). */
const target = computed(() => {
  const values = props.lines.flatMap((l) => l.forecast.series.slice(0, n.value).map((s) => s.balance));
  const strip = hasLoss.value ? 1 : 0;
  const lossMax = Math.max(1, lossMaxIn(n.value)) * 1.12;
  if (!values.length) return { span: 1, yMin: 0, yMax: 1, strip, lossMax };
  const lo = Math.min(0, buffer.value, ...values);
  const hi = Math.max(buffer.value, ...values);
  return { span: n.value - 1, yMin: lo, yMax: hi + (hi - lo || 1) * 0.07, strip, lossMax };
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
      strip: from.strip + (to.strip - from.strip) * e,
      lossMax: from.lossMax + (to.lossMax - from.lossMax) * e,
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
    (v) => v >= target.value.yMin && v <= target.value.yMax,
  ),
);
const pad = computed(() => {
  const f = fontPx.value;
  const longest = Math.max(4, ...yTicks.value.map((v) => eur(v).length));
  // top leaves room for the date tag of a selection
  return { top: tagH.value + 10, right: 14, bottom: Math.round(f * 2 + 10), left: Math.round(longest * f * 0.6 + 14) };
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

/**
 * Loss strip geometry: a small header line ("Without Avida you would lose … −2.940 €") and a panel where the
 * loss grows DOWNWARDS from a zero line (money draining away). It slides open (view.strip 0→1) after a sync;
 * the date labels move below it, so one x axis serves both.
 */
const strip = computed(() => {
  const head = Math.round(fontPx.value * 1.25 + 12);
  const h = Math.round(fontPx.value * 2.4 + 26);
  const top = plot.value.y1 + head; // zero line
  return { head, h, top, bottom: top + h, k: view.value.strip };
});
const svgH = computed(() => H.value + Math.round((strip.value.head + strip.value.h) * view.value.strip));
const ly = (v: number) => strip.value.top + 2 + (v / (view.value.lossMax || 1)) * (strip.value.h - 4);
const guideBottom = computed(() => (hasLoss.value ? strip.value.bottom : plot.value.y1));
const lossDrawn = computed(() => {
  if (!hasLoss.value) return null;
  const last = Math.min(total.value - 1, Math.ceil(view.value.span) + 1);
  const pts = Array.from({ length: last + 1 }, (_, i) => [sx(i), ly(lossAt(i))] as const);
  const d = monotonePath(pts);
  const end = pts[pts.length - 1]?.[0] ?? plot.value.x0;
  return { d, area: `${d}L${end.toFixed(1)},${strip.value.top}L${plot.value.x0},${strip.value.top}Z` };
});
/** Day the strip's header talks about: hovered day → selected day / period end → end of the window. */
const lossIndex = computed(() => {
  if (hover.value !== null && !dragging.value) return hoverIndex.value;
  if (sel.value) return selHi.value;
  return n.value - 1;
});
const lossHead = computed(() => ({
  label: W.value < 520 ? t("Without Avida") : t("Without Avida you would lose"),
  value: `${eur(-lossAt(lossIndex.value))} · ${fmtDayMonth(dateAt(lossIndex.value))}`,
}));

const xTicks = computed(() => {
  // as many date labels as fit without touching (≈5.5 characters each), 2…5
  const count = clamp(Math.floor((plot.value.x1 - plot.value.x0) / (fontPx.value * 5.5)), 2, 5);
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
const shownAt = (i: number) => sx(i) <= revealX.value + 1;

/**
 * Cushion label: inside the red zone when it fits (clear of the "Lowest" call-out above), and on the side
 * the lowest point is not on; short text on narrow phones / big text sizes.
 */
const cushionLabel = computed(() => {
  const { x0, x1, y1 } = plot.value;
  const f = fontPx.value;
  const yb = sy(buffer.value);
  const y = y1 - yb >= f + 5 ? yb + f + 1.5 : yb - 7;
  const mx = sx(mainMin.value.index);
  const widthOf = (s: string) => s.length * f * 0.56;
  // the visible "Lowest" call-out box (with a small margin) – the label must not end up underneath it
  const c = calloutVisible.value ? callout.value : null;
  const underCallout = (from: number, to: number) =>
    !!c && to > c.x - 6 && from < c.x + c.w + 6 && y > c.y - 4 && y - f < c.y + c.h + 4;
  const free = (from: number, to: number) => to <= x1 - 4 && (mx + 9 < from || mx - 9 > to) && !underCallout(from, to);
  const texts = [t("Safety cushion {amount}", { amount: eur(buffer.value) }), t("Cushion {amount}", { amount: eur(buffer.value) })];
  const candidates = texts.flatMap((text) => [
    { text, x: x0 + 8, anchor: "start", from: x0 + 8, to: x0 + 8 + widthOf(text) },
    { text, x: x1 - 8, anchor: "end", from: x1 - 8 - widthOf(text), to: x1 - 8 },
  ]);
  const pick =
    candidates.find((cand) => cand.from >= x0 && free(cand.from, cand.to)) ??
    candidates.find((cand) => cand.from >= x0 && cand.to <= x1 && !underCallout(cand.from, cand.to));
  // no clean spot (narrow phone + big text): hide it – the dashed red line and the red zone still say it
  return pick ? { ...pick, y, shown: true } : { ...candidates[3], y, shown: false };
});

/** "Lowest" call-out above (or below) the main line's lowest point in the window. */
const callout = computed(() => {
  const m = main.value;
  if (!m) return null;
  const f = fontPx.value;
  const label = t("Lowest · {date}", { date: fmtDayMonth(dateAt(mainMin.value.index)) });
  const value = eur(mainMin.value.value);
  const w = Math.round(Math.max(label.length * f * 0.56, value.length * remPx.value * 0.62) + 24);
  const h = Math.round(f * 1.25 + remPx.value * 1.25 + 14);
  const px = sx(mainMin.value.index);
  const py = sy(mainMin.value.value);
  const x = clamp(px - w / 2, plot.value.x0 + 4, W.value - pad.value.right - w);
  const above = py - h - 14 > plot.value.y0 - 6;
  return { w, h, x, y: above ? py - h - 14 : py + 14, label, value, f };
});

// --- selection model ------------------------------------------------------------------------------
interface Sel {
  a: number; // anchor (where the click/drag started)
  b: number; // moving end
}
const sel = ref<Sel | null>(null);
const lastSel = ref<Sel>({ a: 0, b: 0 }); // keeps the marker in place while it fades out
watch(sel, (s) => s && (lastSel.value = s));
const mode = computed<"today" | "day" | "range">(() => (!sel.value ? "today" : sel.value.a === sel.value.b ? "day" : "range"));
const hover = ref<number | null>(null); // mouse preview only

const shownSel = computed(() => sel.value ?? lastSel.value);
const selLo = computed(() => clamp(Math.min(shownSel.value.a, shownSel.value.b), 0, n.value - 1));
const selHi = computed(() => clamp(Math.max(shownSel.value.a, shownSel.value.b), 0, n.value - 1));

/** Period changed: keep what still fits, drop what fell out (markers fade instead of jumping). */
watch(n, (len) => {
  const s = sel.value;
  if (!s) return;
  if (Math.min(s.a, s.b) > len - 1) sel.value = null;
  else sel.value = { a: Math.min(s.a, len - 1), b: Math.min(s.b, len - 1) };
});

function select(next: Sel | null) {
  sel.value = next;
  hover.value = null;
  if (next) markHintSeen();
}
const backToToday = () => select(null);
const jumpToLowest = () => select({ a: mainMin.value.index, b: mainMin.value.index });

// --- pointer: hover preview · click = day · drag = period · Shift+click = period ------------------
interface Press {
  id: number;
  start: number;
  x: number;
  shift: boolean;
  dragging: boolean;
}
let press: Press | null = null;
const dragging = ref(false);

function indexAt(ev: PointerEvent): number {
  const r = svgEl.value!.getBoundingClientRect();
  const px = ((ev.clientX - r.left) / (r.width || 1)) * W.value;
  return clamp(Math.round(((px - plot.value.x0) / (plot.value.x1 - plot.value.x0)) * view.value.span), 0, n.value - 1);
}
function onDown(ev: PointerEvent) {
  if (!svgEl.value || (ev.pointerType === "mouse" && ev.button !== 0)) return;
  press = { id: ev.pointerId, start: indexAt(ev), x: ev.clientX, shift: ev.shiftKey, dragging: false };
  if (ev.pointerType === "mouse") svgEl.value.setPointerCapture(ev.pointerId);
}
function onMove(ev: PointerEvent) {
  if (!svgEl.value) return;
  const i = indexAt(ev);
  if (press && ev.pointerId === press.id) {
    if (!press.dragging && Math.abs(ev.clientX - press.x) > 6) press.dragging = dragging.value = true;
    if (press.dragging) {
      sel.value = { a: press.start, b: i };
      hover.value = null;
      return;
    }
  }
  if (ev.pointerType === "mouse") hover.value = i;
}
function onUp(ev: PointerEvent) {
  if (!press || ev.pointerId !== press.id) return;
  const i = indexAt(ev);
  if (press.dragging) select({ a: press.start, b: i });
  else if (press.shift && sel.value) select({ a: sel.value.a, b: i });
  else select({ a: i, b: i });
  if (ev.pointerType === "mouse") hover.value = i;
  press = null;
  dragging.value = false;
}
function onCancel() {
  // touch: the browser took over for a vertical scroll – nothing gets selected
  press = null;
  dragging.value = false;
  hover.value = null;
}
function onLeave(ev: PointerEvent) {
  if (ev.pointerType === "mouse" && !press) hover.value = null;
}

// --- keyboard -------------------------------------------------------------------------------------
function onKey(ev: KeyboardEvent) {
  const last = n.value - 1;
  const cur = sel.value ? sel.value.b : 0;
  const steps: Record<string, number> = { ArrowRight: cur + 1, ArrowLeft: cur - 1, PageDown: cur + 7, PageUp: cur - 7, Home: 0, End: last };
  if (ev.key in steps) {
    ev.preventDefault();
    const next = clamp(steps[ev.key], 0, last);
    select(ev.shiftKey ? { a: sel.value?.a ?? cur, b: next } : { a: next, b: next });
  } else if (ev.key === "Enter" || ev.key === " ") {
    ev.preventDefault();
    const i = hover.value ?? cur;
    select({ a: i, b: i });
  }
}

// --- hover bubble ---------------------------------------------------------------------------------
const hoverIndex = computed(() => clamp(hover.value ?? 0, 0, n.value - 1));
const hoverX = computed(() => sx(hoverIndex.value));
const tip = computed(() => {
  const { w, h } = tipSize.value;
  const mainY = sy(main.value ? bal(main.value, hoverIndex.value) : 0);
  let left = hoverX.value + 16;
  if (left + w > W.value - 4) left = hoverX.value - 16 - w;
  return {
    left: clamp(left, 4, Math.max(4, W.value - w - 4)),
    top: clamp(mainY - h / 2, plot.value.y0 - 4, Math.max(plot.value.y0, plot.value.y1 - h)),
  };
});

// --- selection marker on the chart ------------------------------------------------------------------
const selX0 = computed(() => sx(selLo.value));
const selX1 = computed(() => sx(selHi.value));

/** The "Lowest" call-out steps back while you hover/drag, and where it would cover your selection. */
const calloutVisible = computed(() => {
  const c = callout.value;
  if (!c || hover.value !== null || dragging.value || reveal.value <= 0.98) return false;
  if (!sel.value) return true;
  return !(selX1.value + 10 > c.x && selX0.value - 10 < c.x + c.w);
});
const tag = computed(() => {
  const text =
    selLo.value === selHi.value
      ? fmtDayMonth(dateAt(selLo.value))
      : `${fmtDayMonth(dateAt(selLo.value))} – ${fmtDayMonth(dateAt(selHi.value))}`;
  const w = Math.round(text.length * fontPx.value * 0.58 + 18);
  const x = clamp((selX0.value + selX1.value) / 2 - w / 2, plot.value.x0 - 6, W.value - w - 2);
  return { text, w, x };
});

// --- read-out --------------------------------------------------------------------------------------
const dayIndex = computed(() => (mode.value === "day" ? selLo.value : 0));
const toneOf = (v: number) => (v > 0 ? TONE_TEXT.positive : v < 0 ? TONE_TEXT.negative : "text-muted");

const dayRows = computed(() =>
  ordered.value.map((l) => {
    const value = bal(l, dayIndex.value);
    const m = windowMin(l.forecast, n.value);
    return { line: l, value, diff: value - bal(l, 0), below: value < buffer.value, min: m.value, minDate: dateAt(m.index) };
  }),
);

const rangeRows = computed(() => {
  const from = selLo.value;
  const to = selHi.value;
  return ordered.value.map((l) => {
    let minI = from;
    let below = 0;
    for (let i = from; i <= to; i++) {
      if (bal(l, i) < bal(l, minI)) minI = i;
      if (bal(l, i) < buffer.value) below++;
    }
    const start = bal(l, from);
    const end = bal(l, to);
    return { line: l, start, end, change: end - start, min: bal(l, minI), minDate: dateAt(minI), below };
  });
});
/** Big payments (the API's largest outflows of the main forecast) that fall inside the period. */
const rangePayments = computed(() => {
  const from = dateAt(selLo.value) ?? "";
  const to = dateAt(selHi.value) ?? "";
  return (main.value?.forecast.largest_outflows ?? [])
    .filter((o) => o.date >= from && o.date <= to)
    .sort((a, b) => a.date.localeCompare(b.date));
});
const rangeDays = computed(() => selHi.value - selLo.value + 1);

/** Read-out row "Without Avida": by the chosen day (today mode: by the end of the window) / within the period. */
const lossRow = computed(() => {
  if (mode.value === "range") {
    const v = lossAt(selHi.value) - lossAt(selLo.value);
    return { value: v, text: t("less in this period") };
  }
  const i = mode.value === "day" ? dayIndex.value : n.value - 1;
  return { value: lossAt(i), text: t("less by {date}", { date: fmtDayMonth(dateAt(i)) }) };
});
const inDays = (i: number) => (i === 0 ? t("Today") : tn(i, "in {n} day", "in {n} days"));
const startsIn = (i: number) => (i === 0 ? t("from today") : tn(i, "starts in {n} day", "starts in {n} days"));

const head = computed<{ main: string; sub: string }>(() => {
  if (mode.value === "range") {
    return {
      main: `${fmtDayMonth(dateAt(selLo.value))} – ${fmtDayMonth(dateAt(selHi.value))}`,
      sub: `${tn(rangeDays.value, "{n} day", "{n} days")} · ${startsIn(selLo.value)}`,
    };
  }
  if (mode.value === "day") return { main: fmtDate(dateAt(dayIndex.value)), sub: inDays(dayIndex.value) };
  return { main: t("Today"), sub: fmtDate(dateAt(0)) };
});

// copy = the read-out as one plain sentence (translated)
const copyText = computed(() => {
  if (mode.value === "range") {
    const rows = rangeRows.value
      .map(
        (r) =>
          `${t(r.line.label)}: ${eur(r.start)} → ${eur(r.end)} (${eurSigned(r.change)}), ` +
          `${t("lowest {amount} on {date}", { amount: eur(r.min), date: fmtDayMonth(r.minDate) })}, ` +
          (r.below ? tn(r.below, "{n} day below cushion", "{n} days below cushion") : t("always above cushion")),
      )
      .join("; ");
    const pays = rangePayments.value.length
      ? `${t("Big payments")}: ${rangePayments.value.map((o) => `${o.label} ${fmtDayMonth(o.date)} ${eur(o.amount)}`).join("; ")}`
      : t("No big payments in this range");
    return `${head.value.main} (${tn(rangeDays.value, "{n} day", "{n} days")}) – ${rows}. ${pays}.${lossCopy.value}`;
  }
  const rows = dayRows.value
    .map((r) =>
      mode.value === "day"
        ? `${t(r.line.label)}: ${eur(r.value)} (${eurSigned(r.diff)} ${t("vs today")})${r.below ? `, ${t("below cushion")}` : ""}`
        : `${t(r.line.label)}: ${eur(r.value)}`,
    )
    .join("; ");
  return mode.value === "day"
    ? `${fmtDate(dateAt(dayIndex.value))} (${inDays(dayIndex.value)}) – ${rows}${lossCopy.value}`
    : `${t("Today")}, ${fmtDate(dateAt(0))} – ${rows}${lossCopy.value}`;
});
const lossCopy = computed(() =>
  hasLoss.value ? ` ${t("Without Avida")}: ${eur(-lossRow.value.value)} ${lossRow.value.text}.` : "",
);

const copied = ref(false);
let copyTimer = 0;
async function copy() {
  const text = copyText.value;
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

// --- one-time hint ---------------------------------------------------------------------------------
const HINT_KEY = "avida-chart-hint-seen";
const readHint = () => {
  try {
    return localStorage.getItem(HINT_KEY) === "1";
  } catch {
    return false;
  }
};
const hintSeen = ref(readHint());
const coarse = typeof window !== "undefined" && window.matchMedia("(pointer: coarse)").matches;
function markHintSeen() {
  if (hintSeen.value) return;
  hintSeen.value = true;
  try {
    localStorage.setItem(HINT_KEY, "1");
  } catch {
    /* storage unavailable – hint just shows again next time */
  }
}

// --- measured read-out height (mode switches animate instead of jumping) -----------------------------
const roInner = ref<HTMLDivElement | null>(null);
const roH = ref<number | null>(null);

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
      else if (e.target === roInner.value) roH.value = (e.target as HTMLElement).offsetHeight;
    }
  });
  // observe the elements whenever they (re)appear (the chart renders only once data is there)
  watch(
    [wrap, tipEl, roInner],
    (els, old) => {
      old?.forEach((el) => el && ro?.unobserve(el));
      els.forEach((el) => el && ro?.observe(el));
    },
    { immediate: true },
  );
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
  <div v-if="base && total >= 2 && main" class="grid gap-3" @keydown.esc="backToToday">
    <!-- chart -->
    <div
      ref="wrap"
      class="relative -mx-1 rounded-lg px-1"
      tabindex="0"
      role="group"
      :aria-label="t('Forecast chart. Click a day or use the arrow keys. Hold Shift to select a period. Escape goes back to today.')"
      @keydown="onKey"
    >
      <svg
        ref="svgEl"
        :width="W"
        :height="svgH"
        :viewBox="`0 0 ${W} ${svgH}`"
        :class="['block w-full select-none overflow-visible [touch-action:pan-y]', dragging ? 'cursor-ew-resize' : 'cursor-crosshair']"
        role="img"
        :aria-label="t('Cash forecast for the next {n} days. Lowest balance {amount} on {date}.', {
          n,
          amount: eur(mainMin.value),
          date: fmtDate(dateAt(mainMin.index)),
        }) + (hasLoss ? ` ${t('Without Avida')}: ${eur(-lossAt(n - 1))} ${t('less by {date}', { date: fmtDate(dateAt(n - 1)) })}.` : '')"
        @pointerdown="onDown"
        @pointermove="onMove"
        @pointerup="onUp"
        @pointercancel="onCancel"
        @pointerleave="onLeave"
      >
        <defs>
          <clipPath :id="clipId">
            <rect :x="plot.x0 - 2" :y="0" :width="Math.max(0, revealX - plot.x0 + 4)" :height="svgH" />
          </clipPath>
        </defs>

        <!-- grid + y labels (fade in/out when the range changes, slide with the scale) -->
        <TransitionGroup name="fade" tag="g">
          <g v-for="v in yTicks" :key="v">
            <line :x1="plot.x0" :x2="plot.x1" :y1="sy(v)" :y2="sy(v)" class="stroke-grid" stroke-width="1" />
            <text :x="plot.x0 - 10" :y="sy(v) + fontPx * 0.35" text-anchor="end" class="fill-muted text-caption tabular-nums">
              {{ eur(v) }}
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
        <text
          :x="cushionLabel.x" :y="cushionLabel.y" :text-anchor="cushionLabel.anchor"
          :opacity="cushionLabel.shown ? 1 : 0"
          class="fill-negative text-caption font-semibold transition-opacity duration-base"
        >
          {{ cushionLabel.text }}
        </text>

        <!-- selected period: soft band (sky = selection colour) -->
        <rect
          x="0" :y="plot.y0" width="1" :height="guideBottom - plot.y0"
          class="pointer-events-none fill-sky transition-[transform,opacity] duration-fast"
          :style="{
            transform: `translateX(${selX0}px) scaleX(${Math.max(1, selX1 - selX0)})`,
            opacity: mode === 'range' ? 0.45 : 0,
          }"
        />

        <!-- x labels -->
        <text
          v-for="(i, k) in xTicks" :key="k"
          :x="sx(i)" :y="svgH - 10"
          :text-anchor="k === 0 ? 'start' : k === xTicks.length - 1 ? 'end' : 'middle'"
          class="fill-muted text-caption tabular-nums"
        >{{ i === 0 ? t("Today") : fmtDayMonth(dateAt(i)) }}</text>

        <!-- lines + area (clipped to the plot; draw in from the left on first paint).
             Area = one flat, faint fill under the main line only (never fading); scenarios differ by colour + dash. -->
        <g :clip-path="`url(#${clipId})`">
          <TransitionGroup name="fade" tag="g">
            <path
              v-for="p in drawn.filter((p) => p.line.tone === 'primary')" :key="`a-${p.line.label}`"
              :d="p.area" class="fill-chart-line" fill-opacity="0.06"
            />
            <path
              v-for="p in drawn" :key="p.line.label"
              :d="p.d"
              fill="none" :class="STROKE[p.line.tone]" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"
              :stroke-dasharray="p.line.tone === 'risk' ? '6 5' : undefined"
            />
          </TransitionGroup>
        </g>

        <!-- "without Avida" strip: header (what you would lose by the day in focus) + loss growing downwards -->
        <g v-if="hasLoss || strip.k > 0.01" :opacity="strip.k" aria-hidden="true">
          <text :x="plot.x0" :y="plot.y1 + strip.head - 6" class="fill-muted text-caption">{{ lossHead.label }}</text>
          <text
            :x="plot.x1" :y="plot.y1 + strip.head - 6" text-anchor="end"
            :class="['text-caption font-semibold tabular-nums', lossAt(lossIndex) > 0 ? 'fill-negative' : 'fill-muted']"
          >{{ lossHead.value }}</text>
          <line :x1="plot.x0" :x2="plot.x1" :y1="strip.top" :y2="strip.top" class="stroke-grid" stroke-width="1" />
          <g v-if="lossDrawn" :clip-path="`url(#${clipId})`">
            <path :d="lossDrawn.area" class="fill-chart-alt" fill-opacity="0.12" />
            <path :d="lossDrawn.d" fill="none" class="stroke-chart-alt" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
          </g>
          <!-- the day in focus (end of the window by default) -->
          <circle
            cx="0" cy="0" r="4" class="fill-chart-alt stroke-surface transition-[transform,opacity] duration-fast" stroke-width="2"
            :style="{ transform: `translate(${sx(lossIndex)}px, ${ly(lossAt(lossIndex))}px)` }"
            :opacity="shownAt(lossIndex) ? 1 : 0"
          />
        </g>

        <!-- points only where they carry meaning: the lowest point of each line (the rest appear on hover) -->
        <circle
          v-for="p in drawn" :key="`min-${p.line.label}`"
          :cx="sx(p.min.index)" :cy="sy(p.min.value)"
          r="4.5" :class="[FILL[p.line.tone], 'stroke-surface transition-opacity duration-base']" stroke-width="2"
          :opacity="shownAt(p.min.index) ? 1 : 0"
        />

        <!-- call-out: lowest point of the main line (steps back while you hover, drag or select over it) -->
        <g
          v-if="callout"
          class="pointer-events-none transition-opacity duration-base"
          :opacity="calloutVisible ? 1 : 0"
          aria-hidden="true"
        >
          <rect :x="callout.x" :y="callout.y" :width="callout.w" :height="callout.h" rx="8" class="fill-surface stroke-line" stroke-width="1" />
          <text :x="callout.x + 12" :y="callout.y + callout.f + 5" class="fill-muted text-caption">{{ callout.label }}</text>
          <text :x="callout.x + 12" :y="callout.y + callout.h - 9" class="fill-fg font-display text-base font-semibold tracking-tight tabular-nums">{{ callout.value }}</text>
        </g>

        <!-- selection: solid edge line(s), dots on every line, date tag on top -->
        <g class="pointer-events-none transition-opacity duration-base" :opacity="sel ? 1 : 0" aria-hidden="true">
          <line
            v-for="(x, k) in [selX0, selX1]" :key="`edge-${k}`"
            x1="0" x2="0" :y1="plot.y0 - 2" :y2="guideBottom"
            class="stroke-fg transition-transform duration-fast" stroke-width="1.5"
            :style="{ transform: `translateX(${x}px)` }"
          />
          <template v-for="(i, k) in [selLo, selHi]" :key="`sel-dots-${k}`">
            <circle
              v-for="l in lines" :key="`sd-${k}-${l.label}`"
              cx="0" cy="0" r="4.5" :class="[FILL[l.tone], 'stroke-surface transition-transform duration-fast']" stroke-width="2"
              :style="{ transform: `translate(${sx(i)}px, ${sy(bal(l, i))}px)` }"
            />
          </template>
          <g class="transition-transform duration-fast" :style="{ transform: `translate(${tag.x}px, 3px)` }">
            <rect x="0" y="0" :width="tag.w" :height="tagH" rx="6" class="fill-fg" />
            <text :x="tag.w / 2" :y="tagH / 2 + fontPx * 0.36" text-anchor="middle" class="fill-surface text-caption font-semibold tabular-nums">
              {{ tag.text }}
            </text>
          </g>
        </g>

        <!-- hover preview: dashed guide + small dots that glide between days -->
        <g
          class="pointer-events-none transition-opacity duration-base"
          :opacity="hover !== null && !dragging ? 1 : 0"
          aria-hidden="true"
        >
          <line
            x1="0" x2="0" :y1="plot.y0" :y2="guideBottom"
            class="stroke-muted transition-transform duration-fast" stroke-width="1" stroke-dasharray="3 3"
            :style="{ transform: `translateX(${hoverX}px)` }"
          />
          <circle
            v-for="l in lines" :key="`h-${l.label}`"
            cx="0" cy="0" r="4" :class="[FILL[l.tone], 'stroke-surface transition-transform duration-fast']" stroke-width="2"
            :style="{ transform: `translate(${hoverX}px, ${sy(bal(l, hoverIndex))}px)` }"
          />
        </g>
      </svg>

      <!-- floating bubble (preview) -->
      <div
        ref="tipEl"
        class="pointer-events-none absolute left-0 top-0 z-10 grid min-w-[9.5rem] gap-1 rounded-lg border border-line bg-surface px-3 py-2 shadow-pop transition-[transform,opacity] duration-fast"
        :style="{ transform: `translate(${tip.left}px, ${tip.top}px)`, opacity: hover !== null && !dragging ? 1 : 0 }"
        aria-hidden="true"
      >
        <b class="text-caption font-semibold text-muted">{{ fmtDate(dateAt(hoverIndex)) }}</b>
        <span v-for="l in ordered" :key="`t-${l.label}`" class="flex items-center justify-between gap-3 text-label">
          <span class="flex items-center gap-1.5 text-muted">
            <span :class="['h-2 w-2 rounded-full', DOT[l.tone]]" />{{ t(l.short) }}
          </span>
          <b class="font-semibold tabular-nums" :class="bal(l, hoverIndex) < buffer ? 'text-negative' : 'text-fg'">
            {{ eur(bal(l, hoverIndex)) }}
          </b>
        </span>
        <span v-if="hasLoss" class="flex items-center justify-between gap-3 border-t border-line pt-1 text-label">
          <span class="flex items-center gap-1.5 text-muted">
            <span class="h-2 w-2 rounded-full bg-chart-alt" />{{ t("Without Avida") }}
          </span>
          <b :class="['font-semibold tabular-nums', lossAt(hoverIndex) > 0 ? 'text-negative' : 'text-fg']">{{ eur(-lossAt(hoverIndex)) }}</b>
        </span>
      </div>
    </div>

    <!-- one-time hint: how to use the chart (fades away after the first selection) -->
    <CollapseTransition>
      <p v-if="!hintSeen" class="flex items-center justify-center gap-1.5 text-center text-caption text-muted">
        <AppIcon name="crosshair" :size="14" class="shrink-0" />
        {{ coarse ? t("Tap a day to see it · swipe sideways to compare a period") : t("Click a day to see it · drag to compare a period") }}
      </p>
    </CollapseTransition>

    <!-- read-out: today · the chosen day · the chosen period -->
    <div class="rounded-xl bg-input px-4 py-3 sm:px-5">
      <!-- buttons wrap under the title only when the title would get too narrow (phones at big text sizes) -->
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="flex min-w-[9rem] flex-1 items-center gap-3" aria-live="polite">
          <span class="grid min-w-0 leading-tight">
            <b class="font-semibold tabular-nums">{{ head.main }}</b>
            <span class="text-label text-muted">{{ head.sub }}</span>
          </span>
        </div>
        <div class="ml-auto flex shrink-0 items-center gap-1.5">
          <!-- slot always reserved (first, so the empty space sits next to the title) → appearing never shifts anything -->
          <button
            type="button"
            :class="[
              'inline-flex min-h-10 min-w-10 items-center justify-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 text-label font-semibold text-fg transition-[opacity,border-color,color] duration-base hover:border-fg/40 sm:min-h-9',
              sel ? 'opacity-100' : 'pointer-events-none opacity-0',
            ]"
            :tabindex="sel ? 0 : -1"
            :aria-hidden="!sel || undefined"
            :title="t('Back to today')"
            :aria-label="t('Back to today')"
            @click="backToToday"
          >
            <AppIcon name="undo" :size="16" /><span class="hidden sm:inline">{{ t("Back to today") }}</span>
          </button>
          <button
            type="button"
            class="inline-flex min-h-10 min-w-10 items-center justify-center gap-1.5 rounded-lg px-2.5 text-label font-semibold text-muted hover:bg-surface hover:text-fg sm:min-h-9"
            :title="t('Jump to the lowest point')"
            :aria-label="t('Jump to the lowest point')"
            @click="jumpToLowest"
          >
            <AppIcon name="trendingDown" :size="16" /><span class="hidden md:inline">{{ t("Lowest") }}</span>
          </button>
          <button
            type="button"
            class="inline-flex min-h-10 min-w-10 items-center justify-center rounded-lg border border-line bg-surface px-2.5 text-label font-semibold text-fg hover:border-fg/40 sm:min-h-9"
            :title="t('Copy')"
            :aria-label="copied ? t('Copied') : t('Copy')"
            @click="copy"
          >
            <!-- both states stacked in one cell → the button never changes size -->
            <span class="grid [&>*]:col-start-1 [&>*]:row-start-1">
              <span :class="['flex items-center gap-1.5 transition-opacity duration-base', copied ? 'opacity-0' : 'opacity-100']">
                <AppIcon name="copy" :size="16" /><span class="hidden lg:inline">{{ t("Copy") }}</span>
              </span>
              <span :class="['flex items-center gap-1.5 text-positive transition-opacity duration-base', copied ? 'opacity-100' : 'opacity-0']">
                <AppIcon name="check" :size="16" /><span class="hidden lg:inline">{{ t("Copied") }}</span>
              </span>
            </span>
            <span class="sr-only" role="status">{{ copied ? t("Copied to clipboard") : "" }}</span>
          </button>
        </div>
      </div>

      <!-- body: height is measured and animated; the content crossfades between modes -->
      <div class="overflow-hidden transition-[height] duration-base" :style="roH !== null ? { height: `${roH}px` } : undefined">
        <div ref="roInner" class="pt-3">
          <Transition name="fade" mode="out-in">
            <!-- period -->
            <div v-if="mode === 'range'" key="range" class="grid gap-3">
              <ul class="grid gap-3">
                <li v-for="r in rangeRows" :key="r.line.label" class="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-x-3 gap-y-1">
                  <svg width="28" height="8" class="mt-2" aria-hidden="true">
                    <line
                      x1="1" x2="27" y1="4" y2="4" :class="STROKE[r.line.tone]" stroke-width="2" stroke-linecap="round"
                      :stroke-dasharray="r.line.tone === 'risk' ? '6 5' : undefined"
                    />
                  </svg>
                  <span class="text-label font-medium leading-snug">{{ t(r.line.label) }}</span>
                  <!-- separate flex items → wraps cleanly on phones and at big text sizes -->
                  <div class="col-start-2 flex flex-wrap items-baseline gap-x-2 gap-y-0.5 font-display text-base font-semibold tracking-tight tabular-nums sm:text-lg">
                    <span>{{ eur(r.start) }}</span>
                    <span class="font-sans font-normal text-muted" aria-hidden="true">→</span>
                    <span class="sr-only">–</span>
                    <span :class="r.end < buffer ? 'text-negative' : ''">{{ eur(r.end) }}</span>
                    <span :class="['ml-1 font-sans text-label font-semibold', toneOf(r.change)]">{{ eurSigned(r.change) }}</span>
                  </div>
                  <span class="col-start-2 text-caption text-muted">
                    {{ t("lowest {amount} on {date}", { amount: eur(r.min), date: fmtDayMonth(r.minDate) }) }} ·
                    <span :class="r.below ? 'font-semibold text-negative' : 'text-positive'">
                      {{ r.below ? tn(r.below, "{n} day below cushion", "{n} days below cushion") : t("always above cushion") }}
                    </span>
                  </span>
                </li>
                <li v-if="hasLoss" class="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-x-3 gap-y-1">
                  <svg width="28" height="8" class="mt-2" aria-hidden="true">
                    <line x1="1" x2="27" y1="4" y2="4" class="stroke-chart-alt" stroke-width="2" stroke-linecap="round" />
                  </svg>
                  <span class="text-label font-medium leading-snug">{{ t("Without Avida you would lose") }}</span>
                  <span
                    :class="[
                      'col-start-2 font-display text-base font-semibold tracking-tight tabular-nums sm:text-lg',
                      lossRow.value > 0 ? 'text-negative' : 'text-muted',
                    ]"
                  >
                    {{ eur(-lossRow.value) }}
                    <span class="ml-1 font-sans text-label font-normal text-muted">{{ lossRow.text }}</span>
                  </span>
                </li>
              </ul>
              <div class="grid gap-2 border-t border-line pt-3">
                <span class="text-label font-semibold">{{ t("Big payments in this range") }}</span>
                <ul v-if="rangePayments.length" class="grid gap-1.5">
                  <!-- name (may truncate) with its date underneath (never cut off), amount on the right -->
                  <li
                    v-for="(o, k) in rangePayments" :key="`${o.date}-${k}`"
                    class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-2.5"
                  >
                    <AppIcon :name="categoryIcon(o.category)" :size="16" class="text-muted" />
                    <span class="grid min-w-0 leading-snug">
                      <span class="truncate text-label" :title="o.label">{{ o.label }}</span>
                      <span class="text-caption tabular-nums text-muted">{{ fmtDate(o.date) }}</span>
                    </span>
                    <b class="whitespace-nowrap text-label font-semibold tabular-nums">{{ eur(o.amount) }}</b>
                  </li>
                </ul>
                <p v-else class="text-label text-muted">{{ t("No big payments in this range") }}</p>
              </div>
            </div>

            <!-- today / one day (same structure → moving between days never changes the height) -->
            <ul v-else key="day" class="grid gap-3">
              <li v-for="r in dayRows" :key="r.line.label" class="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-x-3 gap-y-1">
                <svg width="28" height="8" class="mt-2" aria-hidden="true">
                  <line
                    x1="1" x2="27" y1="4" y2="4" :class="STROKE[r.line.tone]" stroke-width="2" stroke-linecap="round"
                    :stroke-dasharray="r.line.tone === 'risk' ? '6 5' : undefined"
                  />
                </svg>
                <span class="text-label font-medium leading-snug">{{ t(r.line.label) }}</span>
                <!-- line 1: the balance (+ cushion warning, always reserved → no height change while moving) -->
                <div class="col-start-2 flex flex-wrap items-center gap-x-3 gap-y-1">
                  <b :class="['font-display text-lg font-semibold tracking-tight tabular-nums', r.below ? 'text-negative' : 'text-fg']">{{ eur(r.value) }}</b>
                  <StatusPill tone="negative" :class="['transition-opacity duration-base', r.below ? 'opacity-100' : 'invisible opacity-0']">
                    <AppIcon name="alert" :size="13" />{{ t("below cushion") }}
                  </StatusPill>
                </div>
                <!-- line 2: change vs today (a day) or the lowest point ahead (today) – same height in both modes -->
                <span v-if="mode === 'day'" :class="['col-start-2 text-label font-semibold tabular-nums', toneOf(r.diff)]">
                  {{ eurSigned(r.diff) }} <span class="font-normal text-muted">{{ t("vs today") }}</span>
                </span>
                <span v-else class="col-start-2 text-label text-muted">
                  {{ t("Lowest ahead {amount} · {date}", { amount: eur(r.min), date: fmtDayMonth(r.minDate) }) }}
                </span>
              </li>
              <!-- what following Avida is worth: the gap between the two lines, as money you would lose without it -->
              <li v-if="hasLoss" class="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-x-3 gap-y-1 border-t border-line pt-3">
                <svg width="28" height="8" class="mt-2" aria-hidden="true">
                  <line x1="1" x2="27" y1="4" y2="4" class="stroke-chart-alt" stroke-width="2" stroke-linecap="round" />
                </svg>
                <span class="text-label font-medium leading-snug">{{ t("Without Avida you would lose") }}</span>
                <span class="col-start-2 flex flex-wrap items-baseline gap-x-2">
                  <b :class="['font-display text-lg font-semibold tracking-tight tabular-nums', lossRow.value > 0 ? 'text-negative' : 'text-muted']">
                    {{ eur(-lossRow.value) }}
                  </b>
                  <span class="text-label text-muted">{{ lossRow.text }}</span>
                </span>
              </li>
            </ul>
          </Transition>
        </div>
      </div>
    </div>
  </div>
</template>
