import type { IconName } from "@/components/ui/icons";
import type { Action, Finding } from "@/types/api";
import { describeFinding } from "@/components/findings/describe";
import { eur, fmtDayMonth } from "@/utils/format";

/**
 * One item in the Action center. Either an action to approve (optionally explained by the finding it came from),
 * or a finding with nothing to approve (e.g. a price change that is within the contract).
 */
export interface DecisionItem {
  key: string;
  action?: Action;
  finding?: Finding;
}

export type DecisionState = "pending" | "review" | "executed" | "rejected" | "no-action";
export type DecisionCategory = "emails" | "forecast";
type Tone = "accent" | "warn" | "positive" | "neutral" | "info";

export function decisionState(item: DecisionItem): DecisionState {
  if (item.action) return item.action.status;
  return item.finding?.recommendation === "review" ? "review" : "no-action";
}

/** Waiting for the owner: an action to approve, or a finding the owner should check themselves. */
export const isOpenItem = (item: DecisionItem) => {
  const s = decisionState(item);
  return s === "pending" || s === "review";
};

export const categoryOf = (item: DecisionItem): DecisionCategory =>
  item.action && item.action.type !== "send_email" ? "forecast" : "emails";

export const CATEGORY_LABEL: Record<DecisionCategory, string> = {
  emails: "Based on your emails",
  forecast: "Based on your forecast",
};

export const STATUS: Record<DecisionState, { label: string; tone: Tone }> = {
  pending: { label: "Waiting for you", tone: "accent" },
  review: { label: "Check it yourself", tone: "warn" },
  executed: { label: "Approved", tone: "positive" },
  rejected: { label: "Declined", tone: "neutral" },
  "no-action": { label: "No action needed", tone: "info" },
};

export function iconOf(item: DecisionItem): IconName {
  if (!item.action) return "inbox";
  return item.action.type === "send_email" ? "send" : "landmark";
}

/** A two-word gist for the small tile: "CloudHost +15 %" / "Reject the increase". */
export function gist(item: DecisionItem): { title: string; hint: string } {
  const { action: a, finding: f } = item;
  if (a?.type === "credit_application") {
    return { title: "Overdraft", hint: `Bridge ${fmtDayMonth(a.payload.from)} – ${fmtDayMonth(a.payload.until)}` };
  }
  if (f) {
    const d = describeFinding(f);
    const hint = {
      reject: "Reject the increase",
      accept: "Within your contract",
      remind: "Remind them to pay on time",
      review: "Ask for the exact figures",
    }[f.recommendation];
    return { title: `${d.shortParty} · ${d.figure}`, hint };
  }
  return { title: a?.title ?? "Decision", hint: "" };
}

/** The one number worth seeing on the tile. */
export function keyFigure(item: DecisionItem): { label: string; value: string; tone: string } | null {
  const { action: a, finding: f } = item;
  if (a?.type === "credit_application") return { label: "Amount", value: eur(a.payload.amount), tone: "" };
  if (a && a.savings_12m > 0) {
    return a.status === "rejected"
      ? { label: "Would have saved", value: eur(a.savings_12m), tone: "text-muted" }
      : { label: "You save / year", value: eur(a.savings_12m), tone: "text-positive" };
  }
  if (f) {
    const k = describeFinding(f).key;
    return k ? { ...k, tone: "" } : null;
  }
  return null;
}

/** Build the items: every action (with its finding, if any) + every finding without an action. */
export function buildItems(actions: Action[], findings: Finding[]): DecisionItem[] {
  const fromActions = actions.map((a) => ({
    key: a.id,
    action: a,
    finding: findings.find((f) => f.action_id === a.id),
  }));
  const infoOnly = findings.filter((f) => !f.action_id).map((f) => ({ key: f.id, finding: f }));
  return [...fromActions, ...infoOnly];
}
