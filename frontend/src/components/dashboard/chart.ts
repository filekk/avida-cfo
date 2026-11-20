import type { IconName } from "@/components/ui/icons";
import type { Forecast, Scenarios } from "@/types/api";

/** Cash-flow category (backend data/cashflows.json) → icon for the "biggest payments" list. */
const CATEGORY_ICON: Record<string, IconName> = {
  payroll: "users",
  rent: "building",
  supplier: "truck",
  tax: "landmark",
  loan: "landmark",
  revenue: "euro",
  other: "receipt",
};
export const categoryIcon = (category: string): IconName => CATEGORY_ICON[category] ?? "receipt";

export interface ChartLine {
  forecast: Forecast;
  label: string;
  /** 1–3 words for the hover bubble ("Avida's advice"). */
  short: string;
  /** primary = navy (mint in dark) · risk = coral, dashed */
  tone: "primary" | "risk";
}

// --- geometry helpers for ForecastChart (plain SVG, no chart library) ---------------------------

type Pt = readonly [number, number];
const sign = (v: number) => (v < 0 ? -1 : 1);

/** Tangent at p1 (Fritsch–Carlson, as in d3 curveMonotoneX) – never overshoots the data. */
function slope3(p0: Pt, p1: Pt, p2: Pt): number {
  const h0 = p1[0] - p0[0];
  const h1 = p2[0] - p1[0];
  const s0 = (p1[1] - p0[1]) / (h0 || 1e-9);
  const s1 = (p2[1] - p1[1]) / (h1 || 1e-9);
  const p = (s0 * h1 + s1 * h0) / (h0 + h1 || 1e-9);
  return (sign(s0) + sign(s1)) * Math.min(Math.abs(s0), Math.abs(s1), 0.5 * Math.abs(p)) || 0;
}
/** End tangent from the neighbouring one. */
function slope2(p0: Pt, p1: Pt, t: number): number {
  const h = p1[0] - p0[0];
  return h ? ((3 * (p1[1] - p0[1])) / h - t) / 2 : t;
}

/**
 * Smooth SVG path through every point using monotone cubic interpolation: corners are rounded,
 * but the curve never goes above/below the data – the lowest point stays exactly on the line.
 */
export function monotonePath(pts: Pt[]): string {
  const n = pts.length;
  if (!n) return "";
  const f = (v: number) => v.toFixed(1);
  if (n < 3) return pts.map((p, i) => `${i ? "L" : "M"}${f(p[0])},${f(p[1])}`).join("");
  const t = new Array<number>(n);
  for (let i = 1; i < n - 1; i++) t[i] = slope3(pts[i - 1], pts[i], pts[i + 1]);
  t[0] = slope2(pts[0], pts[1], t[1]);
  t[n - 1] = slope2(pts[n - 2], pts[n - 1], t[n - 2]);
  let d = `M${f(pts[0][0])},${f(pts[0][1])}`;
  for (let i = 0; i < n - 1; i++) {
    const [x0, y0] = pts[i];
    const [x1, y1] = pts[i + 1];
    const dx = (x1 - x0) / 3;
    d += `C${f(x0 + dx)},${f(y0 + dx * t[i])},${f(x1 - dx)},${f(y1 - dx * t[i + 1])},${f(x1)},${f(y1)}`;
  }
  return d;
}

/** "Nice" axis ticks (1 / 2 / 2.5 / 5 × 10ⁿ) covering [min, max]. */
export function niceTicks(min: number, max: number, count: number): number[] {
  const span = max - min || 1;
  const raw = span / Math.max(1, count);
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag;
  const ticks: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-6; v += step) ticks.push(Math.round(v * 100) / 100);
  return ticks;
}

/** Index + value of the lowest balance among the first `n` points (first occurrence). */
export function windowMin(f: Forecast, n: number): { index: number; value: number } {
  let index = 0;
  for (let i = 1; i < Math.min(n, f.series.length); i++) if (f.series[i].balance < f.series[index].balance) index = i;
  return { index, value: f.series[index]?.balance ?? 0 };
}

/** Maps backend scenarios to chart lines: before sync only "current", after sync "if_accepted" vs "recommended". */
export function scenarioLines(s: Scenarios): ChartLine[] {
  const lines: ChartLine[] = [];
  if (s.if_accepted) {
    lines.push({ forecast: s.if_accepted, label: "If you accept every price increase", short: "Accept all increases", tone: "risk" });
  }
  lines.push({
    forecast: s.recommended ?? s.current,
    label: s.recommended ? "If you follow Avida's advice" : "Your forecast",
    short: s.recommended ? "Follow Avida's advice" : "Your forecast",
    tone: "primary",
  });
  return lines;
}
