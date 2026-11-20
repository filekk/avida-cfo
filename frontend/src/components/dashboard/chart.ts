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
  /** primary = navy (mint in dark) · risk = coral, dashed */
  tone: "primary" | "risk";
}

/** Maps backend scenarios to chart lines: before sync only "current", after sync "if_accepted" vs "recommended". */
export function scenarioLines(s: Scenarios): ChartLine[] {
  const lines: ChartLine[] = [];
  if (s.if_accepted) lines.push({ forecast: s.if_accepted, label: "If you accept every price increase", tone: "risk" });
  lines.push({
    forecast: s.recommended ?? s.current,
    label: s.recommended ? "If you follow Avida's advice" : "Your forecast",
    tone: "primary",
  });
  return lines;
}
