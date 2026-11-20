import type { Outflow } from "@/types/api";

/**
 * Helpers for the "Biggest payments ahead" donut (PaymentsDonut.vue).
 * The API sends the 5 largest single outflows of the forecast (negative amounts). Payments with the same
 * label are one recurring payment (e.g. payroll every month) → one slice with a sum, a count and their dates.
 */
export interface PaymentGroup {
  key: string;
  label: string;
  /** label without the "(…)" / "– …" detail → fits in the donut centre */
  short: string;
  category: string;
  /** positive EUR */
  total: number;
  /** ISO dates, ascending */
  dates: string[];
  /** 0..1 of all shown payments */
  share: number;
}

export const shortLabel = (label: string) => label.replace(/\s*(\(|–|—).*$/, "").trim() || label;

export function groupPayments(outflows: Outflow[]): PaymentGroup[] {
  const byLabel = new Map<string, PaymentGroup>();
  for (const o of outflows) {
    const g =
      byLabel.get(o.label) ??
      { key: o.label, label: o.label, short: shortLabel(o.label), category: o.category, total: 0, dates: [], share: 0 };
    g.total += Math.abs(o.amount);
    g.dates.push(o.date);
    byLabel.set(o.label, g);
  }
  const groups = [...byLabel.values()].sort((a, b) => b.total - a.total);
  const sum = groups.reduce((s, g) => s + g.total, 0) || 1;
  for (const g of groups) {
    g.share = g.total / sum;
    g.dates.sort();
  }
  return groups;
}

/**
 * Categorical slice colours – the `slice-1…5` tokens (tokens.css). By default they are the Aurum colours
 * (navy/mint → sun → deep blue → sky → steel, neighbours contrast in light AND dark); in High contrast they
 * become 5 distinct hues on black instead of all turning yellow. No positive/negative/chart-alt: those mean
 * good/bad money.
 */
export const SLICES = [
  { stroke: "stroke-slice-1", bg: "bg-slice-1" },
  { stroke: "stroke-slice-2", bg: "bg-slice-2" },
  { stroke: "stroke-slice-3", bg: "bg-slice-3" },
  { stroke: "stroke-slice-4", bg: "bg-slice-4" },
  { stroke: "stroke-slice-5", bg: "bg-slice-5" },
] as const;
