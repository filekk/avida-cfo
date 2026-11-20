import type { IconName } from "@/components/ui/icons";
import type { Tone } from "@/components/ui/tones";
import type { AnswerSource, Autonomy, Recommendation, Verdict } from "@/types/api";

/**
 * The four autonomy levels required by the challenge card. Labels are fixed by docs/API.md –
 * keep them identical everywhere (badge, legend, policy page). Icons: Lucide (no emoji in the UI).
 * `classes` = badge colours · `tone` = the matching IconTile tone (ui/tones.ts) · `tile` = extra IconTile classes
 * (the sandbox level is drawn dashed everywhere, so its tile stays visible on grey panels too).
 */
export const AUTONOMY: Record<
  Autonomy,
  { label: string; icon: IconName; description: string; classes: string; tone: Tone; tile?: string }
> = {
  analyzed: {
    label: "Analysed by agent",
    icon: "analyzed",
    description: "Reads and calculates on its own.",
    classes: "border-transparent bg-mist text-mist-fg",
    tone: "info",
  },
  recommendation: {
    label: "Recommendation",
    icon: "recommendation",
    description: "Suggests a step. You decide.",
    classes: "border-transparent bg-warn-soft text-warn",
    tone: "warn",
  },
  approval: {
    label: "Needs your approval",
    icon: "approval",
    description: "Waits for your click.",
    classes: "border-transparent bg-sun text-sun-on",
    tone: "accent",
  },
  simulated: {
    label: "Simulated execution",
    icon: "simulated",
    description: "Runs in a safe sandbox. Nothing leaves.",
    classes: "border-dashed border-muted bg-surface text-muted",
    tone: "neutral",
    tile: "border border-dashed border-muted",
  },
};

export const AUTONOMY_ORDER: Autonomy[] = ["analyzed", "recommendation", "approval", "simulated"];

export const SOURCE_LABEL: Record<AnswerSource, string> = {
  llm: "AI model",
  fallback: "cached answer",
  rules: "rule-based",
};

export const VERDICT: Record<Verdict, { label: string; tone: "negative" | "positive" | "warn"; icon: IconName }> = {
  violates: { label: "Not allowed by your contract", tone: "negative", icon: "xCircle" },
  allowed: { label: "Allowed by your contract", tone: "positive", icon: "checkCircle" },
  unclear: { label: "No contract found – please check", tone: "warn", icon: "alert" },
};

export const RECOMMENDATION: Record<Recommendation, string> = {
  reject: "Reject the increase",
  accept: "Accept – it's within the contract",
  review: "Check it yourself",
};
