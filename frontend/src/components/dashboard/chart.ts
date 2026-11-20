import type { Forecast, Scenarios } from "@/types/api";

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
