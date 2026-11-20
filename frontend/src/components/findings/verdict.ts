import type { Verdict } from "@/types/api";

/**
 * Verdict → colour roles used by the finding card, price bar and split screen.
 * `stat` is a StatTile tone (ui/tones.ts): a disallowed increase is money you'd lose → red;
 * an allowed one is a legitimate cost → neutral navy value with an info tile.
 */
export function verdictTone(v: Verdict) {
  if (v === "violates") return { bar: "negative", text: "text-negative", panel: "bg-negative-soft", stat: "negative" } as const;
  if (v === "unclear") return { bar: "warn", text: "text-warn", panel: "bg-warn-soft", stat: "warn" } as const;
  return { bar: "neutral", text: "text-fg", panel: "bg-positive-soft", stat: "info" } as const;
}
