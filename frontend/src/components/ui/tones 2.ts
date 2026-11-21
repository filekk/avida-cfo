/**
 * ONE colour map for every "tone" in the app (pills, icon tiles, stat values, KPI values).
 * Positive/negative = money & status only (green = good for you, red = bad for you).
 * Use these maps instead of re-typing `bg-positive-soft text-positive` in components.
 */
export type Tone = "neutral" | "info" | "positive" | "negative" | "warn" | "accent";

/** Soft background + coloured foreground: pills, icon tiles. */
export const TONE_SOFT: Record<Tone, string> = {
  neutral: "bg-input text-muted",
  info: "bg-mist text-mist-fg",
  positive: "bg-positive-soft text-positive",
  negative: "bg-negative-soft text-negative",
  warn: "bg-warn-soft text-warn",
  accent: "bg-sun text-sun-on",
};

/** Text colour for a VALUE (amount, %): only money semantics get a colour, the rest stays navy. */
export const TONE_TEXT: Record<Tone, string> = {
  neutral: "",
  info: "",
  positive: "text-positive",
  negative: "text-negative",
  warn: "text-warn",
  accent: "",
};

/** Trend icon that goes with a tone in KPI/trend pills. */
export const TONE_TREND = { positive: "trendingUp", negative: "trendingDown", neutral: "chart" } as const;
