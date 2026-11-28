import type { Tone } from "@/components/ui/tones";
import { describeFinding } from "@/components/findings/describe";
import { t } from "@/i18n";
import type { Action, AnswerSource, Finding } from "@/types/api";
import { eur, fmtDayMonth } from "@/utils/format";

/**
 * One item in the Action center. Either an action to approve (optionally explained by the finding it came from),
 * or a finding with nothing to approve (e.g. a price change that is within the contract).
 * Labels below are English source text – translate where shown (`t(STATUS[s].label)`); the helpers that build
 * text (gist, keyFigure) call t() themselves, so call them at render time (computed / template).
 */
export interface DecisionItem {
  key: string;
  action?: Action;
  finding?: Finding;
}

/** AV Rewrite result (POST /redraft) handed to ActionCard; `n` changes on every new result so the same text twice still lands. */
export interface RewrittenDraft {
  body: string;
  source: AnswerSource;
  n: number;
  /** "Version 2" */
  attempt: number;
  /** false = the model was unavailable, the draft is unchanged – show `note` */
  changed: boolean;
  note: string | null;
}

/** Result of a check of the draft: the Legal Agent's review of a rewrite, or the instant check while typing. */
export interface DraftCheck {
  approved: boolean;
  issues: string[];
  /** "rewrite" = came with the AV Rewrite proposal · "typing" = POST /review after the owner edited the text */
  origin: "rewrite" | "typing";
}

/** A chip in the AV Rewrite pop-up: what it says and what is sent as the instruction. */
export interface RewriteHint {
  label: string;
  instruction: string;
}

export type DecisionState = "pending" | "review" | "executed" | "rejected" | "no-action";
export type DecisionCategory = "emails" | "forecast";

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
  pending: { label: "Waiting for you", tone: "warn" }, // warn = "pending, needs attention" in the palette
  review: { label: "Check it yourself", tone: "warn" },
  executed: { label: "Approved", tone: "positive" },
  rejected: { label: "Declined", tone: "neutral" },
  "no-action": { label: "No action needed", tone: "info" },
};

/** A two-word gist for the small tile: "CloudHost +15 %" / "Reject the increase" (translated). */
export function gist(item: DecisionItem): { title: string; hint: string } {
  const { action: a, finding: f } = item;
  if (a?.type === "credit_application") {
    return {
      title: t("Overdraft"),
      hint: t("Bridge {from} – {until}", { from: fmtDayMonth(a.payload.from), until: fmtDayMonth(a.payload.until) }),
    };
  }
  if (f) {
    // price change / late payment / email without figures – describeFinding() words all three (translated)
    const d = describeFinding(f);
    const HINT: Record<string, string> = {
      reject: "Reject the increase",
      accept: "Within your contract",
      remind: "Remind them to pay on time",
      review: "Ask for the exact figures",
    };
    return { title: `${d.shortParty} · ${d.figure}`, hint: t(HINT[f.recommendation] ?? "Check it yourself") };
  }
  return { title: a?.title ?? t("Decision"), hint: "" };
}

/** The one number worth seeing on the tile (label translated; `tone` = text colour class). */
export function keyFigure(item: DecisionItem): { label: string; value: string; tone: string } | null {
  const { action: a, finding: f } = item;
  if (a?.type === "credit_application") return { label: t("Amount"), value: eur(a.payload.amount), tone: "" };
  if (a && a.savings_12m > 0) {
    return a.status === "rejected"
      ? { label: t("Would have saved"), value: eur(a.savings_12m), tone: "text-muted" }
      : { label: t("You save / year"), value: eur(a.savings_12m), tone: "text-positive" };
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
