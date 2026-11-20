import type { Verdict } from "@/types/api";

/** Verdict → colour roles used by the finding card, price bar and split screen. */
export function verdictTone(v: Verdict) {
  if (v === "violates") return { bar: "negative", text: "text-negative", panel: "bg-negative-soft/60", stat: "negative" } as const;
  if (v === "unclear") return { bar: "warn", text: "text-warn", panel: "bg-warn-soft/70", stat: "warn" } as const;
  return { bar: "neutral", text: "text-fg", panel: "bg-positive-soft/60", stat: "neutral" } as const;
}
