import type { IconName } from "@/components/ui/icons";
import type { AnswerSource, Autonomy, Recommendation, Verdict } from "@/types/api";

/**
 * The four autonomy levels required by the challenge card. Labels are fixed by docs/API.md –
 * keep them identical everywhere (badge, legend, policy page). Icons: Lucide (no emoji in the UI).
 */
export const AUTONOMY: Record<Autonomy, { label: string; icon: IconName; description: string; classes: string }> = {
  analyzed: {
    label: "Analysed by agent",
    icon: "analyzed",
    description: "The agent did this on its own – reading and calculating only.",
    classes: "bg-mist text-mist-fg",
  },
  recommendation: {
    label: "Recommendation",
    icon: "recommendation",
    description: "The agent suggests something. You decide.",
    classes: "bg-warn-soft text-warn",
  },
  approval: {
    label: "Needs your approval",
    icon: "approval",
    description: "Nothing happens until you click Approve.",
    classes: "bg-sun text-sun-on",
  },
  simulated: {
    label: "Simulated execution",
    icon: "simulated",
    description: "Executed in a safe simulation – nothing leaves the system.",
    classes: "border border-dashed border-muted/60 text-muted",
  },
};

export const AUTONOMY_ORDER: Autonomy[] = ["analyzed", "recommendation", "approval", "simulated"];

export const SOURCE_LABEL: Record<AnswerSource, string> = {
  llm: "AI model",
  fallback: "cached answer",
  rules: "rule-based",
};

export const VERDICT: Record<Verdict, { label: string; tone: "negative" | "positive" | "neutral" }> = {
  violates: { label: "Not allowed by your contract", tone: "negative" },
  allowed: { label: "Allowed by your contract", tone: "positive" },
  unclear: { label: "No contract found – please check", tone: "neutral" },
};

export const RECOMMENDATION: Record<Recommendation, string> = {
  reject: "Reject the increase",
  accept: "Accept – it's within the contract",
  review: "Check it yourself",
};
